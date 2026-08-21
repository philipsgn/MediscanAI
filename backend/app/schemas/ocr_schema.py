# Pydantic models cho kết quả OCR (ONNX PP-OCRv6) - Internal use
from typing import List
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


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


class DrugInteractionAlert(BaseModel):
    severity: str
    title: str
    description: str
    recommendation: str
    interacting_drugs: List[str] = []
    evidence_level: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class DrugConditionAlert(BaseModel):
    severity: str
    title: str
    description: str
    recommendation: str
    drug_name: str
    condition: str
    evidence_level: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class OverdoseAlert(BaseModel):
    severity: str
    title: str
    description: str
    recommendation: str
    ingredient: str
    total_daily_mg: float
    max_safe_mg: Optional[float] = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ClinicalAssessmentResponse(BaseModel):
    drug_drug_interactions: List[DrugInteractionAlert] = []
    drug_condition_interactions: List[DrugConditionAlert] = []
    overdose_duplication_alerts: List[OverdoseAlert] = []
    clinical_recommendations: List[str] = []
    monitoring_parameters: List[str] = []
    disclaimer: str = "Kết quả này được tạo bởi AI và chỉ mang tính tham khảo. Vui lòng tham khảo ý kiến bác sĩ/dược sĩ trước khi thay đổi phác đồ điều trị."

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


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