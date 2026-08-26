# Endpoint OCR + Clinical Assessment Pipeline (Pure Local, No External VLM)
import time
from collections import Counter
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from app.core.config import OCR_PROCESSING_SLA_MS
from app.schemas import (  # Canonical response models — single source of truth [P0/F3.1]
    ClinicalAlertSummary,
    ClinicalAssessmentResponse,
    FullScanResponse,
    MappedDrugItem,
    OCRItem,
)
from app.services.clinical_service import ClinicalAssessmentRequest, clinical_service
from app.services.drug_database import drug_database
from app.services.normalization_service import NormalizationService
from app.services.ocr_engine import ocr_engine

router = APIRouter(prefix="/ocr", tags=["OCR + Clinical Assessment Pipeline"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


# [P0/F3.1] Bộ Response models (OCRItem, MappedDrugItem, ClinicalAlertSummary,
# FullScanResponse) đã hợp nhất về canonical `app.schemas.ocr_schema`
# (Task 1.2 — một schema, một nguồn sự thật). Xóa bản định nghĩa cục bộ trùng
# tên tại đây; endpoint giờ import trực tiếp từ app.schemas.


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _convert_ocr_items(raw_items: list) -> list[OCRItem]:
    """Convert OCRItem from ocr_schema to API OCRItem."""
    return [
        OCRItem(text=item.text, confidence=item.confidence, box=item.box)
        for item in raw_items
    ]


def _ocr_items_to_drug_items(raw_items: list, source_type: str) -> list:
    """Convert raw OCR text lines to DrugItem objects for normalization."""
    from app.schemas import DrugItem

    drug_items = []
    for item in raw_items:
        text = item.text.strip()
        if not text or len(text) < 2:
            continue
        # Heuristic: if text looks like a drug name (contains letters, not just numbers)
        if any(c.isalpha() for c in text):
            # Pipeline gating (ARCHITECTURE.md §3 / AGENTS.md B.1):
            #  - Pipeline 1 (packaging / vỏ hộp): dosage_instruction PHẢI là None —
            #    liều dùng do User nhập tay ở Smart Form; OCR không tự động gán.
            #  - Pipeline 2 (prescription / toa thuốc): OCRItem chưa mang dosage
            #    (bổ sung ở Stage 3 Normalization nếu text toa chứa hướng dẫn liệu).
            if source_type == "packaging":
                dosage_instruction = None
            else:
                dosage_instruction = getattr(item, "dosage_instruction", None)
            drug_items.append(
                DrugItem(
                    brand_name=text,
                    strength="",  # sẽ được fill bởi normalization
                    confidence_score=item.confidence,
                    dosage_instruction=dosage_instruction,
                )
            )
    return drug_items


def _map_drug_items(normalized: list) -> list[MappedDrugItem]:
    """Convert normalized DrugItem to MappedDrugItem for API response."""
    mapped = []
    for drug in normalized:
        mapped.append(
            MappedDrugItem(
                drug_id=getattr(drug, "drug_id", None),
                brand_name=drug.brand_name,
                active_ingredient=drug.active_ingredient,
                strength=drug.strength,
                dosage_instruction=drug.dosage_instruction,
                category=getattr(drug, "category", None),
                max_daily_dosage=getattr(drug, "max_daily_dosage", None),
                warnings=getattr(drug, "warnings", []),
                confidence_score=drug.confidence_score,
                is_verified=drug.is_verified,
                match_method=drug.match_method,  # [P3/F3.6] field chính thức trong schema
                strength_mismatch_warning=getattr(drug, "strength_mismatch_warning", None),  # [F3.7]
            )
        )
    return mapped


def _summarize_clinical(assessment: ClinicalAssessmentResponse) -> ClinicalAlertSummary:
    """Tạo summary từ ClinicalAssessmentResponse.

    [P1/F3.2] Đếm TRỰC TIẾP theo severity đã được clamp bởi schema.
    Loại bỏ công thức suy luận `low = total - high - medium` — nguồn gốc bug
    đếm lệch khi LLM từng trả severity ngoài 3 mức chuẩn (alert "CRITICAL"
    bị nhét nhầm vào bucket LOW)."""
    all_alerts = [
        *assessment.drug_drug_interactions,
        *assessment.drug_condition_interactions,
        *assessment.overdose_duplication_alerts,
    ]
    counts = Counter(alert.severity for alert in all_alerts)
    return ClinicalAlertSummary(
        total_alerts=len(all_alerts),
        high_count=counts["HIGH"],
        medium_count=counts["MEDIUM"],
        low_count=counts["LOW"],
        drug_drug_interactions=len(assessment.drug_drug_interactions),
        drug_condition_interactions=len(assessment.drug_condition_interactions),
        overdose_duplication=len(assessment.overdose_duplication_alerts),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/scan", response_model=FullScanResponse)
async def ocr_scan(
    file: UploadFile = File(...),
    source_type: str = Form("prescription", description="'prescription' (Toa thuốc/Receipt) hoặc 'packaging' (Vỏ hộp/Lọ)"),
    run_clinical: bool = Form(True, description="Chạy Clinical Assessment LLM (mặc định: true)"),
    user_age: Optional[int] = Form(None, description="Tuổi bệnh nhân (cho clinical assessment)"),
    user_conditions: Optional[str] = Form(None, description="Bệnh nền, phân cách bằng dấu phẩy"),
    user_allergies: Optional[str] = Form(None, description="Dị ứng hoạt chất, phân cách bằng dấu phẩy"),
) -> FullScanResponse:
    """
    Full Pipeline: OCR → Normalization → Clinical Assessment (LLM)

    1. OCR: Dual Pipeline (Prescription vs Packaging) - PP-OCRv6 ONNX CPU
    2. Normalization: rapidfuzz map OCR text -> Drug Database (Local + OpenFDA)
    3. Clinical Assessment: LLM (Local Qwen2.5/Phi-3 hoặc OpenAI) phân tích:
       - Drug-Drug Interactions
       - Drug-Condition Interactions  
       - Overdose/Duplication
       - Clinical Recommendations & Monitoring

    Trả về: Raw OCR + Mapped Drugs + Clinical Alerts (JSON Structured)
    """
    # Validate input
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tệp tải lên phải là định dạng hình ảnh (JPEG, PNG, WEBP).",
        )

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng '{suffix or 'trống'}' không được hỗ trợ. Chấp nhận: {sorted(ALLOWED_EXTENSIONS)}",
        )

    if source_type not in {"prescription", "packaging"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_type chỉ nhận 'prescription' hoặc 'packaging'.",
        )

    try:
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File ảnh rỗng, không có dữ liệu để xử lý.",
            )

        # ═══════════════════════════════════════════════════════════════
        # STEP 1: OCR (Dual Pipeline)
        # ═══════════════════════════════════════════════════════════════
        ocr_started = time.perf_counter()
        if source_type == "packaging":
            ocr_result = await run_in_threadpool(ocr_engine.extract_packaging_label, image_bytes)
        else:
            ocr_result = await run_in_threadpool(ocr_engine.extract_prescription_receipt, image_bytes)
        ocr_latency_ms = int(round((time.perf_counter() - ocr_started) * 1000))

        raw_ocr_items = _convert_ocr_items(ocr_result.items)

        # ═══════════════════════════════════════════════════════════════
        # STEP 2: Normalization (OCR Text -> Drug Database)
        # ═══════════════════════════════════════════════════════════════
        norm_started = time.perf_counter()
        drug_items = _ocr_items_to_drug_items(ocr_result.items, source_type)
        normalization_service = NormalizationService()
        # [P2/F3.4] Chuẩn hóa 4 tầng: 3 tầng local + OpenFDA khi local miss toàn bộ
        normalized_drugs = await normalization_service.normalize_ocr_items_full(drug_items)
        normalization_latency_ms = int(round((time.perf_counter() - norm_started) * 1000))

        mapped_drugs = _map_drug_items(normalized_drugs)

        # ═══════════════════════════════════════════════════════════════
        # STEP 3: Clinical Assessment (LLM)
        # ═══════════════════════════════════════════════════════════════
        clinical_assessment = None
        clinical_summary = None
        clinical_latency_ms = 0

        if run_clinical and normalized_drugs:
            clinical_started = time.perf_counter()
            # Build UserProfile from form data
            user_profile = None
            if any([user_age, user_conditions, user_allergies]):
                from app.schemas import UserProfile
                user_profile = UserProfile(
                    age=user_age or 0,
                    conditions=[c.strip() for c in user_conditions.split(",")] if user_conditions else [],
                    allergies=[a.strip() for a in user_allergies.split(",")] if user_allergies else [],
                )

            assessment_request = ClinicalAssessmentRequest(
                drugs=normalized_drugs,
                user_profile=user_profile,
            )
            clinical_assessment = await clinical_service.assess(assessment_request)
            clinical_summary = _summarize_clinical(clinical_assessment)
            clinical_latency_ms = int(round((time.perf_counter() - clinical_started) * 1000))

        # ═══════════════════════════════════════════════════════════════
        # RESPONSE
        # ═══════════════════════════════════════════════════════════════
        total_latency_ms = ocr_latency_ms + normalization_latency_ms + clinical_latency_ms

        return FullScanResponse(
            engine=ocr_result.engine,
            source_type=ocr_result.source_type,
            raw_ocr_items=raw_ocr_items,
            ocr_latency_ms=ocr_latency_ms,
                        sla_exceeded=ocr_latency_ms > OCR_PROCESSING_SLA_MS,  # OCR SLA (from app.core.config)
            image_width=ocr_result.image_width,
            image_height=ocr_result.image_height,
            mapped_drugs=mapped_drugs,
            clinical_assessment=clinical_assessment,
            clinical_summary=clinical_summary,
            total_latency_ms=total_latency_ms,
            normalization_latency_ms=normalization_latency_ms,
            clinical_latency_ms=clinical_latency_ms,
        )

    except HTTPException:
        raise
    # [P3/F3.5] Lỗi kết nối ngoài (OpenFDA/Ollama/OpenAI) đã được bắt CỤ THỂ bên
    # trong các services với graceful degradation; catch biên cuối này chỉ là
    # phòng thủ cho lỗi bất ngờ — luôn chuyển thành HTTPException 500 có mã lỗi
    # rõ ràng, không bao giờ để raise trần làm sập endpoint.
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi pipeline OCR+Clinical: {exc}",
        ) from exc