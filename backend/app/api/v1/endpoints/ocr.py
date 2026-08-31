# Endpoint OCR + Clinical Assessment Pipeline (Pure Local, No External VLM)
import io
import logging
import os
import re
import sys
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Optional, Type

# Ensure repository root is in sys.path for importing ai subsystem
repo_root = str(Path(__file__).resolve().parents[4])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from PIL import Image as PILImage
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.core.config import (
    OCR_MAX_FILE_SIZE_MB,
    OCR_MAX_IMAGE_DIMENSION,
    OCR_MAX_IMAGE_PIXELS,
    OCR_PROCESSING_SLA_MS,
    settings,
)
from app.db.session import get_db
from app.schemas import (  # Canonical response models — single source of truth [P0/F3.1]
    ClinicalAlertSummary,
    ClinicalAssessmentResponse,
    EvaluationResponse,
    ExtractedDrugItem,
    FullScanResponse,
    MappedDrugItem,
    OCRItem,
    OCRPipelineMetrics,
    ScanEvaluationResponse,
    UserProfile,
)
from app.schemas.user_schema import UserResponse
from app.services.clinical_service import ClinicalAssessmentRequest, clinical_service
from app.services.drug_database import drug_database
from app.services.normalization_service import NormalizationService
from app.services.ocr_engine import ocr_engine
from app.services.profile_service import profile_service

logger = logging.getLogger(__name__)

# Threshold convert từ MB thành bytes một lần duy nhất khi module load
_MAX_FILE_SIZE_BYTES: int = OCR_MAX_FILE_SIZE_MB * 1024 * 1024

# Thiết lập giới hạn pixel toàn cục cho PIL để chặn Decompression Bomb attacks
PILImage.MAX_IMAGE_PIXELS = OCR_MAX_IMAGE_PIXELS


router = APIRouter(prefix="/ocr", tags=["OCR + Clinical Assessment Pipeline"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


# ─────────────────────────────────────────────────────────────────────────────
# Error Handling & Transient Classification (Allowlist only)
# ─────────────────────────────────────────────────────────────────────────────

TRANSIENT_EXCEPTIONS: tuple[Type[Exception], ...] = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    ConnectionError,
    TimeoutError,
)


def is_transient_error(exc: Exception) -> bool:
    """Allowlist strictly transient errors (timeout, connection failure, rate-limit, 503).
    Mặc định LUÔN là False cho mọi lỗi khác (kể cả Programming Errors)."""
    if isinstance(exc, TRANSIENT_EXCEPTIONS):
        return True
    exc_type_name = type(exc).__name__
    if exc_type_name in {
        "APITimeoutError",
        "APIConnectionError",
        "RateLimitError",
        "ServiceUnavailableError",
        "InternalServerError",
    }:
        return True
    return False


def _make_error_detail(
    error_code: str,
    message: str,
    stage: str,
    request_id: str,
    service: str = "ocr_clinical_pipeline",
    retryable: bool = False,
) -> dict[str, Any]:
    """Unified Error Contract — bảo đảm 100% error responses có đúng 6 trường."""
    return {
        "error_code": error_code,
        "message": message,
        "service": service,
        "stage": stage,
        "request_id": request_id,
        "retryable": retryable,
    }


async def _read_bounded_upload_file(file: UploadFile, max_bytes: int) -> bytes:
    """Đọc file upload theo chunk (64KB) có chặn trên để chống cạn kiệt RAM/OOM."""
    chunk_size = 64 * 1024
    accumulated = bytearray()
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        accumulated.extend(chunk)
        if len(accumulated) > max_bytes:
            raise ValueError("FILE_TOO_LARGE")
    return bytes(accumulated)


def _validate_image_integrity(image_bytes: bytes, request_id: str, service: str) -> None:
    """Kiểm tra tính hợp lệ của ảnh: magic bytes, dimensions, decompression bomb, raster decode."""
    try:
        with PILImage.open(io.BytesIO(image_bytes)) as img:
            w, h = img.size
            if w > OCR_MAX_IMAGE_DIMENSION or h > OCR_MAX_IMAGE_DIMENSION:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=_make_error_detail(
                        error_code="IMAGE_DIMENSIONS_EXCEEDED",
                        message=f"Kích thước ảnh ({w}x{h}) vượt giới hạn cho phép tối đa ({OCR_MAX_IMAGE_DIMENSION}px).",
                        stage="image_decode",
                        request_id=request_id,
                        service=service,
                        retryable=False,
                    ),
                )
            # Decode toàn bộ raster để phát hiện file truncated hoặc corrupt
            img.load()
    except PILImage.DecompressionBombError as dbe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error_detail(
                error_code="DECOMPRESSION_BOMB_DETECTED",
                message="Phát hiện ảnh có số lượng pixel bất thường (nguy cơ decompression bomb).",
                stage="image_decode",
                request_id=request_id,
                service=service,
                retryable=False,
            ),
        ) from dbe
    except HTTPException:
        raise
    except Exception as img_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error_detail(
                error_code="CORRUPT_IMAGE",
                message="File ảnh bị hỏng hoặc không thể giải mã. Vui lòng kiểm tra và tải lại.",
                stage="image_decode",
                request_id=request_id,
                service=service,
                retryable=False,
            ),
        ) from img_err


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _convert_ocr_items(raw_items: list) -> list[OCRItem]:
    """Convert OCRItem from ocr_schema to API OCRItem."""
    return [
        OCRItem(text=item.text, confidence=item.confidence, box=item.box)
        for item in raw_items
    ]


