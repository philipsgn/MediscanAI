# Service wrapper cho ONNX PP-OCRv6 (PaddleOCR 3.7+ / PaddleX).
# Chạy trên CPU qua engine 'onnxruntime' - KHÔNG cần gói 'paddlepaddle'.
# Tự động downscale ảnh (max dim 1600px) trước khi đưa vào pipeline OCR.
# Dual Pipeline: Stream A (Prescription/Receipt) & Stream B (Packaging Label)
from __future__ import annotations

import asyncio
import logging
import os
import time
import threading
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Tắt connectivity check tới Baidu hosters để chạy offline mượt mà
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

try:
    import numpy as np
except ImportError:  # pragma: no cover - deps optional
    np = None  # type: ignore[assignment]

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError:
    Image = None
    ImageEnhance = None
    ImageFilter = None

from app.core.config import (
    OCR_DOC_ORIENTATION,
    OCR_DOC_UNWARPING,
    OCR_LANG,
    OCR_MAX_DIM,
    OCR_ENGINE,
    OCR_PROCESSING_SLA_MS,
    OCR_MODEL_DIR,
    OCR_ACTIVE_MODEL_VERSION,
    OCR_CUSTOM_DET_MODEL_DIR,
    OCR_CUSTOM_REC_MODEL_DIR,
)
from app.schemas.ocr_schema import MedicineScanResult, OCRItem
from app.services.ocr_model_registry import ModelArtifactManifest, ocr_model_registry


