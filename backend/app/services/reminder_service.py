"""
Reminder Service — Quản lý Nhắc Nhở Uống Thuốc & Nhật Ký Tuân Thủ (Stage 10).
Lưu trữ thread-safe theo `user_id` tại backend/app/data/reminders.json.
Tự động tính chỉ số Tuân thủ điều trị (Adherence Rate %).
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from app.schemas.history_reminder_schema import (
    AdherenceStats,
    ReminderCreate,
    ReminderLogCreate,
    ReminderLogItem,
    ReminderResponse,
    ReminderUpdate,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REMINDERS_FILE = DATA_DIR / "reminders.json"


class ReminderService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._reminders: Dict[str, List[Dict[str, Any]]] = {}
        self._load_reminders()

    def _load_reminders(self) -> None:
        """Đọc danh sách nhắc nhở từ file JSON (nếu có)."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if REMINDERS_FILE.exists():
            try:
                with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                    self._reminders = json.load(f)
            except Exception as exc:
                logger.warning("Không thể đọc reminders.json, khởi tạo bộ nhớ trống: %s", exc)
                self._reminders = {}

    def _save_reminders(self) -> None:
        """Ghi danh sách nhắc nhở vào file JSON thread-safe."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._reminders, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error("Lỗi khi ghi reminders.json: %s", exc)

    def create_reminder(self, user_id: str, data: ReminderCreate) -> ReminderResponse:
        """Tạo một nhắc nhở uống thuốc mới cho user."""
        reminder_id = f"rem_{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc).isoformat()

        record = {
            "id": reminder_id,
            "user_id": user_id,
            "drug_name": data.drug_name.strip(),
            "dosage_instruction": data.dosage_instruction.strip() if data.dosage_instruction else None,
            "time_of_day": data.time_of_day,
            "reminder_time": data.reminder_time,
            "is_active": data.is_active,
            "created_at": created_at,
            "logs": [],
        }

        with self._lock:
            if user_id not in self._reminders:
                self._reminders[user_id] = []
            self._reminders[user_id].append(record)
            self._save_reminders()

        return ReminderResponse(**record)

    def get_reminders(self, user_id: str) -> List[ReminderResponse]:
        """Lấy tất cả các nhắc nhở của user."""
        with self._lock:
            user_items = self._reminders.get(user_id, [])
            return [ReminderResponse(**item) for item in user_items]

    def update_reminder(self, user_id: str, reminder_id: str, data: ReminderUpdate) -> ReminderResponse:
        """Cập nhật nhắc nhở của user."""
        with self._lock:
            user_items = self._reminders.get(user_id, [])
            target: Optional[Dict[str, Any]] = None
            for item in user_items:
                if item["id"] == reminder_id:
                    target = item
                    break

            if not target:
                raise ValueError("Không tìm thấy nhắc nhở.")

            if data.dosage_instruction is not None:
                target["dosage_instruction"] = data.dosage_instruction
            if data.time_of_day is not None:
                target["time_of_day"] = data.time_of_day
            if data.reminder_time is not None:
                target["reminder_time"] = data.reminder_time
            if data.is_active is not None:
                target["is_active"] = data.is_active

            self._save_reminders()
            return ReminderResponse(**target)

    def delete_reminder(self, user_id: str, reminder_id: str) -> bool:
        """Xóa nhắc nhở của user."""
        with self._lock:
            user_items = self._reminders.get(user_id, [])
            initial_len = len(user_items)
            self._reminders[user_id] = [r for r in user_items if r["id"] != reminder_id]
            if len(self._reminders[user_id]) < initial_len:
                self._save_reminders()
                return True
            return False

    def log_reminder(self, user_id: str, reminder_id: str, data: ReminderLogCreate) -> ReminderResponse:
        """Ghi nhận nhật ký trạng thái uống ('taken' | 'skipped')."""
        with self._lock:
            user_items = self._reminders.get(user_id, [])
            target: Optional[Dict[str, Any]] = None
            for item in user_items:
                if item["id"] == reminder_id:
                    target = item
                    break

            if not target:
                raise ValueError("Không tìm thấy nhắc nhở.")

            log_entry = {
                "log_id": f"log_{uuid.uuid4().hex[:8]}",
                "status": data.status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "notes": data.notes,
            }

            if "logs" not in target:
                target["logs"] = []
            target["logs"].insert(0, log_entry)

            self._save_reminders()
            return ReminderResponse(**target)

    def get_adherence_stats(self, user_id: str) -> AdherenceStats:
        """Tính toán thống kê tuân thủ điều trị (Adherence Rate %)."""
        with self._lock:
            user_items = self._reminders.get(user_id, [])
            total_reminders = len(user_items)
            taken_count = 0
            skipped_count = 0

            for r in user_items:
                for log in r.get("logs", []):
                    if log.get("status") == "taken":
                        taken_count += 1
                    elif log.get("status") == "skipped":
                        skipped_count += 1

            total_logs = taken_count + skipped_count
            rate = round((taken_count / total_logs) * 100.0, 1) if total_logs > 0 else 0.0

            return AdherenceStats(
                total_reminders=total_reminders,
                taken_count=taken_count,
                skipped_count=skipped_count,
                adherence_rate=rate,
            )


reminder_service = ReminderService()
