# Entrypoint chính cho FastAPI Backend Service Mediscan AI
# Pure Local OCR + Clinical Assessment Pipeline (No External VLM)
import logging
from contextlib import asynccontextmanager
from typing import Any, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints.ocr import router as ocr_router
from app.core.config import settings
from app.schemas import (
    DrugEvaluationRequest,
    EvaluationResponse,
    InteractionAlert,
)
from app.services.clinical_service import ClinicalAssessmentRequest, clinical_service
from app.services.evaluation_service import evaluation_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
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

# Cấu hình CORS mở rộng hỗ trợ Web Desktop & Mobile
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route OCR + Clinical Assessment Pipeline
app.include_router(ocr_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Health Check"])
async def root() -> dict[str, str]:
    return {
        "status": "online",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs"
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
async def evaluate_interactions(payload: DrugEvaluationRequest) -> EvaluationResponse:
    """
    Đánh giá tương tác thuốc (giữ nguyên contract legacy cho frontend).
    BƯỚC 1 — Rule-engine Stage 5 quyết định tập alert + severity cuối cùng.
    BƯỚC 2 — LLM chỉ enrich description/recommendation bằng ngôn ngữ tự nhiên.
    Layer 1: Overdose/Duplicate · Layer 2: Drug-Drug · Layer 3: Drug-Condition.
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

    return EvaluationResponse(
        total_drugs_analyzed=eval_result.total_drugs_analyzed,
        alerts=enriched,
        schedule_suggestions=schedule_suggestions,
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)