"""
Reminder Service — Quản lý Nhắc Nhở Uống Thuốc & Nhật Ký Tuân Thủ trong PostgreSQL.
Đảm bảo 100% Data Ownership và liên kết an toàn với Tủ thuốc (Cabinet).
"""

import copy
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medication import UserMedicationModel
from app.models.reminder import ReminderModel
from app.schemas.history_reminder_schema import (
    AdherenceStats,
    PaginatedRemindersOverviewResponse,
    ReminderCreate,
    ReminderLogCreate,
    ReminderLogItem,
    ReminderResponse,
    ReminderUpdate,
)

logger = logging.getLogger(__name__)


class ReminderService:
    async def create_reminder(
        self,
        db: AsyncSession,
        user_id: str,
        data: ReminderCreate,
    ) -> ReminderResponse:
        """Tạo một nhắc nhở uống thuốc mới cho user vào PostgreSQL."""
        # Nếu có medication_id -> kiểm tra thuốc thuộc quyền sở hữu của user_id
        if data.medication_id:
            med_stmt = select(UserMedicationModel).where(
                UserMedicationModel.id == data.medication_id,
                UserMedicationModel.user_id == user_id,
            )
            med_res = await db.execute(med_stmt)
            med = med_res.scalar_one_or_none()
            if not med:
                raise ValueError("MEDICATION_NOT_FOUND")

        reminder_id = f"rem_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        record = ReminderModel(
            id=reminder_id,
            user_id=user_id,
            medication_id=data.medication_id,
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
            medication_id=record.medication_id,
            drug_name=record.drug_name,
            dosage_instruction=record.dosage_instruction,
            time_of_day=record.time_of_day,
            reminder_time=record.reminder_time,
            is_active=record.is_active,
            created_at=record.created_at.isoformat(),
            logs=[],
        )

    async def get_reminders(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = False,
    ) -> PaginatedRemindersOverviewResponse:
        """Lấy danh sách nhắc nhở phân trang & thống kê tuân thủ điều trị của user."""
        base_query = select(ReminderModel).where(ReminderModel.user_id == user_id)
        if active_only:
            base_query = base_query.where(ReminderModel.is_active.is_(True))

        # Tổng số
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one() or 0

        # Phân trang
        stmt = base_query.order_by(ReminderModel.created_at).limit(limit).offset(offset)
        result = await db.execute(stmt)
        items = result.scalars().all()

        has_more = (offset + len(items)) < total
        stats = await self.get_adherence_stats(db, user_id)

        return PaginatedRemindersOverviewResponse(
            items=[
                ReminderResponse(
                    id=r.id,
                    user_id=r.user_id,
                    medication_id=r.medication_id,
                    drug_name=r.drug_name,
                    dosage_instruction=r.dosage_instruction,
                    time_of_day=r.time_of_day,
                    reminder_time=r.reminder_time,
                    is_active=r.is_active,
                    created_at=r.created_at.isoformat() if hasattr(r.created_at, "isoformat") else str(r.created_at),
                    logs=[ReminderLogItem(**log) for log in (r.logs or [])],
                )
                for r in items
            ],
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more,
            stats=stats,
        )

    async def update_reminder(
        self,
        db: AsyncSession,
        user_id: str,
        reminder_id: str,
        data: ReminderUpdate,
    ) -> Optional[ReminderResponse]:
        """Cập nhật nhắc nhở của user."""
        stmt = select(ReminderModel).where(ReminderModel.id == reminder_id, ReminderModel.user_id == user_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            return None

        if data.medication_id is not None:
            med_stmt = select(UserMedicationModel).where(
                UserMedicationModel.id == data.medication_id,
                UserMedicationModel.user_id == user_id,
            )
            med_res = await db.execute(med_stmt)
            med = med_res.scalar_one_or_none()
            if not med:
                raise ValueError("MEDICATION_NOT_FOUND")
            record.medication_id = data.medication_id

        if data.drug_name is not None:
            record.drug_name = data.drug_name.strip()
        if data.dosage_instruction is not None:
            record.dosage_instruction = data.dosage_instruction.strip()
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
            medication_id=record.medication_id,
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

    async def log_reminder(
        self,
        db: AsyncSession,
        user_id: str,
        reminder_id: str,
        data: ReminderLogCreate,
    ) -> Optional[ReminderResponse]:
        """Ghi nhận nhật ký trạng thái uống ('taken' | 'skipped'). Giới hạn 1 log/ngày/nhắc nhở."""
        stmt = select(ReminderModel).where(ReminderModel.id == reminder_id, ReminderModel.user_id == user_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            return None

        now = datetime.now(timezone.utc)
        today_date_str = now.strftime("%Y-%m-%d")

        current_logs = copy.deepcopy(record.logs or [])

        # Kiểm tra xem hôm nay đã có bản ghi log nào chưa
        existing_idx = -1
        for idx, log in enumerate(current_logs):
            ts = log.get("timestamp", "")
            if ts.startswith(today_date_str):
                existing_idx = idx
                break

        if existing_idx >= 0:
            # Cập nhật log của ngày hôm nay (thay vì thêm mới làm tăng số lần không giới hạn)
            current_logs[existing_idx]["status"] = data.status
            current_logs[existing_idx]["timestamp"] = now.isoformat()
            if data.notes is not None:
                current_logs[existing_idx]["notes"] = data.notes.strip() if data.notes else None
        else:
            # Tạo mới bản ghi duy nhất cho ngày hôm nay
            log_entry = {
                "log_id": f"log_{uuid.uuid4().hex[:8]}",
                "status": data.status,
                "timestamp": now.isoformat(),
                "notes": data.notes.strip() if data.notes else None,
            }
            current_logs.append(log_entry)

        record.logs = current_logs

        await db.commit()
        await db.refresh(record)

        return ReminderResponse(
            id=record.id,
            user_id=record.user_id,
            medication_id=record.medication_id,
            drug_name=record.drug_name,
            dosage_instruction=record.dosage_instruction,
            time_of_day=record.time_of_day,
            reminder_time=record.reminder_time,
            is_active=record.is_active,
            created_at=record.created_at.isoformat() if hasattr(record.created_at, "isoformat") else str(record.created_at),
            logs=[ReminderLogItem(**log) for log in record.logs],
        )

    async def get_adherence_stats(self, db: AsyncSession, user_id: str) -> AdherenceStats:
        """Tính toán tỉ lệ tuân thủ điều trị trong ngày và toàn bộ quá trình."""
        stmt = select(ReminderModel).where(ReminderModel.user_id == user_id)
        result = await db.execute(stmt)
        reminders = result.scalars().all()

        total_reminders = len(reminders)
        active_reminders = [r for r in reminders if r.is_active]
        today_total_scheduled = len(active_reminders)

        today_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        today_taken_count = 0
        today_skipped_count = 0
        overall_taken_count = 0
        overall_skipped_count = 0

        for r in reminders:
            for log in r.logs or []:
                st = log.get("status")
                ts = log.get("timestamp", "")
                is_today = ts.startswith(today_date_str)

                if st == "taken":
                    overall_taken_count += 1
                    if is_today:
                        today_taken_count += 1
                elif st == "skipped":
                    overall_skipped_count += 1
                    if is_today:
                        today_skipped_count += 1

        # Tỉ lệ tuân thủ trong ngày (%)
        if today_total_scheduled > 0:
            today_adherence_rate = round((today_taken_count / today_total_scheduled) * 100.0, 1)
        else:
            today_total_logs = today_taken_count + today_skipped_count
            today_adherence_rate = round((today_taken_count / today_total_logs) * 100.0, 1) if today_total_logs > 0 else 0.0

        # Tỉ lệ tuân thủ cả quá trình (%)
        overall_total_logs = overall_taken_count + overall_skipped_count
        overall_adherence_rate = round((overall_taken_count / overall_total_logs) * 100.0, 1) if overall_total_logs > 0 else 0.0

        return AdherenceStats(
            total_reminders=total_reminders,
            today_taken_count=today_taken_count,
            today_skipped_count=today_skipped_count,
            today_total_scheduled=today_total_scheduled,
            today_adherence_rate=min(today_adherence_rate, 100.0),
            taken_count=overall_taken_count,
            skipped_count=overall_skipped_count,
            adherence_rate=min(overall_adherence_rate, 100.0),
        )


reminder_service = ReminderService()