PRESCRIPTION_DRUG_PATTERNS = [
    re.compile(r"^\s*\d+[\.\)]\s*(?:T[êe]n\s+thu[oôó]c|Thu[oôó]c)?\s*(?:\([^\)]*\))?\s*[:\.]*\s*(.+)", re.IGNORECASE),
    re.compile(r"(?:T[êe]n\s+thu[oôó]c|Thu[oôó]c)\s*(?:\([^\)]*\))?\s*[:\.]+\s*(.+)", re.IGNORECASE),
]

PRESCRIPTION_IGNORE_PATTERNS = [
    re.compile(r"^(?:TOA\s*THU[OÔÓ]C|PRESCRIPTION)", re.IGNORECASE),
    re.compile(r"^(?:H[oọ]\s*v[aà]\s*t[eê]n|Full\s*name)", re.IGNORECASE),
    re.compile(r"^(?:Tu[oôò]i|Age)", re.IGNORECASE),
    re.compile(r"^(?:[ĐD][iị]a\s*ch[iỉ]|Address)", re.IGNORECASE),
    re.compile(r"^(?:Ch[aẩâ]n\s*[đd]o[aá]n|Diagnosis)", re.IGNORECASE),
    re.compile(r"^(?:Ng[aà]y|Date|Th[aá]ng|Month|N[aăâ]m|Year)", re.IGNORECASE),
    re.compile(r"^(?:B[aá]c\s*s[iĩ]|Doctor|K[yý]\s*t[eê]n|Sign)", re.IGNORECASE),
    re.compile(r"^(?:Take\s*medicine|U[oôố]ng\s*thu[oôó]c\s*sau)", re.IGNORECASE),
]

DOSAGE_INSTRUCTION_PATTERNS = [
    re.compile(r"(?:S[oó]\s*l[uưr][oợơ]ng|Dosage)", re.IGNORECASE),
    re.compile(r"(?:S[aá]ng|Morning|Tr[uưưa]+|Afternoon|T[oôó]i|Night)", re.IGNORECASE),
    re.compile(r"(?:tr[uưr][oóớ]c\s*[aāă]n|sau\s*[aāă]n)", re.IGNORECASE),
]

