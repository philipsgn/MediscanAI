# Cấu hình Production cho Backend Mediscan AI — SINGLE SOURCE OF TRUTH.
# Toàn bộ Settings nền (API keys, LLM, OpenFDA, CORS) và các tham số vận hành
# OCR Engine (Stage 2) nằm tập trung tại đây, đúng vị trí kiến trúc theo
# STAGES.md Task 1.1 và ARCHITECTURE.md mục 6 (core/config.py).
# Mọi tham số OCR đều là field của Settings -> có thể override qua .env
# (xem backend/.env.example) mà không cần sửa code.
# (Trước đây Settings nằm ở app/config.py — đã hợp nhất, file cũ đã xoá.)
from typing import List

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

    # OpenFDA Drug API
    OPENFDA_API_KEY: str = ""
    OPENFDA_BASE_URL: str = "https://api.fda.gov/drug"

    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
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
        env_file=".env",
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
