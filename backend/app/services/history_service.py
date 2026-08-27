"""
History Service — Quản lý Lịch sử Quét & Đánh giá Tương tác Thuốc (Stage 10).
Lưu trữ thread-safe theo `user_id` tại backend/app/data/scan_history.json.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List

from app.schemas.history_reminder_schema import (
    ScanHistoryCreate,
    ScanHistoryResponse,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HISTORY_FILE = DATA_DIR / "scan_history.json"


class HistoryService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._histories: Dict[str, List[Dict[str, Any]]] = {}
        self._load_histories()

    def _load_histories(self) -> None:
        """Đọc lịch sử scan từ file JSON (nếu có)."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self._histories = json.load(f)
            except Exception as exc:
                logger.warning("Không thể đọc scan_history.json, khởi tạo bộ nhớ trống: %s", exc)
                self._histories = {}

    def _save_histories(self) -> None:
        """Ghi lịch sử scan vào file JSON thread-safe."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._histories, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error("Lỗi khi ghi scan_history.json: %s", exc)

    def save_history(self, user_id: str, data: ScanHistoryCreate) -> ScanHistoryResponse:
        """Lưu lại một phiên quét & đánh giá thuốc gắn liền với user_id."""
        history_id = f"hist_{uuid.uuid4().hex[:12]}"
        scanned_at = datetime.now(timezone.utc).isoformat()

        record = {
            "id": history_id,
            "user_id": user_id,
            "scanned_at": scanned_at,
            "source_type": data.source_type,
            "drug_names": data.drug_names,
            "highest_severity": data.highest_severity,
            "summary": data.summary,
            "raw_payload": data.raw_payload,
        }

        with self._lock:
            if user_id not in self._histories:
                self._histories[user_id] = []
            # Thêm vào đầu danh sách (phiên mới nhất xếp trước)
            self._histories[user_id].insert(0, record)
            self._save_histories()

        return ScanHistoryResponse(**record)

    def get_histories(self, user_id: str) -> List[ScanHistoryResponse]:
        """Truy xuất danh sách lịch sử các phiên scan của một user_id."""
        with self._lock:
            user_items = self._histories.get(user_id, [])
            return [ScanHistoryResponse(**item) for item in user_items]


history_service = HistoryService()
