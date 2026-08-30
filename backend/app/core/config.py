# Cấu hình Production cho Backend Mediscan AI — SINGLE SOURCE OF TRUTH.
# Toàn bộ Settings nền (API keys, LLM, OpenFDA, CORS) và các tham số vận hành
# OCR Engine (Stage 2) nằm tập trung tại đây, đúng vị trí kiến trúc theo
# STAGES.md Task 1.1 và ARCHITECTURE.md mục 6 (core/config.py).
# Mọi tham số OCR đều là field của Settings -> có thể override qua .env
# (xem backend/.env.example) mà không cần sửa code.
# (Trước đây Settings nằm ở app/config.py — đã hợp nhất, file cũ đã xoá.)
import os
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Mediscan AI Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # API Keys & External Services
    OPENAI_API_KEY: str = ""  # Fallback LLM text-only (không phải Vision), theo Task 3.3
    OPENAI_FALLBACK_MODEL: str = "gpt-4o-mini"  # [P3/F3.9] Model fallback qua env, không hardcode

    # Local LLM (for Clinical Assessment) - Ollama or similar
    LOCAL_LLM_BASE_URL: str = "http://localhost:11434"
    LOCAL_LLM_MODEL: str = "qwen2.5:0.5b"

    # OpenFDA Drug Database API
    OPENFDA_API_KEY: str = ""
    OPENFDA_BASE_URL: str = "https://api.fda.gov/drug"

    # Drug lookup autocomplete [S4-Closeout/F4.3] — mặc định top 10 kết quả,
    # client có thể override qua query param (giới hạn cứng 1..50 ở router).
    DRUG_SEARCH_DEFAULT_LIMIT: int = 10

    # JWT Authentication (Stage 8) — BẮT BUỘC có JWT_SECRET trong môi trường, cấm hardcode fallback
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 giờ
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7          # 7 ngày

    # Rate Limiting (chống Brute-force Login / Register)
    # Mặc định: 5 requests / phút theo IP cho các endpoint nhạy cảm
    AUTH_RATE_LIMIT: str = "5/minute"


    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        secret = (v or "").strip()
        insecure_fallbacks = {
            "",
            "mediscan-jwt-secret-key-production-change-me-2026",
            "secret",
            "change-me",
        }
        if secret in insecure_fallbacks:
            # Cho phép test runner chạy với ephemeral test secret
            if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("MEDISCAN_TEST_MODE") == "true":
                return "mediscan-ephemeral-test-secret-key-for-pytest-only-2026"
            raise ValueError(
                "CRITICAL SECURITY ERROR: JWT_SECRET environment variable is missing or using an insecure fallback. "
                "You MUST set a cryptographically secure JWT_SECRET in your environment or .env file "
                "(e.g. run: python -c 'import secrets; print(secrets.token_urlsafe(64))')."
            )
        return secret

    # Database Connection (PostgreSQL 16 Async via asyncpg / SQLite Async fallback)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mediscan_db"

    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # ── OCR Engine (Stage 2) — env-driven tuning & feature toggles ─────────
    # Giá trị mặc định giữ nguyên 100% như benchmark đã chốt SLA (avg 5.59s/ảnh CPU).
    OCR_MAX_DIM: int = 1600
    OCR_LANG: str = "vi"
    OCR_ENGINE: str = "onnxruntime"
    OCR_TEXT_REC_THRESHOLD: float = 0.5
    # Tat doc-orientation classifier + UVDoc unwarping: 2 stage preprocessing ton
    # nhieu CPU, chi huu ich voi scan quay vo/trang cong. Anh chup dien thoai
    # thang dung -> tat de dat Avg Latency < SLA (xem test-benchmark).
    OCR_DOC_ORIENTATION: bool = False
    OCR_DOC_UNWARPING: bool = False
    # SLA noi bo (ms)
    OCR_PROCESSING_SLA_MS: int = 15_000

    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Module-level aliases — giữ tương thích import cũ (services/ocr_engine.py và
# api/v1/endpoints/ocr.py dùng `from app.core.config import OCR_*`).
# Giá trị đọc từ Settings để override qua .env có hiệu lực toàn cục.
OCR_MAX_DIM: int = settings.OCR_MAX_DIM
OCR_LANG: str = settings.OCR_LANG
OCR_ENGINE: str = settings.OCR_ENGINE
OCR_TEXT_REC_THRESHOLD: float = settings.OCR_TEXT_REC_THRESHOLD
OCR_DOC_ORIENTATION: bool = settings.OCR_DOC_ORIENTATION
OCR_DOC_UNWARPING: bool = settings.OCR_DOC_UNWARPING
OCR_PROCESSING_SLA_MS: int = settings.OCR_PROCESSING_SLA_MS

__all__ = [
    "Settings",
    "settings",
    "OCR_MAX_DIM",
    "OCR_LANG",
    "OCR_ENGINE",
    "OCR_TEXT_REC_THRESHOLD",
    "OCR_DOC_ORIENTATION",
    "OCR_DOC_UNWARPING",
    "OCR_PROCESSING_SLA_MS",
]
