"""
VietOCR Recognizer Engine for MediScan AI.
Provides highly accurate Vietnamese diacritics recognition on cropped text line boxes.
Works seamlessly with local weights and offline configurations.
"""

from __future__ import annotations

import logging
import os
from typing import Any, List, Optional, Tuple
from PIL import Image
import yaml
import torch

# Tối ưu hóa đa luồng CPU cho PyTorch Transformer Inference
try:
    cpu_cores = os.cpu_count() or 4
    torch.set_num_threads(min(cpu_cores, 8))
except Exception:
    pass

from ai.configs.ocr_config import default_ocr_config

logger = logging.getLogger(__name__)


class VietOCRRecognizer:
    """Thread-safe Singleton wrapper cho VietOCR Predictor."""

    _instance: Optional[VietOCRRecognizer] = None

    def __new__(cls) -> VietOCRRecognizer:
        if cls._instance is None:
            cls._instance = super(VietOCRRecognizer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._predictor = None
        self._is_available = False
        self._init_error = None
        self._init_predictor()
        self._initialized = True

    def _init_predictor(self) -> None:
        if not default_ocr_config.vietocr_enabled:
            logger.info("VietOCR bị vô hiệu hóa trong cấu hình.")
            return

        weights_path = default_ocr_config.vietocr_weights_path
        if not os.path.exists(weights_path):
            logger.warning(
                "Chưa tìm thấy trọng số VietOCR tại: %s. Sẽ fallback về PP-OCR.",
                weights_path,
            )
            return

        try:
            from vietocr.tool.config import Cfg
            from vietocr.tool.predictor import Predictor

            # Nạp cấu hình offline từ tệp local, tránh hoàn toàn truy vấn ra vocr.vn
            base_cfg_path = default_ocr_config.vietocr_base_config_path
            model_cfg_path = default_ocr_config.vietocr_model_config_path

            config_dict = {}
            if os.path.exists(base_cfg_path):
                with open(base_cfg_path, "r", encoding="utf-8") as f:
                    config_dict.update(yaml.safe_load(f))
            if os.path.exists(model_cfg_path):
                with open(model_cfg_path, "r", encoding="utf-8") as f:
                    config_dict.update(yaml.safe_load(f))

            config_dict["weights"] = weights_path
            config_dict["device"] = "cpu"
            config_dict["predictor"] = {"beamsearch": False}

            cfg = Cfg(config_dict)
            self._predictor = Predictor(cfg)
            self._is_available = True
            logger.info("VietOCR Recognizer đã khởi tạo thành công từ trọng số local: %s", weights_path)
        except Exception as e:
            self._init_error = str(e)
            logger.error("Lỗi khi khởi tạo VietOCR Predictor: %s", e)
            self._predictor = None
            self._is_available = False

    def reload(self) -> bool:
        """Tái nạp lại predictor (hữu ích khi tải xong weights sau khi server đã chạy)."""
        self._init_predictor()
        return self.is_available

    @property
    def is_available(self) -> bool:
        return self._is_available and self._predictor is not None

    def predict(self, image: Image.Image) -> Tuple[str, float]:
        """Dự đoán văn bản từ ảnh crop dòng chữ.
        Trả về (text, confidence).
        """
        if not self.is_available:
            return "", 0.0

        try:
            # VietOCR predict() nhận PIL Image và trả về text kèm confidence
            res = self._predictor.predict(image, return_prob=True)
            if isinstance(res, tuple):
                text, prob = res
                return str(text).strip(), float(prob)
            return str(res).strip(), 0.95
        except Exception as err:
            logger.warning("VietOCR predict gặp lỗi trên crop: %s", err)
            return "", 0.0

    def predict_batch(self, images: List[Image.Image]) -> List[Tuple[str, float]]:
        """Dự đoán cho danh sách các crop dòng chữ."""
        return [self.predict(img) for img in images]


# Default singleton instance
default_vietocr_recognizer = VietOCRRecognizer()
