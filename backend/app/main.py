# Entrypoint chính cho FastAPI Backend Service Mediscan AI
# Pure Local OCR + Clinical Assessment Pipeline (No External VLM)
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints.ocr import router as ocr_router
from app.config import settings
from app.schemas import (
    DrugEvaluationRequest,
    EvaluationResponse,
    InteractionAlert,
)


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

# Legacy /evaluate endpoint - now uses Clinical LLM Service internally
# Kept for backward compatibility with existing frontend
@app.post(
    f"{settings.API_V1_STR}/evaluate",
    response_model=EvaluationResponse,
    tags=["Clinical Assessment Engine"],
)
async def evaluate_interactions(payload: DrugEvaluationRequest) -> EvaluationResponse:
    """
    Endpoint đánh giá tương tác thuốc - sử dụng Clinical LLM Service.
    Layer 1: Overdose / Duplicate Active Ingredient
    Layer 2: Drug-Drug Interactions
    Layer 3: Drug-Condition Conflicts (nếu có user_profile)
    """
    try:
        from app.services.clinical_service import clinical_service, ClinicalAssessmentRequest

        assessment_request = ClinicalAssessmentRequest(
            drugs=payload.drugs,
            user_profile=payload.user_profile,
        )
        clinical_response = await clinical_service.assess(assessment_request)

        # Convert ClinicalAssessmentResponse -> EvaluationResponse (legacy format)
        alerts = []
        for alert in clinical_response.drug_drug_interactions:
            alerts.append(InteractionAlert(
                severity=alert.severity,
                title=alert.title,
                description=alert.description,
                recommendation=alert.recommendation,
            ))
        for alert in clinical_response.drug_condition_interactions:
            alerts.append(InteractionAlert(
                severity=alert.severity,
                title=alert.title,
                description=alert.description,
                recommendation=alert.recommendation,
            ))
        for alert in clinical_response.overdose_duplication_alerts:
            alerts.append(InteractionAlert(
                severity=alert.severity,
                title=alert.title,
                description=alert.description,
                recommendation=alert.recommendation,
            ))

        # Sort by severity
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 3))

        return EvaluationResponse(
            total_drugs_analyzed=len(payload.drugs),
            alerts=alerts,
            schedule_suggestions=clinical_response.clinical_recommendations,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi phân tích tương tác thuốc: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)