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
    weight_kg: Optional[float] = Field(None, ge=0, le=300, description="Cân nặng (kg)")
    height_cm: Optional[float] = Field(None, ge=0, le=250, description="Chiều cao (cm)")
    gender: Optional[str] = Field(None, description="'male' | 'female' | 'other'")
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
    """Response chính — 4 Layer (Overdose, Drug-Drug, Drug-Condition, Dosage).

    [Task 5.5] Đã mở rộng so với ban đầu: bổ sung `dosage_checks`
    (Layer 4 — kết quả đối chiếu liều) và `final_summary`
    (tóm tắt tổng hợp toàn bộ cảnh báo — yêu cầu AGENTS §3.B.4/DoD #5).
    """
    total_drugs_analyzed: int
    alerts: List[InteractionAlert]
    schedule_suggestions: List[str] = Field(default=[], description="Gợi ý phân chia lịch uống thuốc an toàn")
    # [Task 5.5] Layer 4 + Final Summary
    dosage_checks: List["DosageCheckResult"] = Field(default=[], description="Kết quả Layer 4 - đối chiếu liều dùng")
    final_summary: str = Field("", description="Tóm tắt tổng quan tình trạng và lời khuyên cuối cùng cho User")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class DosageCheckResult(BaseModel):
    """Kết quả Layer 4: Đối chiếu liều thực tế (kê toa hoặc tự nhập) với liều
    khuyến cáo chuẩn theo population (tuổi/bệnh nền). Schema khớp 100%
    ARCHITECTURE.md §5.1 + IDosageCheckResult phía frontend (§3.A.2)."""
    drug_name: str = Field(..., description="Tên thuốc được kiểm tra")
    prescribed_or_input_dosage: str = Field(..., description="Liều kê toa/người dùng nhập (chuỗi gốc)")
    recommended_dosage: str = Field(..., description="Liều khuyến cáo tham khảo (theo population)")
    is_appropriate: Optional[bool] = Field(
        default=None,
        description="True=phù hợp, False=chênh lệch, None=không đủ dữ liệu/trẻ em ngoài phạm vi",
    )
    note: str = Field(default="", description="Ghi chú theo mẫu an toàn — tuyệt đối tuân thủ đứng dẫn ngôn từ (§5)")

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
    "MappedDrugItem",
    "DrugInteractionAlert",
    "DrugConditionAlert",
    "OverdoseAlert",
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