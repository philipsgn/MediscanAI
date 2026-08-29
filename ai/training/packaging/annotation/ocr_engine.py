"""Local packaging OCR with aspect-preserving preprocessing and boxes."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OCRResult:
    text: str
    confidence: float
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2


def preprocess_image(image_path: Path, max_dimension: int = 1800) -> object:
    """Return a grayscale, contrast-normalized, lightly deskewed image."""
    from PIL import Image, ImageOps
    image = Image.open(image_path).convert("RGB")
    scale = min(1.0, max_dimension / max(image.size))
    if scale < 1.0:
        image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.Resampling.LANCZOS)
    gray = ImageOps.grayscale(image)
    try:
        import cv2
        import numpy as np
        array = np.asarray(gray)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(array)
        # A small robust deskew estimate; near-horizontal text is left alone.
        points = cv2.findNonZero(cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1])
        if points is not None and len(points) > 20:
            angle = cv2.minAreaRect(points)[-1]
            angle = angle + 90 if angle < -45 else angle
            if abs(angle) < 12 and abs(angle) > 0.2:
                center = (enhanced.shape[1] / 2, enhanced.shape[0] / 2)
                matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                enhanced = cv2.warpAffine(enhanced, matrix, (enhanced.shape[1], enhanced.shape[0]), borderMode=cv2.BORDER_REPLICATE)
        return Image.fromarray(enhanced)
    except ImportError:
        return gray


class OCREngine:
    def __init__(self, language: str = "eng") -> None:
        self.language = language

    def extract(self, image_path: Path) -> list[OCRResult]:
        try:
            import pytesseract
            image = preprocess_image(image_path)
            data = pytesseract.image_to_data(image, lang=self.language, output_type=pytesseract.Output.DICT)
            results: list[OCRResult] = []
            for index, raw in enumerate(data.get("text", [])):
                text = str(raw).strip()
                try: confidence = max(0.0, min(1.0, float(data["conf"][index]) / 100))
                except (KeyError, ValueError, TypeError): confidence = 0.0
                if text and confidence >= 0:
                    x1, y1 = int(data["left"][index]), int(data["top"][index])
                    results.append(OCRResult(text, confidence, (x1, y1, x1 + int(data["width"][index]), y1 + int(data["height"][index]))))
            return results
        except (ImportError, OSError, RuntimeError) as exc:
            return [OCRResult(f"OCR unavailable: {type(exc).__name__}", 0.0, (0, 0, 0, 0))]
