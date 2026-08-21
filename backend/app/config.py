# Config management for Mediscan AI Backend using pydantic-settings
import os
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
        "http://localhost:8000"
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()