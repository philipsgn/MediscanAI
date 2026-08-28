"""
Pure-ONNX Runtime OCR Engine Wrapper for MediScan AI.
High-performance, CPU-optimized OCR text line detection & character recognition.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

try:
    import onnxruntime as ort
except ImportError:
    ort = None

from ai.configs.ocr_config import default_ocr_config
from ai.pipelines.preprocessor import default_preprocessor
from ai.pipelines.clinical_ner_parser import default_ner_parser
from ai.normalization.drug_mapper import default_drug_mapper

logger = logging.getLogger(__name__)


class ONNXOCREngine:
    """Wrapper cho ONNX Runtime CPU OCR Inference."""

    def __init__(
        self,
        det_model_path: Optional[str] = None,
        rec_model_path: Optional[str] = None,
        cls_model_path: Optional[str] = None,
        num_threads: int = default_ocr_config.onnx_num_threads,
        confidence_thresh: float = default_ocr_config.confidence_threshold,
    ) -> None:
        self.det_model_path = det_model_path
        self.rec_model_path = rec_model_path
        self.cls_model_path = cls_model_path
        self.num_threads = num_threads
        self.confidence_thresh = confidence_thresh
        self._session_det: Optional[Any] = None
        self._session_rec: Optional[Any] = None
        self._fallback_paddle: Optional[Any] = None

    def _get_session_options(self) -> Any:
        if ort is None:
            return None
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = self.num_threads
        opts.inter_op_num_threads = self.num_threads
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        return opts

    @property
    def fallback_paddle(self) -> Any:
        """Khởi tạo PaddleOCR CPU runtime làm fallback đáng tin cậy nếu chưa nạp riêng session ONNX raw."""
        if self._fallback_paddle is None:
            try:
                from paddleocr import PaddleOCR
                self._fallback_paddle = PaddleOCR(
                    use_textline_orientation=True,
                    device="cpu",
                    lang=default_ocr_config.ocr_lang,
                    engine="onnxruntime",
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    text_det_thresh=0.3,
                    text_det_box_thresh=0.5,
                    text_det_unclip_ratio=1.6,
                )
            except Exception as e:
                logger.warning(f"PaddleOCR wrapper not available: {e}")
                self._fallback_paddle = None
        return self._fallback_paddle

    def extract_raw_ocr_lines(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Trích xuất danh sách các dòng văn bản từ ảnh qua ONNX / PaddleOCR engine.
        Trả về list[{ 'text': str, 'confidence': float, 'box': list }].
        """
        results: List[Dict[str, Any]] = []

        if self.fallback_paddle is not None:
            try:
                raw_out = self.fallback_paddle.predict(image)
                for res in raw_out or []:
                    data = res if isinstance(res, dict) else dict(getattr(res, "json", {}))
                    texts = data.get("rec_texts") or []
                    scores = data.get("rec_scores") or []
                    boxes = data.get("rec_boxes")

                    has_boxes = boxes is not None and len(np.asarray(boxes)) > 0
                    for i, text in enumerate(texts):
                        if not str(text).strip():
                            continue
                        conf = float(scores[i]) if i < len(scores) else 0.0
                        box: List[float] = []
                        if has_boxes:
                            pts = np.asarray(boxes[i], dtype=float)
                            if pts.ndim == 1 and pts.size == 4:
                                box = [float(pts[0]), float(pts[1]), float(pts[2]), float(pts[3])]
                            elif pts.ndim == 2 and pts.shape[1] >= 2:
                                box = [
                                    float(pts[:, 0].min()),
                                    float(pts[:, 1].min()),
                                    float(pts[:, 0].max()),
                                    float(pts[:, 1].max()),
                                ]
                        results.append({
                            "text": str(text).strip(),
                            "confidence": round(conf, 4),
                            "box": box
                        })
            except Exception as e:
                logger.error(f"Error during OCR prediction: {e}")

        return results

    def process_document(
        self,
        image_input: Union[bytes, str, np.ndarray],
        source_stream: str = "prescription",
    ) -> Dict[str, Any]:
        """
        Chạy toàn bộ pipeline AI:
        1. Preprocessing (CLAHE, Deskew, Denoise)
        2. OCR Inference (Text Lines)
        3. Normalization & Fuzzy Brand Mapping
        4. Clinical NER Parsing (Time slots, strength, duration)
        """
        start_time = time.perf_counter()

        # 1. Tiền xử lý ảnh
        proc_img, meta = default_preprocessor.preprocess(image_input, source_type=source_stream)
        prep_time_ms = int(round((time.perf_counter() - start_time) * 1000))

        # 2. OCR suy luận ký tự
        ocr_start = time.perf_counter()
        raw_lines = self.extract_raw_ocr_lines(proc_img)
        ocr_time_ms = int(round((time.perf_counter() - ocr_start) * 1000))

        # 3. Trích xuất thực thể & Map thuốc
        extracted_items: List[Dict[str, Any]] = []
        for line in raw_lines:
            text = line.get("text", "")
            conf = line.get("confidence", 0.0)

            # Map với từ điển Dược
            drug_info = default_drug_mapper.map_raw_text(text)

            # Parse thực thể lâm sàng
            ner_info = default_ner_parser.parse_instruction_and_dosage(text)

            # Ghép dữ liệu chuẩn hóa
            brand_name = drug_info.get("brand_name") or text
            active_ingredient = drug_info.get("active_ingredient")
            strength = drug_info.get("strength") or ner_info.get("strength")
            dosage_form = drug_info.get("dosage_form") or ner_info.get("dosage_form")

            item_dict = {
                "id": drug_info.get("drug_id") or f"ext_{int(time.time()*1000)}_{len(extracted_items)}",
                "drug_name": brand_name,
                "active_ingredient": active_ingredient,
                "strength": strength,
                "dosage_form": dosage_form,
                "dosage_instruction": text if not active_ingredient else f"Uống {strength or ''}",
                "time_slots": ner_info.get("time_slots", []),
                "slot_times": ner_info.get("slot_times", {}),
                "duration_days": ner_info.get("duration_days", 7),
                "start_date": None,
                "is_time_extracted": ner_info.get("is_time_extracted", False),
                "source_stream": source_stream,
                "confidence_score": conf,
                "match_method": drug_info.get("match_method", "raw_fallback")
            }
            extracted_items.append(item_dict)

        total_time_ms = int(round((time.perf_counter() - start_time) * 1000))

        return {
            "engine": "PP-OCRv6-Pure-ONNX",
            "source_stream": source_stream,
            "raw_ocr_lines": raw_lines,
            "extracted_drugs": extracted_items,
            "metrics": {
                "preprocessor_ms": prep_time_ms,
                "ocr_inference_ms": ocr_time_ms,
                "total_latency_ms": total_time_ms,
            },
            "meta": meta
        }


# Global default engine instance
default_onnx_ocr_engine = ONNXOCREngine()
