"""
Reminder Service — Quản lý Nhắc Nhở Uống Thuốc & Nhật Ký Tuân Thủ trong PostgreSQL.
"""

import copy
import logging
import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder import ReminderModel
from app.schemas.history_reminder_schema import (
    AdherenceStats,
    ReminderCreate,
    ReminderLogCreate,
    ReminderLogItem,
    ReminderResponse,
    ReminderUpdate,
)

logger = logging.getLogger(__name__)


class ReminderService:
    async def create_reminder(self, db: AsyncSession, user_id: str, data: ReminderCreate) -> ReminderResponse:
        """Tạo một nhắc nhở uống thuốc mới cho user vào PostgreSQL."""
        reminder_id = f"rem_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        record = ReminderModel(
            id=reminder_id,
            user_id=user_id,
            drug_name=data.drug_name.strip(),
            dosage_instruction=data.dosage_instruction.strip() if data.dosage_instruction else None,
            time_of_day=data.time_of_day,
            reminder_time=data.reminder_time,
            is_active=data.is_active,
            logs=[],
            created_at=now,
        )

        db.add(record)
        await db.commit()
        await db.refresh(record)

        return ReminderResponse(
            id=record.id,
            user_id=record.user_id,
            drug_name=record.drug_name,
            dosage_instruction=record.dosage_instruction,
            time_of_day=record.time_of_day,
            reminder_time=record.reminder_time,
            is_active=record.is_active,
            created_at=record.created_at.isoformat(),
            logs=[],
        )

    async def get_reminders(self, db: AsyncSession, user_id: str) -> List[ReminderResponse]:
        """Lấy tất cả các nhắc nhở của user."""
        stmt = select(ReminderModel).where(ReminderModel.user_id == user_id).order_by(ReminderModel.created_at)
        result = await db.execute(stmt)
        items = result.scalars().all()

        return [
            ReminderResponse(
                id=r.id,
                user_id=r.user_id,
                drug_name=r.drug_name,
                dosage_instruction=r.dosage_instruction,
                time_of_day=r.time_of_day,
                reminder_time=r.reminder_time,
                is_active=r.is_active,
                created_at=r.created_at.isoformat() if hasattr(r.created_at, "isoformat") else str(r.created_at),
                logs=[ReminderLogItem(**log) for log in (r.logs or [])],
            )
            for r in items
        ]

    async def update_reminder(self, db: AsyncSession, user_id: str, reminder_id: str, data: ReminderUpdate) -> ReminderResponse:
        """Cập nhật nhắc nhở của user."""
        stmt = select(ReminderModel).where(ReminderModel.id == reminder_id, ReminderModel.user_id == user_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            raise ValueError("Không tìm thấy nhắc nhở.")

        if data.dosage_instruction is not None:
            record.dosage_instruction = data.dosage_instruction
        if data.time_of_day is not None:
            record.time_of_day = data.time_of_day
        if data.reminder_time is not None:
            record.reminder_time = data.reminder_time
        if data.is_active is not None:
            record.is_active = data.is_active

        await db.commit()
        await db.refresh(record)

        return ReminderResponse(
            id=record.id,
            user_id=record.user_id,
            drug_name=record.drug_name,
            dosage_instruction=record.dosage_instruction,
            time_of_day=record.time_of_day,
            reminder_time=record.reminder_time,
            is_active=record.is_active,
            created_at=record.created_at.isoformat() if hasattr(record.created_at, "isoformat") else str(record.created_at),
            logs=[ReminderLogItem(**log) for log in (record.logs or [])],
        )

    async def delete_reminder(self, db: AsyncSession, user_id: str, reminder_id: str) -> bool:
        """Xóa nhắc nhở của user."""
        stmt = select(ReminderModel).where(ReminderModel.id == reminder_id, ReminderModel.user_id == user_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            return False

        await db.delete(record)
        await db.commit()
        return True

    async def log_reminder(self, db: AsyncSession, user_id: str, reminder_id: str, data: ReminderLogCreate) -> ReminderResponse:
        """Ghi nhận nhật ký trạng thái uống ('taken' | 'skipped')."""
        stmt = select(ReminderModel).where(ReminderModel.id == reminder_id, ReminderModel.user_id == user_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            raise ValueError("Không tìm thấy nhắc nhở.")

        log_entry = {
            "log_id": f"log_{uuid.uuid4().hex[:8]}",
            "status": data.status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": data.notes,
        }

        current_logs = list(record.logs or [])
        current_logs.insert(0, log_entry)
        record.logs = current_logs

        await db.commit()
        await db.refresh(record)

        return ReminderResponse(
            id=record.id,
            user_id=record.user_id,
            drug_name=record.drug_name,
            dosage_instruction=record.dosage_instruction,
            time_of_day=record.time_of_day,
            reminder_time=record.reminder_time,
            is_active=record.is_active,
            created_at=record.created_at.isoformat() if hasattr(record.created_at, "isoformat") else str(record.created_at),
            logs=[ReminderLogItem(**log) for log in record.logs],
        )

    async def get_adherence_stats(self, db: AsyncSession, user_id: str) -> AdherenceStats:
        """Tính toán thống kê tuân thủ điều trị (Adherence Rate %)."""
        stmt = select(ReminderModel).where(ReminderModel.user_id == user_id)
        result = await db.execute(stmt)
        items = result.scalars().all()

        total_reminders = len(items)
        taken_count = 0
        skipped_count = 0

        for r in items:
            for log in (r.logs or []):
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
