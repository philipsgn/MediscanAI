# Entrypoint chính cho FastAPI Backend Service Mediscan AI
# Pure Local OCR + Clinical Assessment Pipeline (No External VLM)
import logging
from contextlib import asynccontextmanager
from typing import Any, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from slowapi.errors import RateLimitExceeded
from app.api.v1.endpoints.auth import get_optional_current_user, router as auth_router
from app.api.v1.endpoints.drugs import router as drugs_router
from app.api.v1.endpoints.history import router as history_router
from app.api.v1.endpoints.medications import router as medications_router
from app.api.v1.endpoints.ocr import router as ocr_router
from app.api.v1.endpoints.profile import router as profile_router
from app.api.v1.endpoints.reminders import router as reminders_router
from app.api.v1.endpoints.metrics import router as metrics_router
from app.core.config import settings
from app.core.limiter import custom_rate_limit_exceeded_handler, limiter
from app.schemas import (
    DrugEvaluationRequest,
    EvaluationResponse,
    InteractionAlert,
)
from app.schemas.user_schema import UserResponse
from app.db.init_db import init_db
from app.db.session import get_db
from app.services.clinical_service import ClinicalAssessmentRequest, clinical_service
from app.services.evaluation_service import evaluation_service
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Khởi tạo Database schema nếu cần
    await init_db()
    # Nạp learned drugs từ database vào L1 RAM (Stage 18)
    try:
        from app.services.drug_database import drug_database
        await drug_database.load_learned_from_db()
    except Exception as e:
        logger.warning("Could not load learned drugs from DB on startup: %s", e)
    # Khởi tạo chậm: OCR engine được load lazy tại request scan đầu tiên.
    yield
    from app.services.ocr_engine import ocr_engine

    ocr_engine.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend REST API cho Mediscan AI - Pure Local OCR + Clinical LLM Assessment",
    lifespan=lifespan,
)

# Gắn Rate Limiter (slowapi) cho toàn bộ ứng dụng
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)

# Cấu hình CORS mở rộng hỗ trợ Web Desktop & Mobile
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_tracing_middleware(request, call_next):
    """Request tracing middleware: guarantees every request carries a single consistent request_id."""
    import uuid
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Route Authentication System (Stage 8)
app.include_router(auth_router, prefix=settings.API_V1_STR)

# Route Personalized Clinical Health Profile (Stage 9)
app.include_router(profile_router, prefix=settings.API_V1_STR)

# Route Medication History & Smart Reminders & Cabinet (Stage 10)
app.include_router(history_router, prefix=settings.API_V1_STR)
app.include_router(reminders_router, prefix=settings.API_V1_STR)
app.include_router(medications_router, prefix=settings.API_V1_STR)

# Route OCR + Clinical Assessment Pipeline
app.include_router(ocr_router, prefix=settings.API_V1_STR)

# Route Drug Lookup (autocomplete) [S4-Closeout/F4.3]
app.include_router(drugs_router, prefix=settings.API_V1_STR)

