"""
Image Preprocessing Pipeline for MediScan AI.
Specialized for thermal receipts, prescription forms, and medicine box packaging.
Includes: Grayscale conversion, CLAHE contrast, Bilateral denoise, Auto-deskew, and Downscale.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple, Union
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError:
    Image = None

from ai.configs.ocr_config import default_ocr_config

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Module tiền xử lý ảnh chuyên sâu tối ưu cho OCR y tế."""

    def __init__(
        self,
        max_dim: int = default_ocr_config.max_dim,
        enable_clahe: bool = default_ocr_config.enable_clahe,
        clahe_clip_limit: float = default_ocr_config.clahe_clip_limit,
        clahe_tile_grid_size: tuple = default_ocr_config.clahe_tile_grid_size,
        enable_deskew: bool = default_ocr_config.enable_deskew,
        enable_denoise: bool = default_ocr_config.enable_denoise,
    ) -> None:
        self.max_dim = max_dim
        self.enable_clahe = enable_clahe
        self.clahe_clip_limit = clahe_clip_limit
        self.clahe_tile_grid_size = clahe_tile_grid_size
        self.enable_deskew = enable_deskew
        self.enable_denoise = enable_denoise

    def load_image(self, image_input: Union[bytes, str, np.ndarray]) -> np.ndarray:
        """Đọc ảnh từ raw bytes, đường dẫn tệp, hoặc numpy array thành numpy BGR."""
        if isinstance(image_input, np.ndarray):
            return image_input.copy()

        if isinstance(image_input, (str, bytes)):
            if isinstance(image_input, str):
                with open(image_input, "rb") as f:
                    data = f.read()
            else:
                data = image_input

            if cv2 is not None:
                img = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is not None:
                    return img

            if Image is not None:
                import io
                pil_img = Image.open(io.BytesIO(data)).convert("RGB")
                return np.array(pil_img)[:, :, ::-1]  # RGB -> BGR

        raise ValueError("Không thể giải mã định dạng ảnh đầu vào.")

    def downscale(self, image: np.ndarray, max_dim: Optional[int] = None) -> np.ndarray:
        """Downscale giữ nguyên tỉ lệ khung hình sao cho max(h, w) <= max_dim."""
        limit = max_dim or self.max_dim
        h, w = image.shape[:2]
        longest = max(h, w)
        if longest <= limit:
            return image

        scale = limit / float(longest)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))

        if cv2 is not None:
            return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

        if Image is not None:
            rgb = Image.fromarray(image[:, :, ::-1] if image.ndim == 3 else image)
            rgb = rgb.resize((new_w, new_h), Image.LANCZOS)
            return np.array(rgb)[:, :, ::-1]

        return image

    def apply_clahe(self, image: np.ndarray) -> np.ndarray:
        """Contrast Limited Adaptive Histogram Equalization (CLAHE) làm nét chữ mờ / in nhiệt."""
        if cv2 is None:
            return image

        if image.ndim == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(
                clipLimit=self.clahe_clip_limit,
                tileGridSize=self.clahe_tile_grid_size,
            )
            l = clahe.apply(l)
            merged = cv2.merge((l, a, b))
            return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        else:
            clahe = cv2.createCLAHE(
                clipLimit=self.clahe_clip_limit,
                tileGridSize=self.clahe_tile_grid_size,
            )
            return clahe.apply(image)

    def denoise(self, image: np.ndarray) -> np.ndarray:
        """Bilateral Filter khử nhiễu bề mặt nhưng giữ nguyên độ sắc nét cạnh ký tự."""
        if cv2 is None:
            return image

        if image.ndim == 3:
            return cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)
        else:
            return cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)

    def detect_skew_angle(self, image: np.ndarray) -> float:
        """Phát hiện góc nghiêng của văn bản dựa trên MinAreaRect và Hough Transform."""
        if cv2 is None:
            return 0.0

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # Tìm các điểm contours có text
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 50:
            return 0.0

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle
        else:
            angle = -angle

        # Giới hạn góc xoay hợp lý (-30 độ -> +30 độ) để tránh đảo lộn ảnh
        if abs(angle) > 30.0:
            return 0.0

        return float(angle)

    def rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Xoay ảnh theo góc xác định mà không làm mất góc cạnh."""
        if cv2 is None or abs(angle) < 0.5:
            return image

        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])

        # Tính toán kích thước mới sau khi xoay
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]

        return cv2.warpAffine(image, M, (new_w, new_h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    def auto_deskew(self, image: np.ndarray) -> np.ndarray:
        """Tự động phát hiện góc nghiêng và xoay thẳng văn bản."""
        angle = self.detect_skew_angle(image)
        if abs(angle) >= 0.5:
            logger.debug(f"Detected document skew angle: {angle:.2f}° - Rotating image")
            return self.rotate_image(image, angle)
        return image

    def preprocess(
        self,
        image_input: Union[bytes, str, np.ndarray],
        source_type: str = "prescription",
    ) -> Tuple[np.ndarray, dict]:
        """
        Chạy toàn bộ pipeline tiền xử lý:
        1. Load & downscale
        2. Auto-deskew
        3. CLAHE contrast enhancement
        4. Bilateral Denoise
        Trả về (ảnh_sau_xử_lý, thông_tin_metadata).
        """
        raw = self.load_image(image_input)
        orig_h, orig_w = raw.shape[:2]

        processed = self.downscale(raw)

        if self.enable_deskew:
            processed = self.auto_deskew(processed)

        if self.enable_clahe:
            processed = self.apply_clahe(processed)

        if self.enable_denoise:
            processed = self.denoise(processed)

        meta = {
            "original_width": orig_w,
            "original_height": orig_h,
            "processed_width": processed.shape[1],
            "processed_height": processed.shape[0],
            "source_type": source_type,
        }

        return processed, meta


# Global default instance
default_preprocessor = ImagePreprocessor()
