"""
versioning.py

Centralized Version Registry & Lineage Metadata for Mediscan AI.
Bảo đảm không hardcode version rải rác; đóng vai trò Single Source of Truth
cho Data-Centric AI Platform, Active Learning Dataset và Model Lineage.
"""

import os
import subprocess
from functools import lru_cache
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


# ─────────────────────────────────────────────────────────────────────────────
# Centralized Version Registry Constants
# ─────────────────────────────────────────────────────────────────────────────

PIPELINE_VERSION: str = "2.1.0"
OCR_MODEL_VERSION: str = "ppocrv6-tiny-onnx-v1"
NORMALIZATION_VERSION: str = "fuzzy-4tier-v2"
CLINICAL_RULES_VERSION: str = "clinical-rules-4layer-v1.2"
CLINICAL_MODEL_VERSION: str = "gpt-4o-mini-clinical-v1"
PROMPT_VERSION: str = "prompt-clinical-assessment-v1.0"
DEFAULT_DATASET_VERSION: str = "mediscan-v1.0"


@lru_cache(maxsize=1)
def get_git_commit_hash() -> str:
    """Truy xuất short git commit hash của build hiện tại hoặc fallback sang env."""
    env_hash = os.getenv("GIT_COMMIT_HASH")
    if env_hash:
        return env_hash[:8]
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=2.0,
        )
        return output.decode("utf-8").strip()
    except Exception:
        return "local-build"


@lru_cache(maxsize=1)
def get_ocr_model_hash() -> str:
    """Trả về fingerprint hash định danh trọng số mô hình OCR ONNX."""
    return os.getenv("OCR_MODEL_HASH", "onnx-ppocrv6-tiny-sha256-verified")


class PipelineLineageMetadata(BaseModel):
    """Lineage metadata gắn liền với mọi scan record để truy xuất nguồn gốc."""

    pipeline_version: str = Field(default=PIPELINE_VERSION, description="Phiên bản pipeline tổng thể")
    ocr_model_version: str = Field(default=OCR_MODEL_VERSION, description="Phiên bản OCR model")
    ocr_model_hash: str = Field(default_factory=get_ocr_model_hash, description="Fingerprint hash trọng số OCR")
    git_commit_hash: str = Field(default_factory=get_git_commit_hash, description="Git commit hash của bản dựng")
    normalization_version: str = Field(default=NORMALIZATION_VERSION, description="Phiên bản chuẩn hóa dược phẩm")
    clinical_rules_version: str = Field(default=CLINICAL_RULES_VERSION, description="Phiên bản Rule Engine 4 tầng")
    clinical_model_version: str = Field(default=CLINICAL_MODEL_VERSION, description="Phiên bản mô hình lâm sàng")
    prompt_version: str = Field(default=PROMPT_VERSION, description="Phiên bản prompt template")
    dataset_version: Optional[str] = Field(default=DEFAULT_DATASET_VERSION, description="Phiên bản dataset liên kết")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


def get_current_pipeline_lineage(dataset_version: Optional[str] = None) -> PipelineLineageMetadata:
    """Trả về instance metadata hiện tại từ centralized constants."""
    return PipelineLineageMetadata(
        pipeline_version=PIPELINE_VERSION,
        ocr_model_version=OCR_MODEL_VERSION,
        ocr_model_hash=get_ocr_model_hash(),
        git_commit_hash=get_git_commit_hash(),
        normalization_version=NORMALIZATION_VERSION,
        clinical_rules_version=CLINICAL_RULES_VERSION,
        clinical_model_version=CLINICAL_MODEL_VERSION,
        prompt_version=PROMPT_VERSION,
        dataset_version=dataset_version or DEFAULT_DATASET_VERSION,
    )