class OcrEngine:
    """Wrapper production cho PP-OCRv6 ONNX Runtime trên CPU với lazy singleton và Concurrency Control."""

    def __init__(
        self,
        lang: str = OCR_LANG,
        max_dim: int = OCR_MAX_DIM,
        max_concurrent: int = 2,
        active_version: str = OCR_ACTIVE_MODEL_VERSION,
    ) -> None:
        self.lang = lang
        self.max_dim = max_dim
        self.max_concurrent = max_concurrent
        self.active_version = active_version
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._paddle_ocr: Optional[Any] = None
        self._paddle_ocr_packaging: Optional[Any] = None
        self._lock = threading.Lock()

        if OCR_MODEL_DIR:
            os.environ["PADDLE_PDX_DIR"] = OCR_MODEL_DIR
            os.environ["PADDLE_HOME"] = OCR_MODEL_DIR

        # Nếu có custom model dirs được chỉ định qua config, đăng ký vào Registry
        if OCR_CUSTOM_DET_MODEL_DIR or OCR_CUSTOM_REC_MODEL_DIR:
            custom_manifest = ModelArtifactManifest(
                version=self.active_version,
                model_type="fine_tuned" if self.active_version != "ppocrv6_tiny_baseline" else "baseline",
                base_model="PP-OCRv6_tiny",
                domain="general",
                training_framework="PaddleOCR 3.7.0 / PaddleX 3.7.2",
                inference_runtime=OCR_ENGINE,
                text_detection_model_dir=OCR_CUSTOM_DET_MODEL_DIR,
                text_recognition_model_dir=OCR_CUSTOM_REC_MODEL_DIR,
                status="production",
            )
            ocr_model_registry.register_manifest(custom_manifest)

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Concurrency control semaphore (giới hạn số luồng suy luận OCR đồng thời để bảo vệ CPU)."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    def get_active_model_info(self) -> Dict[str, Any]:
        """Truy xuất thông tin mô hình OCR đang được kích hoạt."""
        manifest = ocr_model_registry.get_manifest(self.active_version)
        return {
            "active_version": self.active_version,
            "engine": OCR_ENGINE,
            "lang": self.lang,
            "max_dim": self.max_dim,
            "manifest": manifest.model_dump() if manifest else None,
        }

    @property
    def paddle_ocr(self) -> Any:
        """Khởi tạo PaddleOCR cho Stream A (Prescription/Receipt) - PP-OCRv6_tiny ONNX CPU."""
        with self._lock:
            if self._paddle_ocr is None:
                from paddleocr import PaddleOCR  # type: ignore[import-not-found]

                init_params = ocr_model_registry.resolve_runtime_params(
                    version=self.active_version,
                    stream_type="prescription",
                    orientation_enabled=False,
                    unwarping_enabled=False,
                )
                self._paddle_ocr = PaddleOCR(**init_params)
            return self._paddle_ocr

    @property
    def paddle_ocr_packaging(self) -> Any:
        """Khởi tạo PaddleOCR cho Stream B (Packaging Label) - PP-OCRv6_tiny ONNX CPU."""
        with self._lock:
            if self._paddle_ocr_packaging is None:
                from paddleocr import PaddleOCR  # type: ignore[import-not-found]

                init_params = ocr_model_registry.resolve_runtime_params(
                    version=self.active_version,
                    stream_type="packaging",
                    orientation_enabled=OCR_DOC_ORIENTATION,
                    unwarping_enabled=OCR_DOC_UNWARPING,
                )
                self._paddle_ocr_packaging = PaddleOCR(**init_params)
            return self._paddle_ocr_packaging

    def warmup(self) -> None:
        """Tạo ảnh 1x1 dummy để nạp ONNX kernels vào memory ở cả 2 luồng."""
        if np is None:
            return
        dummy_img = np.zeros((1, 1, 3), dtype=np.uint8)
        
        try:
            self.paddle_ocr.predict(dummy_img)
        except Exception:  # noqa: BLE001
            pass
            
        try:
            self.paddle_ocr_packaging.predict(dummy_img)
        except Exception:  # noqa: BLE001
            pass

    def close(self) -> None:
        if self._paddle_ocr is not None:
            try:
                self._paddle_ocr.close()
            except Exception:  # noqa: BLE001
                pass
            self._paddle_ocr = None
        if self._paddle_ocr_packaging is not None:
            try:
                self._paddle_ocr_packaging.close()
            except Exception:  # noqa: BLE001
                pass
            self._paddle_ocr_packaging = None

    def downscale(self, image: "np.ndarray") -> "np.ndarray":
        """Downscale giữ nguyên aspect ratio sao cho max(h, w) <= max_dim."""
        height, width = image.shape[:2]
        longest = max(height, width)
        if longest <= self.max_dim:
            return image

        scale = self.max_dim / longest
        new_w = max(1, round(width * scale))
        new_h = max(1, round(height * scale))

        if cv2 is not None:
            return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        if Image is None:
            raise RuntimeError("Thiếu 'opencv-python' hoặc 'pillow' để downscale.")
        rgb = Image.fromarray(image[:, :, ::-1] if image.ndim == 3 else image)
        rgb = rgb.resize((new_w, new_h), Image.LANCZOS)
        return np.array(rgb)[:, :, ::-1]  # type: ignore[no-any-return]

    def _load_array(self, data: bytes, source_type: str = "prescription") -> "np.ndarray":
        """Giải mã bytes ảnh (jpg/png/webp) thành numpy.ndarray BGR (downscale chuẩn hóa)."""
        if np is None:
            raise RuntimeError("Thiếu thư viện 'numpy'.")

        image = None
        if cv2 is not None:
            image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            if Image is None:
                raise RuntimeError("Thiếu 'opencv-python' hoặc 'pillow' để đọc ảnh.")
            with Image.open(__import__("io").BytesIO(data)) as img:
                image = np.array(img.convert("RGB"))[:, :, ::-1]  # RGB -> BGR
        
        # Downscale nếu ảnh vượt quá max_dim
        image = self.downscale(image)
        return image

    def _extract_items(self, result: Any) -> list[OCRItem]:
        """Trích OCRItem từ kết quả predict (hỗ trợ API PaddleX 3.7+ và cũ)."""
        items: list[OCRItem] = []

        try:
            for res in result:
                data = res if isinstance(res, dict) else dict(getattr(res, "json", {}))
                texts = data.get("rec_texts") or []
                scores = data.get("rec_scores") or []
                boxes = data.get("rec_boxes")

                has_boxes = boxes is not None and len(np.asarray(boxes)) > 0

                for i, text in enumerate(texts):
                    if not str(text).strip():
                        continue
                    conf = float(scores[i]) if i < len(scores) else 0.0
                    box: list[float] = []
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
                    items.append(OCRItem(text=str(text), confidence=round(conf, 4), box=box))
        except (TypeError, KeyError, AttributeError, IndexError):
            items = []

        if not items:
            # Fallback legacy: kết quả dạng (boxes, (text, score))
            try:
                for page in result or []:
                    for line in page or []:
                        if len(line) >= 2 and line[1]:
                            box = line[0]
                            items.append(
                                OCRItem(
                                    text=str(line[1][0]),
                                    confidence=round(float(line[1][1]), 4),
                                    box=[float(box[0][0]), float(box[0][1]), float(box[2][0]), float(box[2][1])],
                                )
                            )
            except (TypeError, KeyError, AttributeError, IndexError):
                items = []

        return items

    def extract_prescription_receipt(self, image_bytes: bytes) -> MedicineScanResult:
        """Stream A: OCR cho Toa thuốc / Hóa đơn in nhiệt (thermal receipt).
        - Tự động enhance contrast, sharpness cho text dot-matrix mờ
        - Tắt doc orientation/unwarping vì receipt thường thẳng đứng
        - [Stage 15] Tích hợp Hybrid Recognition: PP-OCR Detection + VietOCR Transformer tiếng Việt"""
        image = self._load_array(image_bytes, "prescription")
        height, width = image.shape[:2]

        start = time.perf_counter()
        try:
            result = self.paddle_ocr.predict(image)
        except Exception as exc:
            raise RuntimeError("OCR_INFERENCE_FAILED") from exc

        items = self._extract_items(result)

        # [Stage 15] VietOCR Hybrid Recognition cho đơn thuốc tiếng Việt
        used_vietocr = False
        try:
            from ai.pipelines.vietocr_engine import default_vietocr_recognizer
            if default_vietocr_recognizer.is_available and items and Image is not None:
                pil_img = Image.fromarray(image[:, :, ::-1] if image.ndim == 3 else image)

                # SLA Time-Budget Protection:
                # Giới hạn tối đa 8.0s và tối đa 6 crops cho VietOCR để tổng thời gian luôn < 10s (SLA < 15s)
                time_budget_sec = 8.0
                vietocr_start = time.perf_counter()
                processed_count = 0
                max_crops = 6

                def _needs_vietocr(t: str, c: float) -> bool:
                    lower = t.lower()
                    diacritic_typos = ("trra", "trua", "tôi", "tòi", "sô lung", "lrong", "trróc", "truóc", "ān no")
                    return any(typo in lower for typo in diacritic_typos)

                for item in items:
                    if processed_count >= max_crops or (time.perf_counter() - vietocr_start) > time_budget_sec:
                        break

                    if not _needs_vietocr(item.text, item.confidence):
                        continue

                    box = item.box
                    if box and len(box) == 4:
                        x_min, y_min, x_max, y_max = int(box[0]), int(box[1]), int(box[2]), int(box[3])
                        pad_x = max(2, int((x_max - x_min) * 0.02))
                        pad_y = max(2, int((y_max - y_min) * 0.05))
                        crop_x1 = max(0, x_min - pad_x)
                        crop_y1 = max(0, y_min - pad_y)
                        crop_x2 = min(width, x_max + pad_x)
                        crop_y2 = min(height, y_max + pad_y)

                        if crop_x2 > crop_x1 + 5 and crop_y2 > crop_y1 + 5:
                            crop = pil_img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                            v_text, v_conf = default_vietocr_recognizer.predict(crop)
                            if v_text and len(v_text.strip()) >= 2:
                                item.text = v_text.strip()
                                item.confidence = round(max(item.confidence, v_conf), 4)
                                used_vietocr = True
                                processed_count += 1
        except Exception as v_err:
            logger.warning("VietOCR hybrid recognition gặp sự cố, tiếp tục với PP-OCR: %s", v_err)

        latency_ms = int(round((time.perf_counter() - start) * 1000))
        engine_name = "PP-OCRv6+VietOCR_Transformer-Hybrid" if used_vietocr else "PP-OCRv6_tiny-ONNX"

        return MedicineScanResult(
            engine=engine_name,
            source_type="prescription",
            items=items,
            latency_ms=latency_ms,
            sla_exceeded=latency_ms > OCR_PROCESSING_SLA_MS,
            image_width=width,
            image_height=height,
        )

    def extract_packaging_label(self, image_bytes: bytes) -> MedicineScanResult:
        """Stream B: OCR cho Vỏ hộp / Lọ thuốc (Packaging Label).
        - Xử lý phản quang, font 3D/in nổi bằng CLAHE
        - Có thể bật doc orientation/unwarping cho ảnh chụp nghiêng"""
        image = self._load_array(image_bytes, "packaging")
        height, width = image.shape[:2]

        start = time.perf_counter()
        try:
            result = self.paddle_ocr_packaging.predict(image)
        except Exception as exc:
            raise RuntimeError("OCR_INFERENCE_FAILED") from exc
        latency_ms = int(round((time.perf_counter() - start) * 1000))

        items = self._extract_items(result)
        return MedicineScanResult(
            engine="PP-OCRv6_tiny-ONNX",
            source_type="packaging",
            items=items,
            latency_ms=latency_ms,
            sla_exceeded=latency_ms > OCR_PROCESSING_SLA_MS,
            image_width=width,
            image_height=height,
        )

    async def extract_prescription_receipt_async(self, image_bytes: bytes) -> MedicineScanResult:
        """Async wrapper được bảo vệ bởi concurrency semaphore."""
        from fastapi.concurrency import run_in_threadpool

        async with self.semaphore:
            return await run_in_threadpool(self.extract_prescription_receipt, image_bytes)

    async def extract_packaging_label_async(self, image_bytes: bytes) -> MedicineScanResult:
        """Async wrapper được bảo vệ bởi concurrency semaphore."""
        from fastapi.concurrency import run_in_threadpool

        async with self.semaphore:
            return await run_in_threadpool(self.extract_packaging_label, image_bytes)

    # Backward compatibility
    def scan(self, image_bytes: bytes, source_type: str = "prescription") -> MedicineScanResult:
        """Nhận bytes ảnh, trả về kết quả OCR chuẩn hóa (legacy method)."""
        if source_type == "packaging":
            return self.extract_packaging_label(image_bytes)
        return self.extract_prescription_receipt(image_bytes)


# Singleton dùng chung trong toàn app
ocr_engine = OcrEngine()