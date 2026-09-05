"""
Unit tests for VietOCR Hybrid Architecture & Prescription Recognition.
Validates singleton lifecycle, offline configuration loading, and graceful fallback.
"""

import pytest
import numpy as np
from PIL import Image

from ai.configs.ocr_config import default_ocr_config
from ai.pipelines.vietocr_engine import VietOCRRecognizer, default_vietocr_recognizer
from app.services.ocr_engine import OcrEngine


def test_vietocr_singleton_lifecycle():
    """Kiểm tra mô hình Singleton của VietOCRRecognizer."""
    rec1 = VietOCRRecognizer()
    rec2 = VietOCRRecognizer()
    assert rec1 is rec2
    assert rec1 is default_vietocr_recognizer


def test_vietocr_offline_config_existence():
    """Kiểm tra các tệp cấu hình offline base.yml và vgg-transformer.yml tồn tại."""
    import os
    assert os.path.exists(default_ocr_config.vietocr_base_config_path), "Thiếu base.yml"
    assert os.path.exists(default_ocr_config.vietocr_model_config_path), "Thiếu vgg-transformer.yml"


def test_vietocr_fallback_when_unavailable():
    """Kiểm tra cơ chế an toàn: predict trả về ("", 0.0) khi model chưa sẵn sàng hoặc crop hỏng."""
    recognizer = VietOCRRecognizer()
    # Tạo một ảnh rỗng đen nhỏ
    blank_img = Image.new("RGB", (50, 20), color=(0, 0, 0))
    text, conf = recognizer.predict(blank_img)
    # Không được văng Exception
    assert isinstance(text, str)
    assert isinstance(conf, float)


def test_ocr_engine_prescription_hybrid_integration():
    """Kiểm tra OcrEngine tích hợp mượt mà, không văng lỗi khi chạy extract_prescription_receipt."""
    import io
    engine = OcrEngine()
    
    # Tạo ảnh giả lập dạng JPEG in-memory
    dummy_img = Image.new("RGB", (400, 200), color=(255, 255, 255))
    buf = io.BytesIO()
    dummy_img.save(buf, format="JPEG")
    image_bytes = buf.getvalue()

    result = engine.extract_prescription_receipt(image_bytes)
    assert result.source_type == "prescription"
    assert isinstance(result.items, list)
    assert result.latency_ms >= 0
