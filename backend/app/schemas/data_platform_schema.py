"""
data_platform_schema.py

Pydantic Schemas cho Data-Centric AI Platform:
- Review Queue & Data Quality Management
- Human-in-the-Loop (HITL) Correction with Optimistic Locking
- Dataset Candidate & Active Learning Lineage & Snapshot Integrity
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.core.versioning import PipelineLineageMetadata
from app.schemas.ocr_schema import (
    EvaluationResponse,
    MappedDrugItem,
    OCRItem,
)


class ScanRecordStatus(str, Enum):
    PROCESSED = "PROCESSED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    IN_REVIEW = "IN_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    # Legacy alias for backward compatibility (treated as non-ground truth)
    REVIEWED = "REVIEWED"


# ─────────────────────────────────────────────────────────────────────────────
# State Transition Semantics & Validator
# ─────────────────────────────────────────────────────────────────────────────

VALID_STATE_TRANSITIONS: Dict[ScanRecordStatus, List[ScanRecordStatus]] = {
    ScanRecordStatus.PROCESSED: [
        ScanRecordStatus.REVIEW_REQUIRED,
        ScanRecordStatus.IN_REVIEW,
        ScanRecordStatus.ACCEPTED,
        ScanRecordStatus.REJECTED,
    ],
    ScanRecordStatus.REVIEW_REQUIRED: [
        ScanRecordStatus.IN_REVIEW,
        ScanRecordStatus.ACCEPTED,
        ScanRecordStatus.REJECTED,
    ],
    ScanRecordStatus.IN_REVIEW: [
        ScanRecordStatus.ACCEPTED,
        ScanRecordStatus.REJECTED,
        ScanRecordStatus.REVIEW_REQUIRED,
    ],
    ScanRecordStatus.ACCEPTED: [
        ScanRecordStatus.ACCEPTED,  # Re-correction / update ground truth
        ScanRecordStatus.REJECTED,
    ],
    ScanRecordStatus.REJECTED: [
        ScanRecordStatus.IN_REVIEW,  # Re-opened for review
    ],
    ScanRecordStatus.REVIEWED: [
        ScanRecordStatus.ACCEPTED,
        ScanRecordStatus.REJECTED,
        ScanRecordStatus.IN_REVIEW,
    ],
}


def validate_state_transition(current_status: ScanRecordStatus, target_status: ScanRecordStatus) -> None:
    """Kiểm tra tính hợp lệ của việc chuyển trạng thái trong State Machine."""
    allowed = VALID_STATE_TRANSITIONS.get(current_status, [])
    if target_status not in allowed and target_status != current_status:
        raise ValueError(
            f"Chuyển trạng thái không hợp lệ: Không thể chuyển từ '{current_status.value}' "
            f"sang '{target_status.value}'. Các trạng thái cho phép: {[s.value for s in allowed]}",
        )


class HumanCorrectedDrug(BaseModel):
    """Một mục thuốc được chuyên viên hiệu đính trong bước HITL."""
    brand_name: str = Field(..., description="Tên biệt dược chuẩn hóa")
    active_ingredient: Optional[str] = Field(None, description="Hoạt chất gốc")
    strength: Optional[str] = Field(None, description="Hàm lượng / nồng độ")
    dosage_instruction: Optional[str] = Field(None, description="Hướng dẫn liều dùng")
    notes: Optional[str] = Field(None, description="Ghi chú chi tiết cho mục thuốc này")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class HumanCorrectionRequest(BaseModel):
    """Request submit chỉnh sửa từ Reviewer."""
    decision: ScanRecordStatus = Field(
        ...,
        description="Quyết định phê duyệt: ACCEPTED (chấp nhận ground truth), REJECTED (ảnh rác/không đọc được), IN_REVIEW (đang xử lý)",
    )
    expected_version: Optional[int] = Field(
        None,
        description="Phiên bản optimistic locking mong đợi để phòng chống Lost Update khi concurrent review",
    )
    corrected_drugs: List[HumanCorrectedDrug] = Field(
        default_factory=list,
        description="Danh sách các loại thuốc đã được hiệu đính chính xác",
    )
    review_notes: Optional[str] = Field(None, description="Lý do / nhận xét của reviewer")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class HumanCorrectionResponse(BaseModel):
    """Phản hồi sau khi lưu trữ Human Correction."""
    scan_id: str
    status: ScanRecordStatus
    version: int
    reviewed_by: str
    reviewed_at: datetime
    message: str
    corrected_drugs_count: int

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ScanReviewSummaryItem(BaseModel):
    """Item tóm tắt trong danh sách hàng đợi Review."""
    scan_id: str
    request_id: str
    user_id: Optional[str] = None
    source_type: str
    image_sha256: str
    image_storage_ref: str
    image_ref: str
    status: ScanRecordStatus
    quality_score: float
    quality_flags: List[str]
    is_dataset_candidate: bool
    dataset_version: Optional[str] = None
    version: int
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ScanReviewListResponse(BaseModel):
    """Danh sách các scan cần review kèm phân trang."""
    total: int
    limit: int
    offset: int
    items: List[ScanReviewSummaryItem]

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ScanReviewDetailResponse(BaseModel):
    """Chi tiết toàn bộ scan artifacts phục vụ giao diện Reviewer."""
    scan_id: str
    request_id: str
    user_id: Optional[str] = None
    source_type: str
    image_sha256: str
    image_storage_ref: str
    image_ref: str
    image_available: bool = Field(True, description="Ảnh vật lý có thể truy xuất từ storage disk/cloud hay không")
    status: ScanRecordStatus
    quality_score: float
    quality_flags: List[str]
    raw_ocr_result: List[OCRItem]
    normalized_result: List[MappedDrugItem]
    clinical_result: Optional[EvaluationResponse] = None
    corrected_payload: Optional[Dict[str, Any]] = None
    is_dataset_candidate: bool
    dataset_version: Optional[str] = None
    dataset_tag: Optional[str] = None
    version_metadata: PipelineLineageMetadata
    version: int
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class DatasetCandidateRequest(BaseModel):
    """Request đánh dấu scan thành ứng viên dataset huấn luyện."""
    dataset_version: Optional[str] = Field(None, description="Phiên bản dataset, ví dụ 'mediscan-v1.0'")
    dataset_tag: Optional[str] = Field(None, description="Tag phân loại, ví dụ 'vietnamese_packaging_hard_cases'")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class DatasetCandidateResponse(BaseModel):
    """Phản hồi sau khi gán cờ Dataset Candidate."""
    scan_id: str
    is_dataset_candidate: bool
    dataset_version: str
    dataset_tag: Optional[str] = None
    status: ScanRecordStatus
    version: int
    message: str

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class DatasetExportItem(BaseModel):
    """Một mẫu dữ liệu trong dataset xuất ra cho Active Learning / Fine-tuning."""
    scan_id: str
    source_type: str
    image_sha256: str
    image_storage_ref: str
    image_available: bool
    raw_ocr_items: List[OCRItem]
    ground_truth_drugs: List[HumanCorrectedDrug]
    original_ai_normalized_drugs: List[MappedDrugItem]
    quality_score: float
    quality_flags: List[str]
    version: int
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    lineage: PipelineLineageMetadata

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class DatasetExportResponse(BaseModel):
    """Tập dữ liệu Ground Truth hoàn chỉnh xuất ra kèm Lineage Metadata và Snapshot Hash."""
    dataset_version: str
    snapshot_hash: str = Field(..., description="SHA-256 snapshot hash bảo đảm tính tái lập của dataset export")
    exported_at: datetime
    total_samples: int
    samples: List[DatasetExportItem]

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class DataPlatformErrorEntry(BaseModel):
    """Chi tiết lỗi capture thất bại gần đây phục vụ giám sát."""
    request_id: str
    timestamp: str
    error: str
    error_type: str

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class DataPlatformMetricsResponse(BaseModel):
    """Metrics giám sát độ bền vững và tỷ lệ thành công của Data Capture subsystem."""
    total_captures: int
    failed_captures: int
    success_rate: float
    recent_errors: List[DataPlatformErrorEntry]

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
