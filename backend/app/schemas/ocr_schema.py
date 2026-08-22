# Pydantic models cho kết quả OCR (ONNX PP-OCRv6) - Internal use
import logging
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic.alias_generators import to_camel

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# [P1/F3.2] Fail-safe Severity Clamp — AGENTS.md §B.4 / §5
# Mọi severity do LLM sinh ra phải bị ép về đúng 3 mức y khoa chuẩn
# HIGH / MEDIUM / LOW. Nguyên tắc fail-safe: giá trị lạ / rỗng / sai kiểu
# LUÔN nâng lên "HIGH" (thận trọng tối đa), KHÔNG BAO GIỜ hạ xuống "LOW"
# và KHÔNG raise exception làm chết pipeline. Mỗi lần clamp đều log warning
# để theo dõi tần suất LLM lệch chuẩn.
# ─────────────────────────────────────────────────────────────────────────────
SEVERITY_LEVELS = ("HIGH", "MEDIUM", "LOW")

# Alias thường gặp từ LLM → mức chuẩn gần nhất theo hướng thận trọng
_SEVERITY_ALIASES = {
    "CRITICAL": "HIGH",
    "SEVERE": "HIGH",
    "EXTREME": "HIGH",
    "URGENT": "HIGH",
    "DANGEROUS": "HIGH",
    "CONTRAINDICATED": "HIGH",
    "MODERATE": "MEDIUM",
    "WARNING": "MEDIUM",
    "CAUTION": "MEDIUM",
    "MINOR": "LOW",
    "INFO": "LOW",
    "SAFE": "LOW",
}


def clamp_severity(value: object) -> str:
    """Ép severity về HIGH/MEDIUM/LOW; giá trị bất định → HIGH (fail-safe)."""
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in SEVERITY_LEVELS:
            return normalized
        if normalized in _SEVERITY_ALIASES:
            clamped = _SEVERITY_ALIASES[normalized]
            logger.warning(
                "[severity-clamp] LLM trả alias '%s' → ép về '%s'", value, clamped
            )
            return clamped
        logger.warning(
            "[severity-clamp] LLM trả severity không chuẩn %r → ép lên 'HIGH' (fail-safe)",
            value,
        )
        return "HIGH"
    logger.warning(
        "[severity-clamp] LLM trả severity sai kiểu %r → ép lên 'HIGH' (fail-safe)", value
    )
    return "HIGH"


class OCRItem(BaseModel):
    text: str = Field(..., description="Chuỗi văn bản nhận diện bởi OCR")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Độ tin cậy nhận diện (0.0 -> 1.0)")
    box: List[float] = Field(default=[], description="Tọa độ bounding box [x1, y1, x2, y2]")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class MedicineScanResult(BaseModel):
    engine: str = Field("PP-OCRv6-ONNX", description="OCR engine đã sử dụng")
    source_type: str = Field("prescription", description="Nguồn ảnh: 'prescription' hoặc 'packaging'")
    items: List[OCRItem] = Field(..., description="Danh sách các dòng văn bản nhận diện")
    latency_ms: int = Field(..., ge=0, description="Thời gian xử lý (milliseconds)")
    sla_exceeded: bool = Field(False, description="True nếu vượt SLA xử lý nội bộ")
    image_width: int = Field(..., ge=0)
    image_height: int = Field(..., ge=0)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


# ─────────────────────────────────────────────────────────────────────────────
# Full Pipeline Response Models (Public API)
# ─────────────────────────────────────────────────────────────────────────────

class MappedDrugItem(BaseModel):
    """Thuốc đã được map từ OCR raw text -> Drug Database."""
    drug_id: Optional[str] = None
    brand_name: str
    active_ingredient: Optional[str] = None
    strength: str
    dosage_instruction: Optional[str] = None
    category: Optional[str] = None
    max_daily_dosage: Optional[str] = None
    warnings: List[str] = []
    confidence_score: float
    is_verified: bool
    match_method: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


# NOTE [Audit-S3 / P0 / F3.1]: Các model Clinical bên dưới CỐ Ý không cấu hình
# alias_generator=to_camel nhằm bảo toàn wire-format lịch sử của payload
# `clinical_assessment` (snake_case) mà frontend đang tiêu thụ, trong khi
# envelope ngoài (FullScanResponse, MappedDrugItem, OCRItem, ClinicalAlertSummary)
# vẫn camelCase. Bật alias ở đây sẽ âm thầm đổi contract §3.A — không làm nếu
# chưa có quyết định đồng bộ frontend từ Architect.
class DrugInteractionAlert(BaseModel):
    """Cảnh báo tương tác thuốc - thuốc (nguồn: LLM hoặc rule-engine)."""

    severity: Literal["HIGH", "MEDIUM", "LOW"]
    title: str
    description: str
    recommendation: str
    interacting_drugs: List[str] = []
    evidence_level: Optional[str] = None

    @field_validator("severity", mode="before")
    @classmethod
    def _severity_fail_safe(cls, v: object) -> str:
        return clamp_severity(v)


class DrugConditionAlert(BaseModel):
    """Cảnh báo thuốc - bệnh nền (nguồn: LLM hoặc rule-engine)."""

    severity: Literal["HIGH", "MEDIUM", "LOW"]
    title: str
    description: str
    recommendation: str
    drug_name: str
    condition: str
    evidence_level: Optional[str] = None

    @field_validator("severity", mode="before")
    @classmethod
    def _severity_fail_safe(cls, v: object) -> str:
        return clamp_severity(v)


class OverdoseAlert(BaseModel):
    """Cảnh báo quá liều / trùng lặp hoạt chất (nguồn: LLM hoặc rule-engine)."""

    severity: Literal["HIGH", "MEDIUM", "LOW"]
    title: str
    description: str
    recommendation: str
    ingredient: str
    total_daily_mg: float
    max_safe_mg: Optional[float] = None

    @field_validator("severity", mode="before")
    @classmethod
    def _severity_fail_safe(cls, v: object) -> str:
        return clamp_severity(v)


class ClinicalAssessmentResponse(BaseModel):
    drug_drug_interactions: List[DrugInteractionAlert] = []
    drug_condition_interactions: List[DrugConditionAlert] = []
    overdose_duplication_alerts: List[OverdoseAlert] = []
    clinical_recommendations: List[str] = []
    monitoring_parameters: List[str] = []
    disclaimer: str = "Kết quả này được tạo bởi AI và chỉ mang tính tham khảo. Vui lòng tham khảo ý kiến bác sĩ/dược sĩ trước khi thay đổi phác đồ điều trị."


class ClinicalAlertSummary(BaseModel):
    total_alerts: int
    high_count: int
    medium_count: int
    low_count: int
    drug_drug_interactions: int
    drug_condition_interactions: int
    overdose_duplication: int

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class FullScanResponse(BaseModel):
    """Full Pipeline Response: Raw OCR + Mapped Drugs + Clinical Assessment."""
    engine: str
    source_type: str
    raw_ocr_items: List[OCRItem]
    ocr_latency_ms: int
    sla_exceeded: bool
    image_width: int
    image_height: int
    mapped_drugs: List[MappedDrugItem]
    clinical_assessment: Optional[ClinicalAssessmentResponse] = None
    clinical_summary: Optional[ClinicalAlertSummary] = None
    total_latency_ms: int
    normalization_latency_ms: int
    clinical_latency_ms: int

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)