PACKAGING_IGNORE_PATTERNS = [
    re.compile(r"^(?:FOR\s+ACNE|TREATMENT|TOPICAL\s+CREAM|COMPLEMENTO|ALIMENTICID)", re.IGNORECASE),
    re.compile(r"^(?:Good\s+for|TOWARDS|PRE-DIABETES|DIABETES|AND\s+PRE-DIABETES)", re.IGNORECASE),
    re.compile(r"^(?:Jamjoom\s+Pharma|BIOIBERICA|BIotBERICA|Pharma|Laboratories|Laboratory)", re.IGNORECASE),
    re.compile(r"^(?:Derma|Serum|Lotion|Shampoo|Cream|Gel)$", re.IGNORECASE),
    re.compile(r"^(?:60\s*CAP|30\s*GM|\(30|CN:\d+|000|\d{2,4}$)", re.IGNORECASE),
    re.compile(r"^(?:00O|aLEA|deteido|nes\s+ylgaentom|whiaotzatn\s+spoL|cisarandos,)$", re.IGNORECASE),
    re.compile(r"[\u4e00-\u9fff]", re.UNICODE),
]

STRENGTH_REGEX = re.compile(
    r"(\d+(?:[\.,]\d+)?\s*(?:mg|g|ml|mcg|iu|%|\/)(?:\s*(?:w\/w|w\/v))?)",
    re.IGNORECASE,
)


