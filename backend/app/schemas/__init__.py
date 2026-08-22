# Data Schemas cho Backend Mediscan AI (Pydantic v2) - package init.
# Tuân thủ 100% Data Contract định nghĩa trong ARCHITECTURE.md §5.1 & §5.2
# Kế thừa nguyên vẹn từ schemas.py, giữ import `from app.schemas import X`.
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic.alias_generators import to_camel

# Canonical clinical models + fail-safe clamp [P0/P1 — Audit Stage 3]
from app.schemas.ocr_schema import (  # noqa: E402
    clamp_severity,
    ClinicalAlertSummary,
    ClinicalAssessmentResponse,
    DrugConditionAlert,
    DrugInteractionAlert,
    FullScanResponse,
    MappedDrugItem,
    MedicineScanResult,
    OCRItem,
    OverdoseAlert,
)

class UserProfile(BaseModel):
    age: int = Field(..., ge=0, le=120, description="Tuổi bệnh nhân")
    conditions: List[str] = Field(default=[], description="Danh sách mã/tên bệnh nền (Ví dụ: Hypertension, Diabetes)")
    allergies: List[str] = Field(default=[], description="Danh sách hoạt chất dị ứng")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

class DrugItem(BaseModel):
    brand_name: str = Field(..., description="Tên thương mại trích xuất được")
    active_ingredient: Optional[str] = Field(None, description="Tên hoạt chất sau khi chuẩn hóa")
    strength: str = Field(..., description="Hàm lượng (Ví dụ: 500mg, 10ml)")
    dosage_instruction: Optional[str] = Field(None, description="Hướng dẫn liều dùng")
    confidence_score: float = Field(1.0, ge=0.0, le=1.0, description="Độ tin cậy trích xuất của AI (0.0 -> 1.0)")
    is_verified: bool = Field(False, description="Người dùng đã xác nhận tính chính xác chưa")
    # Extended fields from Drug Database
    drug_id: Optional[str] = Field(None, description="ID thuốc trong Database chuẩn")
    category: Optional[str] = Field(None, description="Nhóm điều trị (VD: Kháng sinh, Giảm đau...)")
    max_daily_dosage: Optional[str] = Field(None, description="Liều tối đa/ngày từ DB (VD: 4000mg)")
    warnings: List[str] = Field(default=[], description="Cảnh báo/Chống chỉ định từ DB")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

class Prescription(BaseModel):
    source_type: str = Field(..., description="Nguồn trích xuất: 'prescription' hoặc 'packaging'")
    items: List[DrugItem] = Field(..., description="Danh sách các loại thuốc trích xuất được")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

class InteractionAlert(BaseModel):
    """Alert hợp nhất cho báo cáo đánh giá — severity là NGUỒN QUYẾT ĐỊNH cuối cùng
    thuộc rule-engine Stage 5; LLM chỉ enrich văn bản [F3.3]. Giá trị lạ từ LLM
    được fail-safe clamp về HIGH, không bao giờ hạ xuống LOW [F3.2]."""

    severity: Literal["HIGH", "MEDIUM", "LOW"]
    title: str = Field(..., description="Tiêu đề cảnh báo ngắn gọn")
    description: str = Field(..., description="Chi tiết tương tác/xung đột thuốc")
    recommendation: str = Field(..., description="Lời khuyên y tế hướng xử lý")

    @field_validator("severity", mode="before")
    @classmethod
    def _severity_fail_safe(cls, v: object) -> str:
        return clamp_severity(v)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

class EvaluationResponse(BaseModel):
    total_drugs_analyzed: int
    alerts: List[InteractionAlert]
    schedule_suggestions: List[str] = Field(default=[], description="Gợi ý phân chia lịch uống thuốc an toàn")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

class DrugEvaluationRequest(BaseModel):
    user_profile: Optional[UserProfile] = Field(None, description="Hồ sơ bệnh nhân (tuổi, bệnh nền, dị ứng)")
    drugs: List[DrugItem] = Field(..., description="Danh sách các thuốc trong tủ thuốc/đơn cần đánh giá")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

# (Khối re-export OCR schemas cũ đã gộp vào import canonical ở đầu file — P0/F3.1.)

__all__ = [
    "UserProfile",
    "DrugItem",
    "Prescription",
    "InteractionAlert",
    "EvaluationResponse",
    "DrugEvaluationRequest",
    "MedicineScanResult",
    "OCRItem",
    "MappedDrugItem",
    "DrugInteractionAlert",
    "DrugConditionAlert",
    "OverdoseAlert",
    "ClinicalAssessmentResponse",
    "ClinicalAlertSummary",
    "FullScanResponse",
]