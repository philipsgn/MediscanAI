"""
data_platform.py

API Endpoints cho Mediscan AI Data-Centric Platform:
- Quản lý hàng đợi Review Queue & Data Quality
- Human-in-the-Loop (HITL) Correction
- Dataset Candidate & Active Learning Ground Truth Export
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.core.versioning import DEFAULT_DATASET_VERSION, PipelineLineageMetadata
from app.db.session import get_db
from app.schemas.data_platform_schema import (
    DatasetCandidateRequest,
    DatasetCandidateResponse,
    DatasetExportItem,
    DatasetExportResponse,
    HumanCorrectedDrug,
    HumanCorrectionRequest,
    HumanCorrectionResponse,
    ScanRecordStatus,
    ScanReviewDetailResponse,
    ScanReviewListResponse,
    ScanReviewSummaryItem,
)
from app.schemas.ocr_schema import EvaluationResponse, MappedDrugItem, OCRItem
from app.schemas.user_schema import UserResponse
from app.services.data_capture_service import data_capture_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["Data-Centric AI Platform & HITL Review Queue"])


@router.get("/reviews", response_model=ScanReviewListResponse)
async def list_review_queue(
    status_filter: Optional[ScanRecordStatus] = Query(None, alias="status", description="Lọc theo trạng thái scan"),
    source_type: Optional[str] = Query(None, description="Lọc theo loại nguồn ('prescription' | 'packaging')"),
    is_dataset_candidate: Optional[bool] = Query(None, description="Lọc các scan đã là ứng viên dataset"),
    min_quality: Optional[float] = Query(None, ge=0.0, le=1.0, description="Ngưỡng quality score tối thiểu"),
    max_quality: Optional[float] = Query(None, ge=0.0, le=1.0, description="Ngưỡng quality score tối đa"),
    limit: int = Query(50, ge=1, le=100, description="Số lượng bản ghi mỗi trang"),
    offset: int = Query(0, ge=0, description="Vị trí bắt đầu phân trang"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScanReviewListResponse:
    """Lấy danh sách các scan trong Review Queue phục vụ kiểm soát chất lượng dữ liệu."""
    total, records = await data_capture_service.get_review_queue(
        db=db,
        status=status_filter,
        source_type=source_type,
        is_dataset_candidate=is_dataset_candidate,
        min_quality=min_quality,
        max_quality=max_quality,
        limit=limit,
        offset=offset,
    )

    items = [
        ScanReviewSummaryItem(
            scan_id=rec.id,
            request_id=rec.request_id,
            user_id=rec.user_id,
            source_type=rec.source_type,
            image_ref=rec.image_ref,
            status=ScanRecordStatus(rec.status),
            quality_score=rec.quality_score,
            quality_flags=rec.quality_flags or [],
            is_dataset_candidate=rec.is_dataset_candidate,
            dataset_version=rec.dataset_version,
            created_at=rec.created_at,
            reviewed_at=rec.reviewed_at,
            reviewed_by=rec.reviewed_by,
        )
        for rec in records
    ]

    return ScanReviewListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@router.get("/reviews/{scan_id}", response_model=ScanReviewDetailResponse)
async def get_scan_review_detail(
    scan_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScanReviewDetailResponse:
    """Lấy chi tiết toàn bộ artifacts của một scan phục vụ giao diện hiệu đính Human-in-the-Loop."""
    rec = await data_capture_service.get_scan_record(db, scan_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "SCAN_RECORD_NOT_FOUND",
                "message": f"Không tìm thấy bản ghi scan với ID '{scan_id}'.",
                "service": "data_platform",
                "stage": "review_detail",
                "request_id": scan_id,
                "retryable": False,
            },
        )

    raw_ocr = [OCRItem(**item) for item in (rec.raw_ocr_result or [])]
    normalized = [MappedDrugItem(**item) for item in (rec.normalized_result or [])]
    clinical = EvaluationResponse(**rec.clinical_result) if rec.clinical_result else None
    lineage = PipelineLineageMetadata(**(rec.version_metadata or {}))

    return ScanReviewDetailResponse(
        scan_id=rec.id,
        request_id=rec.request_id,
        user_id=rec.user_id,
        source_type=rec.source_type,
        image_ref=rec.image_ref,
        status=ScanRecordStatus(rec.status),
        quality_score=rec.quality_score,
        quality_flags=rec.quality_flags or [],
        raw_ocr_result=raw_ocr,
        normalized_result=normalized,
        clinical_result=clinical,
        corrected_payload=rec.corrected_payload,
        is_dataset_candidate=rec.is_dataset_candidate,
        dataset_version=rec.dataset_version,
        dataset_tag=rec.dataset_tag,
        version_metadata=lineage,
        reviewed_by=rec.reviewed_by,
        reviewed_at=rec.reviewed_at,
        review_notes=rec.review_notes,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
    )


@router.post("/reviews/{scan_id}/correct", response_model=HumanCorrectionResponse)
async def submit_human_correction(
    scan_id: str,
    body: HumanCorrectionRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HumanCorrectionResponse:
    """
    Submit hiệu đính từ Human Reviewer (HITL).
    Bảo đảm: Lưu corrected_payload riêng biệt, không ghi đè raw AI output.
    """
    try:
        updated_scan = await data_capture_service.submit_human_correction(
            db=db,
            scan_id=scan_id,
            reviewer_id=current_user.id,
            correction_req=body,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "SCAN_RECORD_NOT_FOUND",
                "message": str(exc),
                "service": "data_platform",
                "stage": "human_correction",
                "request_id": scan_id,
                "retryable": False,
            },
        ) from exc

    return HumanCorrectionResponse(
        scan_id=updated_scan.id,
        status=ScanRecordStatus(updated_scan.status),
        reviewed_by=current_user.id,
        reviewed_at=updated_scan.reviewed_at or datetime.now(timezone.utc),
        message=f"Đã lưu kết quả hiệu đính thành công với trạng thái '{updated_scan.status}'.",
        corrected_drugs_count=len(body.corrected_drugs),
    )


@router.post("/reviews/{scan_id}/candidate", response_model=DatasetCandidateResponse)
async def mark_dataset_candidate(
    scan_id: str,
    body: DatasetCandidateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DatasetCandidateResponse:
    """
    Đánh dấu scan thành ứng viên dataset huấn luyện.
    Chỉ cho phép khi scan có trạng thái ACCEPTED hoặc REVIEWED (Ground Truth hợp lệ).
    """
    try:
        updated_scan = await data_capture_service.mark_dataset_candidate(
            db=db,
            scan_id=scan_id,
            candidate_req=body,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_DATASET_CANDIDATE_TRANSITION",
                "message": str(exc),
                "service": "data_platform",
                "stage": "dataset_candidate",
                "request_id": scan_id,
                "retryable": False,
            },
        ) from exc

    return DatasetCandidateResponse(
        scan_id=updated_scan.id,
        is_dataset_candidate=updated_scan.is_dataset_candidate,
        dataset_version=updated_scan.dataset_version or DEFAULT_DATASET_VERSION,
        dataset_tag=updated_scan.dataset_tag,
        status=ScanRecordStatus(updated_scan.status),
        message=f"Đã gắn cờ Dataset Candidate thành công cho phiên bản '{updated_scan.dataset_version}'.",
    )


@router.get("/datasets/export", response_model=DatasetExportResponse)
async def export_dataset(
    dataset_version: Optional[str] = Query(None, description="Lọc theo dataset version (mặc định tất cả ứng viên)"),
    status_filter: Optional[ScanRecordStatus] = Query(None, alias="status", description="Lọc theo trạng thái ('ACCEPTED' | 'REVIEWED')"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DatasetExportResponse:
    """
    Xuất tập dữ liệu Ground Truth hoàn chỉnh cho Active Learning / Model Fine-tuning.
    Bao gồm: Raw OCR items, Ground Truth do Reviewer xác nhận, và Model Lineage Metadata.
    """
    records = await data_capture_service.export_dataset(
        db=db,
        dataset_version=dataset_version,
        status=status_filter,
    )

    samples: List[DatasetExportItem] = []
    for rec in records:
        raw_ocr = [OCRItem(**item) for item in (rec.raw_ocr_result or [])]
        original_ai = [MappedDrugItem(**item) for item in (rec.normalized_result or [])]

        corrected_drugs = []
        if rec.corrected_payload and isinstance(rec.corrected_payload, dict):
            drugs_list = rec.corrected_payload.get("corrected_drugs", [])
            corrected_drugs = [HumanCorrectedDrug(**d) for d in drugs_list]

        lineage = PipelineLineageMetadata(**(rec.version_metadata or {}))

        samples.append(
            DatasetExportItem(
                scan_id=rec.id,
                source_type=rec.source_type,
                image_ref=rec.image_ref,
                raw_ocr_items=raw_ocr,
                ground_truth_drugs=corrected_drugs,
                original_ai_normalized_drugs=original_ai,
                quality_score=rec.quality_score,
                quality_flags=rec.quality_flags or [],
                reviewed_by=rec.reviewed_by,
                reviewed_at=rec.reviewed_at,
                lineage=lineage,
            )
        )

    return DatasetExportResponse(
        dataset_version=dataset_version or "all_candidates",
        exported_at=datetime.now(timezone.utc),
        total_samples=len(samples),
        samples=samples,
    )