def _ocr_items_to_drug_items(raw_items: list[OCRItem], source_type: str) -> list:
    """Convert raw OCR text lines to DrugItem objects for normalization.
    - Pipeline 1 (packaging): Trích xuất tên sạch, lọc slogan/bao bì, dosage_instruction = None.
    - Pipeline 2 (prescription): Bóc tách tên thuốc, hàm lượng và ghép liều dùng liên tiếp."""
    from app.schemas import DrugItem

    if source_type == "packaging":
        # Sắp xếp các box theo diện tích giảm dần để ưu tiên nhãn/tên thương mại lớn nhất
        def _get_box_area(item: OCRItem) -> float:
            box = getattr(item, "box", None) or []
            if len(box) == 4:
                return float(max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1]))
            return 0.0

        sorted_items = sorted(raw_items, key=_get_box_area, reverse=True)
        drug_items = []
        for item in sorted_items:
            text = str(getattr(item, "text", "")).strip()
            conf = getattr(item, "confidence", 0.9)
            if not text or len(text) < 3:
                continue
            if conf < 0.65:
                continue
            if not any(c.isalpha() for c in text):
                continue
            if any(p.search(text) for p in PACKAGING_IGNORE_PATTERNS):
                continue

            cleaned = re.sub(r"[\.\…\s]+$", "", text)
            cleaned = re.sub(r"^[\.\…\s]+", "", cleaned)
            cleaned = re.sub(r"\.{2,}", " ", cleaned)

            # Tách nồng độ
            st_match = STRENGTH_REGEX.search(cleaned)
            strength = st_match.group(1).strip() if st_match else ""

            drug_items.append(
                DrugItem(
                    brand_name=cleaned,
                    strength=strength,
                    confidence_score=conf,
                    dosage_instruction=None,  # Pipeline 1: Bắt buộc do User nhập tay ở Smart Form
                )
            )
            # Cap tối đa 3 candidates sáng giá nhất trên bao bì
            if len(drug_items) >= 3:
                break
        return drug_items

    # Pipeline 2: Toa thuốc (Prescription)
    # Kiểm tra xem có bất kỳ dòng nào khớp mẫu có cấu trúc "1. Tên thuốc / Thuốc:" không
    has_structured_pattern = any(
        any(p.search(str(getattr(it, "text", ""))) for p in PRESCRIPTION_DRUG_PATTERNS)
        for it in raw_items
    )

    if not has_structured_pattern:
        # Fallback snippet / hóa đơn tự do: mỗi dòng chữ là 1 DrugItem
        drug_items = []
        for item in raw_items:
            text = str(getattr(item, "text", "")).strip()
            if not text or len(text) < 2:
                continue
            if any(c.isalpha() for c in text):
                cleaned = re.sub(r"[\.\…\s]+$", "", text)
                st_match = STRENGTH_REGEX.search(cleaned)
                strength = st_match.group(1).strip() if st_match else ""
                drug_items.append(
                    DrugItem(
                        brand_name=cleaned,
                        strength=strength,
                        confidence_score=getattr(item, "confidence", 0.9),
                        dosage_instruction=getattr(item, "dosage_instruction", None),
                    )
                )
        return drug_items

    # Bóc tách có cấu trúc cho đơn thuốc chính quy
    drug_items = []
    current_drug = None

    for item in raw_items:
        text = str(getattr(item, "text", "")).strip()
        if not text or len(text) < 2:
            continue
        if not any(c.isalpha() for c in text):
            continue
        if any(p.search(text) for p in PRESCRIPTION_IGNORE_PATTERNS):
            continue

        drug_match = None
        for p in PRESCRIPTION_DRUG_PATTERNS:
            m = p.search(text)
            if m:
                drug_match = m.group(1).strip()
                break

        if drug_match:
            cleaned = re.sub(r"[\.\…\s]+$", "", drug_match)
            cleaned = re.split(r"(?:S[oó]\s*l[uưr][oợơ]ng|Dosage)", cleaned, flags=re.IGNORECASE)[0].strip()
            cleaned = re.sub(r"[\.\…\s]+$", "", cleaned)
            cleaned = re.sub(r"^[\.\…\s]+", "", cleaned)
            cleaned = re.sub(r"\.{2,}", " ", cleaned)

            st_match = STRENGTH_REGEX.search(cleaned)
            strength = st_match.group(1).strip() if st_match else ""

            current_drug = DrugItem(
                brand_name=cleaned,
                strength=strength,
                confidence_score=getattr(item, "confidence", 0.9),
                dosage_instruction=None,
            )
            drug_items.append(current_drug)
        elif current_drug is not None and any(p.search(text) for p in DOSAGE_INSTRUCTION_PATTERNS):
            if current_drug.dosage_instruction:
                current_drug.dosage_instruction += " | " + text
            else:
                current_drug.dosage_instruction = text

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
    """Tạo summary từ ClinicalAssessmentResponse."""
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
# Main Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/scan", response_model=FullScanResponse)
async def ocr_scan(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    source_type: str = Form("prescription", description="'prescription' (Toa thuốc/Receipt) hoặc 'packaging' (Vỏ hộp/Lọ)"),
    run_clinical: bool = Form(True, description="Chạy Clinical Assessment LLM (mặc định: true)"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FullScanResponse:
    """
    Full Pipeline: OCR → Normalization → Clinical Assessment (LLM)
    """
    service_name = "ocr_clinical_pipeline"
    request_id = request.headers.get("X-Request-ID") or getattr(getattr(request, "state", None), "request_id", None) or str(uuid.uuid4())
    response.headers["X-Request-ID"] = request_id

    # Validate input — thứ tự: content_type → extension → source_type → size → bytes
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error_detail(
                error_code="INVALID_MIME_TYPE",
                message="Tệp tải lên phải là định dạng hình ảnh (JPEG, PNG, WEBP).",
                stage="validation",
                request_id=request_id,
                service=service_name,
                retryable=False,
            ),
        )

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error_detail(
                error_code="INVALID_EXTENSION",
                message=f"Định dạng '{suffix or 'trống'}' không được hỗ trợ. Chấp nhận: {sorted(ALLOWED_EXTENSIONS)}",
                stage="validation",
                request_id=request_id,
                service=service_name,
                retryable=False,
            ),
        )

    if source_type not in {"prescription", "packaging"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error_detail(
                error_code="INVALID_SOURCE_TYPE",
                message="source_type chỉ nhận 'prescription' hoặc 'packaging'.",
                stage="validation",
                request_id=request_id,
                service=service_name,
                retryable=False,
            ),
        )

    # Kiểm tra size trước khi đọc nếu client cung cấp header Content-Length
    if file.size is not None and file.size > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=_make_error_detail(
                error_code="FILE_TOO_LARGE",
                message=f"File vượt giới hạn {OCR_MAX_FILE_SIZE_MB}MB. Vui lòng nén hoặc cắt xén ảnh trước khi tải lên.",
                stage="upload",
                request_id=request_id,
                service=service_name,
                retryable=False,
            ),
        )

    try:
        try:
            image_bytes = await _read_bounded_upload_file(file, _MAX_FILE_SIZE_BYTES)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=_make_error_detail(
                    error_code="FILE_TOO_LARGE",
                    message=f"File vượt giới hạn {OCR_MAX_FILE_SIZE_MB}MB.",
                    stage="upload",
                    request_id=request_id,
                    service=service_name,
                    retryable=False,
                ),
            )

        if not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_make_error_detail(
                    error_code="EMPTY_FILE",
                    message="File ảnh rỗng, không có dữ liệu để xử lý.",
                    stage="upload",
                    request_id=request_id,
                    service=service_name,
                    retryable=False,
                ),
            )

        # Decode validation & Decompression Bomb protection
        _validate_image_integrity(image_bytes, request_id, service_name)

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
        # STEP 3: Clinical Assessment (LLM) — Đọc UserProfile từ Database
        # ═══════════════════════════════════════════════════════════════
        clinical_assessment = None
        clinical_summary = None
        clinical_latency_ms = 0

        if run_clinical and normalized_drugs:
            db_profile = await profile_service.get_profile(db, current_user.id)
            if not db_profile or not current_user.is_profile_completed:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=_make_error_detail(
                        error_code="INCOMPLETE_ONBOARDING",
                        message="Tài khoản chưa hoàn tất hồ sơ y tế cá nhân (Onboarding). Vui lòng hoàn thành hồ sơ tại /onboarding trước khi đánh giá lâm sàng.",
                        stage="clinical_assessment",
                        request_id=request_id,
                        service=service_name,
                        retryable=False,
                    ),
                )

            user_profile = UserProfile(
                age=db_profile.age,
                conditions=db_profile.conditions or [],
                allergies=db_profile.allergies or [],
            )

            clinical_started = time.perf_counter()
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
        logger.info(
            "[OCR_SCAN_OK] request_id=%s source=%s drugs=%d clinical=%s total_ms=%d",
            request_id, source_type, len(mapped_drugs),
            clinical_assessment is not None, total_latency_ms,
        )

        return FullScanResponse(
            request_id=request_id,
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
    except Exception as exc:  # noqa: BLE001
        retryable = is_transient_error(exc)
        logger.exception(
            "[OCR_PIPELINE_ERROR] request_id=%s stage=ocr_scan retryable=%s error_type=%s",
            request_id, retryable, type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error_detail(
                error_code="INTERNAL_SERVER_ERROR",
                message="Đã xảy ra sự cố kết nối/timeout tạm thời. Vui lòng thử lại sau giây lát."
                if retryable
                else "Lỗi hệ thống nội bộ. Vui lòng liên hệ hỗ trợ kỹ thuật kèm request_id.",
                stage="ocr_scan",
                request_id=request_id,
                service=service_name,
                retryable=retryable,
            ),
        ) from exc


@router.post("/process", response_model=ScanEvaluationResponse)
async def process_scan_pipeline(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    source_stream: str = Form("prescription", description="'prescription' hoặc 'packaging'"),
) -> ScanEvaluationResponse:
    """
    End-to-End Direct Pipeline nối trực tiếp phân hệ /ai:
    1. Tiền xử lý ảnh (Deskew, CLAHE, Denoise, Downscale)
    2. ONNX OCR Inference
    3. Fuzzy Medical Normalization & Brand-to-Generic Mapping
    4. Clinical NER (Extraction of Strength, Dosage, Time slots)
    5. 4-Layer Clinical Rule Engine Evaluation
    """
    service_name = "onnx_ocr_pipeline"
    request_id = request.headers.get("X-Request-ID") or getattr(getattr(request, "state", None), "request_id", None) or str(uuid.uuid4())
    response.headers["X-Request-ID"] = request_id

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error_detail(
                error_code="INVALID_MIME_TYPE",
                message="Tệp tải lên phải là hình ảnh hợp lệ (JPEG, PNG, WEBP).",
                stage="validation",
                request_id=request_id,
                service=service_name,
                retryable=False,
            ),
        )

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error_detail(
                error_code="INVALID_EXTENSION",
                message=f"Định dạng '{suffix}' không được hỗ trợ. Chấp nhận: {sorted(ALLOWED_EXTENSIONS)}",
                stage="validation",
                request_id=request_id,
                service=service_name,
                retryable=False,
            ),
        )

    if source_stream not in {"prescription", "packaging"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_error_detail(
                error_code="INVALID_SOURCE_STREAM",
                message="source_stream chỉ nhận 'prescription' hoặc 'packaging'.",
                stage="validation",
                request_id=request_id,
                service=service_name,
                retryable=False,
            ),
        )

    if file.size is not None and file.size > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=_make_error_detail(
                error_code="FILE_TOO_LARGE",
                message=f"File vượt giới hạn {OCR_MAX_FILE_SIZE_MB}MB.",
                stage="upload",
                request_id=request_id,
                service=service_name,
                retryable=False,
            ),
        )

    try:
        try:
            image_bytes = await _read_bounded_upload_file(file, _MAX_FILE_SIZE_BYTES)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=_make_error_detail(
                    error_code="FILE_TOO_LARGE",
                    message=f"File vượt giới hạn {OCR_MAX_FILE_SIZE_MB}MB.",
                    stage="upload",
                    request_id=request_id,
                    service=service_name,
                    retryable=False,
                ),
            )

        if not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_make_error_detail(
                    error_code="EMPTY_FILE",
                    message="File ảnh rỗng, không có dữ liệu để xử lý.",
                    stage="upload",
                    request_id=request_id,
                    service=service_name,
                    retryable=False,
                ),
            )

        # Decode validation & Decompression Bomb protection
        _validate_image_integrity(image_bytes, request_id, service_name)

        from ai.pipelines.onnx_ocr_engine import default_onnx_ocr_engine
        from ai.clinical_evaluator.rule_engine import default_clinical_rule_engine

        ai_out = await run_in_threadpool(
            default_onnx_ocr_engine.process_document,
            image_bytes,
            source_stream,
        )

        extracted_raw_drugs = ai_out.get("extracted_drugs", [])

        extracted_drugs = [
            ExtractedDrugItem(
                id=d.get("id") or f"ext_{idx}",
                drug_name=d.get("drug_name") or "",
                active_ingredient=d.get("active_ingredient"),
                strength=d.get("strength"),
                dosage_form=d.get("dosage_form"),
                dosage_instruction=d.get("dosage_instruction"),
                time_slots=d.get("time_slots", []),
                slot_times=d.get("slot_times", {}),
                duration_days=d.get("duration_days"),
                start_date=d.get("start_date"),
                is_time_extracted=d.get("is_time_extracted", False),
                source_stream=source_stream,
            )
            for idx, d in enumerate(extracted_raw_drugs)
        ]
        user_prof = {}

        raw_eval_report = await run_in_threadpool(
            default_clinical_rule_engine.evaluate,
            [d.model_dump() for d in extracted_drugs],
            user_prof,
        )

        eval_report: Optional[EvaluationResponse] = None
        if raw_eval_report and isinstance(raw_eval_report, dict):
            eval_report = EvaluationResponse(**raw_eval_report)

        raw_metrics = ai_out.get("metrics", {})
        return ScanEvaluationResponse(
            request_id=request_id,
            engine="PP-OCRv6-Pure-ONNX",
            source_stream=source_stream,
            extracted_drugs=extracted_drugs,
            clinical_report=eval_report,
            metrics=OCRPipelineMetrics(
                preprocessor_ms=raw_metrics.get("preprocessor_ms", 0),
                ocr_inference_ms=raw_metrics.get("ocr_inference_ms", 0),
                total_latency_ms=raw_metrics.get("total_latency_ms", 0),
            ),
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        retryable = is_transient_error(exc)
        logger.exception(
            "[PROCESS_PIPELINE_ERROR] request_id=%s retryable=%s error_type=%s",
            request_id, retryable, type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_make_error_detail(
                error_code="INTERNAL_SERVER_ERROR",
                message="Đã xảy ra sự cố kết nối/timeout tạm thời. Vui lòng thử lại sau giây lát."
                if retryable
                else "Lỗi hệ thống nội bộ. Vui lòng liên hệ hỗ trợ kỹ thuật kèm request_id.",
                stage="process_scan",
                request_id=request_id,
                service=service_name,
                retryable=retryable,
            ),
        ) from exc