# Service wrapper cho ONNX PP-OCRv6 (PaddleOCR 3.7+ / PaddleX).
# Chạy trên CPU qua engine 'onnxruntime' - KHÔNG cần gói 'paddlepaddle'.
# Tự động downscale ảnh (max dim 1600px) trước khi đưa vào pipeline OCR.
# Dual Pipeline: Stream A (Prescription/Receipt) & Stream B (Packaging Label)
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

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
)
from app.schemas.ocr_schema import MedicineScanResult, OCRItem


class OcrEngine:
    """Wrapper production cho PP-OCRv6 ONNX Runtime trên CPU với lazy singleton."""

    def __init__(self, lang: str = OCR_LANG, max_dim: int = OCR_MAX_DIM) -> None:
        self.lang = lang
        self.max_dim = max_dim
        self._paddle_ocr: Optional[Any] = None
        self._paddle_ocr_packaging: Optional[Any] = None

    @property
    def paddle_ocr(self) -> Any:
        """Khởi tạo PaddleOCR cho Stream A (Prescription/Receipt) - tối ưu cho hóa đơn in nhiệt."""
        if self._paddle_ocr is None:
            from paddleocr import PaddleOCR  # type: ignore[import-not-found]

            self._paddle_ocr = PaddleOCR(
                use_textline_orientation=True,
                device="cpu",
                lang=self.lang,
                engine=OCR_ENGINE,
                use_doc_orientation_classify=False,  # Tắt cho receipt thẳng đứng
                use_doc_unwarping=False,  # Tắt unwarping cho receipt
                # Tối ưu cho thermal receipt: text detection nhạy hơn
                text_det_thresh=0.3,
                text_det_box_thresh=0.5,
                text_det_unclip_ratio=1.6,
            )
        return self._paddle_ocr

    @property
    def paddle_ocr_packaging(self) -> Any:
        """Khởi tạo PaddleOCR cho Stream B (Packaging Label) - tối ưu cho bao bì đa hướng."""
        if self._paddle_ocr_packaging is None:
            from paddleocr import PaddleOCR  # type: ignore[import-not-found]

            self._paddle_ocr_packaging = PaddleOCR(
                use_textline_orientation=True,
                device="cpu",
                lang=self.lang,
                engine=OCR_ENGINE,
                use_doc_orientation_classify=OCR_DOC_ORIENTATION,  # Có thể bật cho packaging
                use_doc_unwarping=OCR_DOC_UNWARPING,  # Có thể bật cho packaging
                # Tối ưu cho bao bì: detect text theo nhiều hướng
                text_det_thresh=0.4,
                text_det_box_thresh=0.6,
                text_det_unclip_ratio=1.8,
            )
        return self._paddle_ocr_packaging

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

    def _enhance_receipt(self, image: "np.ndarray") -> "np.ndarray":
        """Tiền xử lý chuyên biệt cho hóa đơn in nhiệt (thermal receipt).
        - Tăng contrast, làm sắc nét text mờ
        - Khử nhiễu, điều chỉnh độ sáng"""
        if cv2 is None or Image is None or ImageEnhance is None or ImageFilter is None:
            return image
        
        # Chuyển sang PIL để enhance
        pil_img = Image.fromarray(image[:, :, ::-1])  # BGR -> RGB
        
        # Tăng contrast mạnh cho receipt mờ
        enhancer = ImageEnhance.Contrast(pil_img)
        pil_img = enhancer.enhance(1.8)
        
        # Tăng sharpness cho text dot-matrix
        enhancer = ImageEnhance.Sharpness(pil_img)
        pil_img = enhancer.enhance(2.0)
        
        # Điều chỉnh độ sáng nếu quá tối
        enhancer = ImageEnhance.Brightness(pil_img)
        pil_img = enhancer.enhance(1.2)
        
        # Lọc giảm nhiễu nhẹ
        pil_img = pil_img.filter(ImageFilter.MedianFilter(size=3))
        
        # Trở về numpy BGR
        return np.array(pil_img)[:, :, ::-1]

    def _enhance_packaging(self, image: "np.ndarray") -> "np.ndarray":
        """Tiền xử lý chuyên biệt cho vỏ hộp/lọ thuốc (packaging).
        - Xử lý phản quang, font 3D, in nổi
        - Cân bằng histogram để đều màu"""
        if cv2 is None:
            return image
        
        # Chuyển sang LAB để cân bằng kênh L (lightness) mà không làm lệch màu
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # CLAHE (Contrast Limited Adaptive Histogram Equalization) trên kênh L
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        # Gộp lại
        lab = cv2.merge((l, a, b))
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    def _load_array(self, data: bytes, source_type: str = "prescription") -> "np.ndarray":
        """Giải mã bytes ảnh (jpg/png/webp) thành numpy.ndarray BGR (downscale + enhance xong)."""
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
        
        # Downscale trước
        image = self.downscale(image)
        
        # Enhance theo source_type
        if source_type == "prescription":
            image = self._enhance_receipt(image)
        elif source_type == "packaging":
            image = self._enhance_packaging(image)
        
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
        - Tắt doc orientation/unwarping vì receipt thường thẳng đứng"""
        image = self._load_array(image_bytes, "prescription")
        height, width = image.shape[:2]

        start = time.perf_counter()
        result = self.paddle_ocr.predict(image)
        latency_ms = int(round((time.perf_counter() - start) * 1000))

        items = self._extract_items(result)
        return MedicineScanResult(
            engine="PP-OCRv6-ONNX",
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
        result = self.paddle_ocr_packaging.predict(image)
        latency_ms = int(round((time.perf_counter() - start) * 1000))

        items = self._extract_items(result)
        return MedicineScanResult(
            engine="PP-OCRv6-ONNX",
            source_type="packaging",
            items=items,
            latency_ms=latency_ms,
            sla_exceeded=latency_ms > OCR_PROCESSING_SLA_MS,
            image_width=width,
            image_height=height,
        )

    # Backward compatibility
    def scan(self, image_bytes: bytes, source_type: str = "prescription") -> MedicineScanResult:
        """Nhận bytes ảnh, trả về kết quả OCR chuẩn hóa (legacy method)."""
        if source_type == "packaging":
            return self.extract_packaging_label(image_bytes)
        return self.extract_prescription_receipt(image_bytes)


# Singleton dùng chung trong toàn app
ocr_engine = OcrEngine()