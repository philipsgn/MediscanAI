"""
data_capture_service.py

Service Quản lý Lưu trữ Dữ liệu Scan, Review Queue (HITL),
và Ground Truth Dataset cho Mediscan AI Data Platform.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning import DEFAULT_DATASET_VERSION, get_current_pipeline_lineage
from app.models.data_capture import ScanRecordModel
from app.schemas.data_platform_schema import (
    DatasetCandidateRequest,
    HumanCorrectionRequest,
    ScanRecordStatus,
)
from app.services.data_quality_service import data_quality_service

logger = logging.getLogger(__name__)


def _to_serializable(items: Any) -> Any:
    """Helper chuyển đổi Pydantic models hoặc dataclasses thành dict để lưu JSON."""
    if items is None:
        return None
    if isinstance(items, list):
        return [_to_serializable(x) for x in items]
    if hasattr(items, "model_dump"):
        return items.model_dump()
    if hasattr(items, "dict"):
        return items.dict()
    if isinstance(items, dict):
        return {k: _to_serializable(v) for k, v in items.items()}
    return items


class DataCaptureService:
    """Service chịu trách nhiệm lưu trữ lineage, điều phối review queue và tạo dataset."""

    async def capture_scan(
        self,
        db: AsyncSession,
        request_id: str,
        user_id: Optional[str],
        source_type: str,
        image_bytes: bytes,
        raw_ocr_items: List[Any],
        mapped_drugs: List[Any],
        clinical_assessment: Optional[Any] = None,
    ) -> Optional[ScanRecordModel]:
        """
        Lưu vết scan vào bảng `scan_records` kèm version lineage và quality evaluation.
        Có cơ chế Safe Degradation (không ném Exception làm ngắt quãng response của user).
        """
        try:
            image_ref = hashlib.sha256(image_bytes).hexdigest()
            quality_score, quality_flags, initial_status = data_quality_service.evaluate_scan(
                raw_ocr_items=raw_ocr_items,
                mapped_drugs=mapped_drugs,
                clinical_assessment=clinical_assessment,
            )
            lineage = get_current_pipeline_lineage()

            scan_record = ScanRecordModel(
                request_id=request_id,
                user_id=user_id,
                source_type=source_type,
                image_ref=f"sha256:{image_ref}",
                status=initial_status.value,
                quality_score=quality_score,
                quality_flags=quality_flags,
                raw_ocr_result=_to_serializable(raw_ocr_items) or [],
                normalized_result=_to_serializable(mapped_drugs) or [],
                clinical_result=_to_serializable(clinical_assessment),
                corrected_payload=None,
                is_dataset_candidate=False,
                dataset_version=None,
                dataset_tag=None,
                version_metadata=lineage.model_dump(),
            )

            db.add(scan_record)
            await db.commit()
            await db.refresh(scan_record)

            logger.info(
                "[DATA_CAPTURE_OK] scan_id=%s request_id=%s status=%s quality=%.2f flags=%s",
                scan_record.id, request_id, scan_record.status, quality_score, quality_flags,
            )
            return scan_record

        except Exception as exc:  # noqa: BLE001
            # Safe degradation: Log error nhưng không làm sập luồng chính của người dùng
            logger.error(
                "[DATA_CAPTURE_FAILED] request_id=%s error=%s (Safe Degradation Active)",
                request_id, exc, exc_info=True,
            )
            try:
                await db.rollback()
            except Exception:  # noqa: S110
                pass
            return None

    async def get_review_queue(
        self,
        db: AsyncSession,
        status: Optional[ScanRecordStatus] = None,
        source_type: Optional[str] = None,
        is_dataset_candidate: Optional[bool] = None,
        min_quality: Optional[float] = None,
        max_quality: Optional[float] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[ScanRecordModel]]:
        """Lấy danh sách scan trong Review Queue kèm bộ lọc và phân trang."""
        stmt = select(ScanRecordModel)

        if status is not None:
            stmt = stmt.where(ScanRecordModel.status == status.value)
        if source_type is not None:
            stmt = stmt.where(ScanRecordModel.source_type == source_type)
        if is_dataset_candidate is not None:
            stmt = stmt.where(ScanRecordModel.is_dataset_candidate == is_dataset_candidate)
        if min_quality is not None:
            stmt = stmt.where(ScanRecordModel.quality_score >= min_quality)
        if max_quality is not None:
            stmt = stmt.where(ScanRecordModel.quality_score <= max_quality)

        # Đếm tổng số bản ghi khớp điều kiện
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one_or_none() or 0

        # Lấy danh sách bản ghi
        stmt = stmt.order_by(ScanRecordModel.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        items = list(result.scalars().all())

        return total, items

    async def get_scan_record(self, db: AsyncSession, scan_id: str) -> Optional[ScanRecordModel]:
        """Truy xuất chi tiết một scan record theo id."""
        stmt = select(ScanRecordModel).where(ScanRecordModel.id == scan_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def submit_human_correction(
        self,
        db: AsyncSession,
        scan_id: str,
        reviewer_id: str,
        correction_req: HumanCorrectionRequest,
    ) -> ScanRecordModel:
        """
        Ghi nhận chỉnh sửa của Reviewer (HITL).
        QUY TẮC BẢO VỆ: Tuyệt đối không ghi đè raw_ocr_result hay normalized_result gốc của AI.
        """
        scan = await self.get_scan_record(db, scan_id)
        if not scan:
            raise ValueError(f"Scan record với ID '{scan_id}' không tồn tại.")

        # Lưu payload hiệu đính riêng biệt
        corrected_payload = {
            "corrected_drugs": [d.model_dump() for d in correction_req.corrected_drugs],
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "reviewer_id": reviewer_id,
            "decision": correction_req.decision.value,
            "review_notes": correction_req.review_notes,
        }

        scan.corrected_payload = corrected_payload
        scan.status = correction_req.decision.value
        scan.reviewed_by = reviewer_id
        scan.reviewed_at = datetime.now(timezone.utc)
        scan.review_notes = correction_req.review_notes

        await db.commit()
        await db.refresh(scan)

        logger.info(
            "[HUMAN_CORRECTION_SAVED] scan_id=%s decision=%s reviewer=%s drugs_count=%d",
            scan.id, scan.status, reviewer_id, len(correction_req.corrected_drugs),
        )
        return scan

    async def mark_dataset_candidate(
        self,
        db: AsyncSession,
        scan_id: str,
        candidate_req: DatasetCandidateRequest,
    ) -> ScanRecordModel:
        """
        Đánh dấu scan làm ứng viên dataset cho Active Learning / Fine-tuning.
        Chỉ cho phép khi scan đã được kiểm duyệt hợp lệ (ACCEPTED hoặc REVIEWED).
        """
        scan = await self.get_scan_record(db, scan_id)
        if not scan:
            raise ValueError(f"Scan record với ID '{scan_id}' không tồn tại.")

        if scan.status not in {ScanRecordStatus.ACCEPTED.value, ScanRecordStatus.REVIEWED.value}:
            raise ValueError(
                f"Không thể tạo Dataset Candidate từ scan có trạng thái '{scan.status}'. "
                "Chỉ các scan đã được kiểm duyệt (ACCEPTED hoặc REVIEWED) mới đủ điều kiện tạo Ground Truth.",
            )

        scan.is_dataset_candidate = True
        scan.dataset_version = candidate_req.dataset_version or scan.dataset_version or DEFAULT_DATASET_VERSION
        scan.dataset_tag = candidate_req.dataset_tag or scan.dataset_tag

        await db.commit()
        await db.refresh(scan)

        logger.info(
            "[DATASET_CANDIDATE_MARKED] scan_id=%s dataset_version=%s tag=%s",
            scan.id, scan.dataset_version, scan.dataset_tag,
        )
        return scan

    async def export_dataset(
        self,
        db: AsyncSession,
        dataset_version: Optional[str] = None,
        status: Optional[ScanRecordStatus] = None,
    ) -> List[ScanRecordModel]:
        """Truy xuất toàn bộ các scan đã đánh dấu dataset candidate kèm lineage đầy đủ."""
        stmt = select(ScanRecordModel).where(ScanRecordModel.is_dataset_candidate.is_(True))

        if dataset_version:
            stmt = stmt.where(ScanRecordModel.dataset_version == dataset_version)
        if status:
            stmt = stmt.where(ScanRecordModel.status == status.value)

        stmt = stmt.order_by(ScanRecordModel.created_at.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())


data_capture_service = DataCaptureService()
