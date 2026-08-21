# Cấu hình Production cho Backend Mediscan AI.
# Settings nền vẫn được định nghĩa tại app.config (giữ tương thích toàn bộ
# services/ hiện có). Module này tập trung các hằng số vận hành cho OCR Engine.
from app.config import Settings, settings

# ONNX PP-OCRv6 - preprocessing
OCR_MAX_DIM: int = 1600
OCR_LANG: str = "vi"
OCR_ENGINE: str = "onnxruntime"
OCR_TEXT_REC_THRESHOLD: float = 0.5
# Tat doc-orientation classifier + UVDoc unwarping: 2 stage preprocessing ton
# nhieu CPU, chi huu ich voi scan quay vo/trang cong. Anh chup dien thoai
# thang dung -> tat de dat Avg Latency < SLA (xem test-benchmark).
OCR_DOC_ORIENTATION: bool = False
OCR_DOC_UNWARPING: bool = False

# SLA noi bo (ms)
OCR_PROCESSING_SLA_MS: int = 15_000

__all__ = [
    "Settings",
    "settings",
    "OCR_MAX_DIM",
    "OCR_LANG",
    "OCR_ENGINE",
    "OCR_TEXT_REC_THRESHOLD",
    "OCR_DOC_ORIENTATION",
    "OCR_DOC_UNWARPING",
    "OCR_PROCESSING_SLA_MS",
]