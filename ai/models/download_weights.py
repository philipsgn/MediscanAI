"""
Download and Verification Script for ONNX OCR Model Weights.
Supports downloading pre-trained ONNX models or configuring local paths.
"""

import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent

MODEL_SOURCES = {
    "det_model": {
        "filename": "ch_PP-OCRv4_det_infer.onnx",
        "description": "PP-OCR Text Detection Model (ONNX)",
    },
    "rec_model": {
        "filename": "ch_PP-OCRv4_rec_infer.onnx",
        "description": "PP-OCR Text Recognition Model (ONNX)",
    },
    "cls_model": {
        "filename": "ch_ppocr_mobile_v2.0_cls_infer.onnx",
        "description": "PP-OCR Direction Classifier Model (ONNX)",
    }
}


def check_models_present() -> dict:
    """Kiểm tra xem các model ONNX đã có sẵn trong thư mục ai/models chưa."""
    status = {}
    for key, info in MODEL_SOURCES.items():
        filepath = MODELS_DIR / info["filename"]
        exists = filepath.exists() and filepath.stat().st_size > 0
        status[key] = {
            "path": str(filepath),
            "exists": exists,
            "filename": info["filename"]
        }
        if exists:
            logger.info(f"✔ Found {info['description']}: {filepath} ({filepath.stat().st_size / (1024*1024):.2f} MB)")
        else:
            logger.info(f"ℹ {info['description']} not found at {filepath} (PaddleOCR runtime fallback will be used)")
    return status


def ensure_models():
    """Đảm bảo thư mục models tồn tại và log tình trạng trọng số."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    status = check_models_present()
    return status


if __name__ == "__main__":
    ensure_models()
