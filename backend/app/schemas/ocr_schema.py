# Pydantic models cho kết quả OCR (ONNX PP-OCRv6) - Internal use
import logging
from typing import Any, Dict, List, Literal, Optional

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

class ExtractedDrugItem(BaseModel):
    """Unified Clinical Feature Schema cho cả 2 luồng Prescription & Packaging."""
    id: str = Field(..., description="ID định danh duy nhất cho item thuốc trích xuất")
    drug_name: str = Field(..., description="Tên biệt dược hoặc tên thuốc gốc")
    active_ingredient: Optional[str] = Field(None, description="Tên hoạt chất chuẩn hóa")
    strength: Optional[str] = Field(None, description="Hàm lượng (VD: 500mg)")
    dosage_form: Optional[str] = Field(None, description="Dạng bào chế (viên, gói, chai...)")
    dosage_instruction: Optional[str] = Field(None, description="Hướng dẫn liều dùng (VD: Sáng 1v, Tối 1v sau ăn)")
    time_slots: List[str] = Field(default=[], description="Các buổi uống thuốc: ['morning', 'noon', 'afternoon', 'evening']")
    slot_times: Dict[str, str] = Field(default={}, description="Khung giờ cụ thể {'morning': '08:00', 'evening': '20:00'}")
    duration_days: Optional[int] = Field(None, description="Số ngày uống thuốc")
    start_date: Optional[str] = Field(None, description="Ngày bắt đầu (YYYY-MM-DD)")
    is_time_extracted: bool = Field(False, description="True nếu OCR trích xuất được giờ, False nếu cần nhập tay")
    source_stream: str = Field("prescription", description="Nguồn trích xuất: 'prescription' hoặc 'packaging'")

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


class DosageCheckResult(BaseModel):
    """Kết quả Layer 4: Đối chiếu liều thực tế (kê toa hoặc tự nhập) với liều
    khuyến cáo chuẩn theo population (tuổi/bệnh nền)."""
    drug_name: str = Field(..., description="Tên thuốc được kiểm tra")
    prescribed_or_input_dosage: str = Field(..., description="Liều kê toa/người dùng nhập (chuỗi gốc)")
    recommended_dosage: str = Field(..., description="Liều khuyến cáo tham khảo (theo population)")
    is_appropriate: Optional[bool] = Field(
        default=None,
        description="True=phù hợp, False=chênh lệch, None=không đủ dữ liệu/trẻ em ngoài phạm vi",
    )
    note: str = Field(default="", description="Ghi chú theo mẫu an toàn")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class EvaluationResponse(BaseModel):
    """Response chính — 4 Layer (Overdose, Drug-Drug, Drug-Condition, Dosage)."""
    total_drugs_analyzed: int = 0
    alerts: List[InteractionAlert] = []
    schedule_suggestions: List[str] = Field(default=[], description="Gợi ý phân chia lịch uống thuốc an toàn")
    dosage_checks: List[DosageCheckResult] = Field(default=[], description="Kết quả Layer 4 - đối chiếu liều dùng")
    final_summary: str = Field("", description="Tóm tắt tổng quan tình trạng và lời khuyên cuối cùng cho User")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class OCRPipelineMetrics(BaseModel):
    """Typed latency metrics trả về từ ONNX OCR Pipeline.

    [P2/F3-harden] Thay thế `Dict[str, Any]` trong ScanEvaluationResponse —
    shape xác định từ ai/pipelines/onnx_ocr_engine.py:187."""
    preprocessor_ms: int = Field(0, ge=0, description="Thời gian tiền xử lý ảnh (ms)")
    ocr_inference_ms: int = Field(0, ge=0, description="Thời gian inference OCR model (ms)")
    total_latency_ms: int = Field(0, ge=0, description="Tổng thời gian pipeline (ms)")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ScanEvaluationResponse(BaseModel):
    """Integrated Scan + 4-Layer Clinical Evaluation Response Model."""
    engine: str = "PP-OCRv6-Pure-ONNX"
    source_stream: str = "prescription"
    extracted_drugs: List[ExtractedDrugItem] = []
    clinical_report: Optional[EvaluationResponse] = Field(
        default=None,
        description="Báo cáo 4-Layer Clinical Rule Engine",
    )
    metrics: OCRPipelineMetrics = Field(
        default_factory=OCRPipelineMetrics,
        description="Latency metrics chi tiết của pipeline ONNX",
    )
    request_id: str = Field("", description="UUID để trace pipeline scan trong server log")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


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
    # [F3.7] Cach bao dam ham luong khac DB (light warn — hien thi UI, KHONG block submit)
    strength_mismatch_warning: Optional[str] = None

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
    """Full Pipeline Response: Raw OCR + Mapped Drugs + Clinical Assessment.

    [P2/F3-harden] `request_id` thêm vào để Frontend có thể gửi lại khi
    cần hỗ trợ — tương quan với server log (request_id ghi vào mọi log lỗi)."""
    scan_id: Optional[str] = Field(None, description="Unique Scan Record ID trong Data Platform phục vụ Lineage & HITL Review")
    request_id: str = Field("", description="UUID để trace pipeline scan trong server log")
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