# Route AI & System Metrics (Stage 18)
app.include_router(metrics_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health Check"])
async def root() -> dict[str, str]:
    return {
        "status": "online",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
    }


@app.get("/health/live", tags=["Health Check"])
async def liveness() -> dict[str, str]:
    """Liveness probe: verifies server process is responsive."""
    return {"status": "ok", "probe": "liveness", "version": settings.VERSION}


@app.get("/health/ready", tags=["Health Check"])
async def readiness() -> dict[str, Any]:
    """Readiness probe: verifies database connectivity and core config state."""
    from sqlalchemy import text
    from app.db.session import AsyncSessionLocal

    db_status = "ok"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[HEALTH_READY] Database check failed: %s", exc)
        db_status = f"error: {type(exc).__name__}"

    is_ready = db_status == "ok"
    return {
        "status": "ready" if is_ready else "degraded",
        "probe": "readiness",
        "database": db_status,
        "version": settings.VERSION,
    }


@app.post("/health/warmup", tags=["Health Check"])
async def warmup() -> dict[str, Any]:
    """Dedicated Model Warmup: preloads OCR models without blocking health probes."""
    import time
    from app.services.ocr_engine import ocr_engine

    started = time.perf_counter()
    try:
        ocr_engine.warmup()
        elapsed_ms = int(round((time.perf_counter() - started) * 1000))
        return {
            "status": "ok",
            "warmup": "completed",
            "elapsed_ms": elapsed_ms,
        }
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int(round((time.perf_counter() - started) * 1000))
        logger.error("[WARMUP_FAILED] %s", exc)
        return {
            "status": "failed",
            "warmup": "error",
            "error": str(exc),
            "elapsed_ms": elapsed_ms,
        }

# ══════════════════════════════════════════════════════════════════════════════
# [Audit-S3 / P1 / F3.3] RANH GIỚI STAGE 5 — THAY ĐỔI ĐƯỢC ARCHITECT PHÊ DUYỆT
# ──────────────────────────────────────────────────────────────────────────────
# Endpoint này TRƯỚC ĐÂY delegate toàn bộ cho clinical_service (LLM), vô hiệu hóa
# rule-engine Stage 5 và để LLM quyết định severity (rủi ro hallucination y tế).
# Quy tắc mới theo Audit Stage 3 report (Findings F3.2/F3.3):
#   1) evaluation_service (rule-engine Stage 5) là NGUỒN QUYẾT ĐỊNH
#      severity/alert CUỐI CÙNG (source of truth).
#   2) clinical_service (LLM) CHỈ bổ sung diễn giải ngôn ngữ tự nhiên
#      (description/recommendation) cho alert khớp entity — KHÔNG đổi severity.
#   3) Alert chỉ LLM tìm ra mà rule-engine bỏ sót: giữ nguyên hành vi cũ
#      (bổ sung vào kết quả); severity qua fail-safe clamp của schema [F3.2].
# Ghi chú cho audit Stage 5: KHÔNG phải drift — đã được Architect phê duyệt
# qua Audit Stage 3 report + remediation plan P1.
# ══════════════════════════════════════════════════════════════════════════════
def _llm_entities(alert_obj: Any) -> List[str]:
    """Trích entity (thuốc/bệnh nền/hoạt chất) từ một LLM-alert để khớp rule-alert."""
    entities: List[str] = []
    for fname in ("interacting_drugs", "drug_name", "condition", "ingredient"):
        val = getattr(alert_obj, fname, None)
        if isinstance(val, list):
            entities.extend(str(x) for x in val if x)
        elif val:
            entities.append(str(val))
    title = getattr(alert_obj, "title", None)
    if title:
        entities.append(str(title))
    return [e.strip().lower() for e in entities if e and e.strip()]


def _match_llm_alert(rule_alert: InteractionAlert, llm_pool: List[Any]) -> Optional[Any]:
    """Khớp rule-alert ↔ LLM-alert: entity (≥4 ký tự) nằm trong title/description."""
    text = f"{rule_alert.title} {rule_alert.description}".lower()
    for llm_alert in llm_pool:
        for ent in _llm_entities(llm_alert):
            if len(ent) >= 4 and ent in text:
                return llm_alert
    return None


@app.post(
    f"{settings.API_V1_STR}/evaluate",
    response_model=EvaluationResponse,
    tags=["Clinical Assessment Engine"],
)
async def evaluate_interactions(
    payload: DrugEvaluationRequest,
    current_user: Optional[UserResponse] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    """
    Đánh giá tương tác thuốc (giữ nguyên contract legacy cho frontend).
    BƯỚC 1 — Rule-engine Stage 5 quyết định tập alert + severity cuối cùng.
    BƯỚC 2 — LLM chỉ enrich description/recommendation bằng ngôn ngữ tự nhiên.
    Layer 1: Overdose/Duplicate · Layer 2: Drug-Drug · Layer 3: Drug-Condition.
    BƯỚC 3 — Tự động lưu Lịch sử (Internal Write) cho authenticated user (Zero Image).
    """
    # ── BƯỚC 1: Rule engine = source of truth cho severity [F3.3] ────────────
    eval_result = evaluation_service.evaluate_medications(payload.drugs, payload.user_profile)
    alerts: List[InteractionAlert] = list(eval_result.alerts)

    # ── BƯỚC 2: LLM enrichment (không quyết định severity) ───────────────────
    llm_pool: List[Any] = []
    clinical_recommendations: List[str] = []
    try:
        assessment_request = ClinicalAssessmentRequest(
            drugs=payload.drugs,
            user_profile=payload.user_profile,
        )
        clinical_response = await clinical_service.assess(assessment_request)
        llm_pool = [
            *clinical_response.drug_drug_interactions,
            *clinical_response.drug_condition_interactions,
            *clinical_response.overdose_duplication_alerts,
        ]
        clinical_recommendations = list(clinical_response.clinical_recommendations)
    except Exception as exc:  # noqa: BLE001 — lỗi kết nối cụ thể đã được bắt bên trong
        # clinical_service (F3.5); catch biên này là phòng thủ cuối để LLM-down
        # KHÔNG BAO GIỜ làm chết endpoint — luôn còn kết quả rule-engine.
        logger.warning("LLM enrichment unavailable — trả kết quả rule-engine thuần: %s", exc)

    enriched: List[InteractionAlert] = []
    matched_ids: set[int] = set()
    for rule_alert in alerts:
        llm_match = _match_llm_alert(rule_alert, llm_pool)
        if llm_match is not None:
            matched_ids.add(id(llm_match))
            enriched.append(
                InteractionAlert(
                    severity=rule_alert.severity,  # RULE-ENGINE WINS [F3.3]
                    title=rule_alert.title,
                    description=getattr(llm_match, "description", "") or rule_alert.description,
                    recommendation=getattr(llm_match, "recommendation", "") or rule_alert.recommendation,
                )
            )
        else:
            enriched.append(rule_alert)

    # Alert LLM-only (rule-engine bỏ sót): giữ hành vi cũ — vẫn hiển thị.
    # severity truyền qua validator fail-safe của InteractionAlert (clamp lên
    # HIGH nếu lệch chuẩn — F3.2), không bao giờ bị hạ xuống LOW.
    for llm_alert in llm_pool:
        if id(llm_alert) not in matched_ids:
            enriched.append(
                InteractionAlert(
                    severity=str(getattr(llm_alert, "severity", "HIGH")),
                    title=str(getattr(llm_alert, "title", "")),
                    description=str(getattr(llm_alert, "description", "")),
                    recommendation=str(getattr(llm_alert, "recommendation", "")),
                )
            )

    # Sort HIGH trước — giữ hành vi cũ
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    enriched.sort(key=lambda a: severity_order.get(a.severity, 3))

    # schedule_suggestions: rule-engine là gốc; enrich thêm khuyến nghị LLM chưa trùng
    schedule_suggestions = list(eval_result.schedule_suggestions)
    seen_lower = {s.strip().lower() for s in schedule_suggestions}
    for rec in clinical_recommendations:
        if rec.strip() and rec.strip().lower() not in seen_lower:
            schedule_suggestions.append(rec)
            seen_lower.add(rec.strip().lower())

    eval_response = EvaluationResponse(
        total_drugs_analyzed=eval_result.total_drugs_analyzed,
        alerts=enriched,
        schedule_suggestions=schedule_suggestions,
        dosage_checks=eval_result.dosage_checks,  # [Task 5.5] Layer 4
        final_summary=eval_result.final_summary,  # [Task 5.5] tổng hợp 4 layer
        coverage_status=eval_result.coverage_status,
        drug_coverage_details=eval_result.drug_coverage_details,
        provenance_metadata=eval_result.provenance_metadata,
    )

    # ── BƯỚC 3: Tự động lưu Lịch sử (Internal Write) khi người dùng đã xác thực ─
    if current_user and current_user.id:
        try:
            from app.services.history_service import history_service
            from app.schemas.history_reminder_schema import ScanHistoryCreate

            highest_sev = "NONE"
            if any(a.severity == "HIGH" for a in enriched):
                highest_sev = "HIGH"
            elif any(a.severity == "MEDIUM" for a in enriched):
                highest_sev = "MEDIUM"
            elif any(a.severity == "LOW" for a in enriched):
                highest_sev = "LOW"

            drug_names = [d.brand_name for d in payload.drugs if d.brand_name]

            raw_snapshot = {
                "alerts": [a.model_dump(by_alias=True) for a in enriched],
                "dosageChecks": [dc.model_dump(by_alias=True) for dc in eval_result.dosage_checks],
                "finalSummary": eval_result.final_summary,
                "scheduleSuggestions": schedule_suggestions,
                "coverageStatus": eval_result.coverage_status,
                "drugCoverageDetails": [d.model_dump(by_alias=True) for d in eval_result.drug_coverage_details],
                "provenanceMetadata": eval_result.provenance_metadata.model_dump(by_alias=True) if eval_result.provenance_metadata else None,
                "drugs": [d.model_dump(by_alias=True) for d in payload.drugs],
            }

            await history_service.create_internal_history(
                db,
                user_id=current_user.id,
                data=ScanHistoryCreate(
                    source_type="manual",
                    drug_names=drug_names,
                    highest_severity=highest_sev,
                    summary=eval_result.final_summary,
                    raw_payload=raw_snapshot,
                ),
            )
        except Exception as hist_err:  # noqa: BLE001
            logger.warning("Không thể tự động lưu History cho evaluate: %s", hist_err)

    return eval_response


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)