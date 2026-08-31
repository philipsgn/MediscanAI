"""
storage_service.py

Abstraction Lưu trữ File Ảnh (Scan Storage Engine) cho Mediscan AI.
Phân định rạch ròi giữa:
- `image_sha256`: Fingerprint băm nội dung để đối soát / deduplication.
- `image_storage_ref`: Tham chiếu URI vật lý (ví dụ `file://data/storage/scans/{sha256}.jpg`) để truy xuất ảnh gốc phục vụ Review và Training Dataset.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple

from app.core.config import SCAN_STORAGE_DIR

logger = logging.getLogger(__name__)


class StorageService:
    """Quản lý lưu trữ và truy xuất ảnh scan phục vụ Data-Centric AI Platform."""

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.base_dir = Path(base_dir or SCAN_STORAGE_DIR)
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning("[STORAGE_INIT_WARNING] Could not create storage directory: %s", exc)

    def save_scan_image(self, image_bytes: bytes, suffix: str = ".jpg") -> Tuple[str, str]:
        """
        Lưu nội dung ảnh vào storage vật lý và trả về cặp (sha256, storage_ref).
        - image_sha256: 64 ký tự hex.
        - image_storage_ref: URI định dạng 'file://data/storage/scans/<sha256><suffix>'.
        """
        image_sha256 = hashlib.sha256(image_bytes).hexdigest()
        clean_suffix = suffix.lower() if suffix.startswith(".") else f".{suffix.lower()}"
        filename = f"{image_sha256}{clean_suffix}"
        target_path = self.base_dir / filename

        try:
            if not target_path.exists():
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(image_bytes)
                logger.debug("[STORAGE_SAVED] image_sha256=%s path=%s", image_sha256, target_path)
            storage_ref = f"file://{target_path.as_posix()}"
        except Exception as exc:
            logger.error("[STORAGE_WRITE_FAILED] sha256=%s error=%s", image_sha256, exc)
            storage_ref = f"unpersisted://sha256/{image_sha256}"

        return image_sha256, storage_ref

    def get_scan_image(self, storage_ref: str) -> Optional[bytes]:
        """Đọc nội dung bytes của ảnh từ storage_ref."""
        if not storage_ref or not storage_ref.startswith("file://"):
            return None
        file_path = Path(storage_ref.replace("file://", ""))
        if file_path.exists() and file_path.is_file():
            return file_path.read_bytes()
        return None

    def image_exists(self, storage_ref: str) -> bool:
        """Kiểm tra xem ảnh vật lý có tồn tại trên disk hay không."""
        if not storage_ref or not storage_ref.startswith("file://"):
            return False
        file_path = Path(storage_ref.replace("file://", ""))
        return file_path.exists() and file_path.is_file()


storage_service = StorageService()
