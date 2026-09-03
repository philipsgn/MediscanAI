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
    DatasetProvenanceInfo,
    DosageCheckResult,
    DrugConditionAlert,
    DrugCoverageItem,
    DrugCoverageStatus,
    DrugInteractionAlert,
    EvaluationResponse,
    ExtractedDrugItem,
    FullScanResponse,
    InteractionAlert,
    MappedDrugItem,
    MedicineScanResult,
    OCRItem,
    OCRPipelineMetrics,
    OverdoseAlert,
    ScanEvaluationResponse,
)

class UserProfile(BaseModel):
    age: int = Field(..., ge=0, le=120, description="Tuổi bệnh nhân")
    weight_kg: Optional[float] = Field(None, ge=0, le=300, description="Cân nặng (kg)")
    height_cm: Optional[float] = Field(None, ge=0, le=250, description="Chiều cao (cm)")
    gender: Optional[str] = Field(None, description="'male' | 'female' | 'other'")
    conditions: List[str] = Field(default=[], description="Danh sách mã/tên bệnh nền (Ví dụ: Hypertension, Diabetes)")
    allergies: List[str] = Field(default=[], description="Danh sách hoạt chất dị ứng")
    is_pregnant: Optional[bool] = Field(default=False, description="Đang mang thai (chỉ áp dụng nữ giới)")
    is_breastfeeding: Optional[bool] = Field(default=False, description="Đang cho con bú (chỉ áp dụng nữ giới)")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

class DrugItem(BaseModel):
    brand_name: str = Field(..., description="Tên thương mại trích xuất được")
    active_ingredient: Optional[str] = Field(None, description="Tên hoạt chất sau khi chuẩn hóa")
    strength: Optional[str] = Field(default="", description="Hàm lượng (Ví dụ: 500mg, 10ml, hoặc để trống)")
    dosage_instruction: Optional[str] = Field(None, description="Hướng dẫn liều dùng")
    confidence_score: float = Field(1.0, ge=0.0, le=1.0, description="Độ tin cậy trích xuất của AI (0.0 -> 1.0)")
    is_verified: bool = Field(False, description="Người dùng đã xác nhận tính chính xác chưa")
    variants: List[str] = Field(default=[], description="Danh sách biến thể hàm lượng chuẩn từ CSDL")
    # Extended fields from Drug Database
    drug_id: Optional[str] = Field(None, description="ID thuốc trong Database chuẩn")
    category: Optional[str] = Field(None, description="Nhóm điều trị (VD: Kháng sinh, Giảm đau...)")
    max_daily_dosage: Optional[str] = Field(None, description="Liều tối đa/ngày từ DB (VD: 4000mg)")
    warnings: List[str] = Field(default=[], description="Cảnh báo/Chống chỉ định từ DB")
    match_method: Optional[str] = Field(
        None,
        description=(
            "Cách khớp DB [P2/F3.4]: exact | fuzzy | ingredient_fallback | "
            "openfda | openfda_ingredient | None (không match)"
        ),
    )
    # [F3.7] Cảnh báo nhẹ: hàm lượng user/OCR khác DB chuẩn (non-blocking hint
    # cho Human-in-the-Loop). KHÔNG thay đổi công thức gán strength ở _apply_db_info.
    strength_mismatch_warning: Optional[str] = Field(
        None,
        description="Cảnh báo hàm lượng (strength) nhập vào khác với DB chuẩn",
    )

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

class Prescription(BaseModel):
    source_type: str = Field(..., description="Nguồn trích xuất: 'prescription' hoặc 'packaging'")
    items: List[DrugItem] = Field(..., description="Danh sách các loại thuốc trích xuất được")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class DrugSearchResult(BaseModel):
    """[S4-Closeout/F4.3] Kết quả RÚT GỌN cho autocomplete từ điển thuốc.

    Chỉ trả các trường UI dropdown cần — KHÔNG trả full DrugItem (tránh lộ
    warnings/max_daily_dosage không cần thiết cho gợi ý nhập liệu).
    Wire-format camelCase khớp `IDrugSearchResult` phía frontend (§3.A)."""
    drug_id: str = Field(..., description="ID thuốc trong DB chuẩn (hoặc openfda:<uuid>)")
    brand_name: str = Field(..., description="Tên thương mại")
    active_ingredient: Optional[str] = Field(None, description="Hoạt chất gốc chuẩn hóa")
    strength: str = Field("", description="Hàm lượng")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class DrugEvaluationRequest(BaseModel):
    user_profile: Optional[UserProfile] = Field(None, description="Hồ sơ bệnh nhân (tuổi, bệnh nền, dị ứng)")
    drugs: List[DrugItem] = Field(..., description="Danh sách các thuốc trong tủ thuốc/đơn cần đánh giá")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

# (Khối re-export OCR schemas cũ đã gộp vào import canonical ở đầu file — P0/F3.1.)

from app.schemas.user_schema import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenPayload,
)
from app.schemas.user_profile_schema import (
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileResponse,
)
from app.schemas.history_reminder_schema import (
    ScanHistoryCreate,
    ScanHistoryResponse,
    ReminderCreate,
    ReminderUpdate,
    ReminderLogCreate,
    ReminderLogItem,
    ReminderResponse,
    AdherenceStats,
)

__all__ = [
    "UserProfile",
    "DrugItem",
    "Prescription",
    "InteractionAlert",
    "EvaluationResponse",
    "DrugEvaluationRequest",
    "MedicineScanResult",
    "OCRItem",
    "OCRPipelineMetrics",
    "MappedDrugItem",
    "DrugInteractionAlert",
    "DrugConditionAlert",
    "OverdoseAlert",
    "ExtractedDrugItem",
    "ClinicalAssessmentResponse",
    "ClinicalAlertSummary",
    "FullScanResponse",
    "UserRegister",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "TokenPayload",
    "UserProfileCreate",
    "UserProfileUpdate",
    "UserProfileResponse",
    "ScanHistoryCreate",
    "ScanHistoryResponse",
    "ReminderCreate",
    "ReminderUpdate",
    "ReminderLogCreate",
    "ReminderLogItem",
    "ReminderResponse",
    "AdherenceStats",
]