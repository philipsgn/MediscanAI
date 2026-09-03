"""
Medication Service — Quản lý Tủ thuốc (Cabinet) cá nhân hóa trong PostgreSQL.
Đảm bảo 100% Data Ownership theo user_id giải mã từ JWT token.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medication import UserMedicationModel
from app.schemas.history_reminder_schema import (
    PaginatedMedicationsResponse,
    UserMedicationCreate,
    UserMedicationResponse,
    UserMedicationUpdate,
)

logger = logging.getLogger(__name__)


class MedicationService:
    async def get_medications(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = False,
    ) -> PaginatedMedicationsResponse:
        """Lấy danh sách thuốc trong Tủ thuốc của user (hỗ trợ phân trang)."""
        base_query = select(UserMedicationModel).where(UserMedicationModel.user_id == user_id)
        if active_only:
            base_query = base_query.where(UserMedicationModel.is_active.is_(True))

        # Đếm tổng số bản ghi
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one() or 0

        # Lấy dữ liệu phân trang
        stmt = base_query.order_by(desc(UserMedicationModel.created_at)).limit(limit).offset(offset)
        result = await db.execute(stmt)
        items = result.scalars().all()

        has_more = (offset + len(items)) < total

        return PaginatedMedicationsResponse(
            items=[
                UserMedicationResponse(
                    id=m.id,
                    user_id=m.user_id,
                    brand_name=m.brand_name,
                    active_ingredient=m.active_ingredient,
                    strength=m.strength,
                    dosage_instruction=m.dosage_instruction,
                    duration_days=m.duration_days,
                    is_active=m.is_active,
                    notes=m.notes,
                    created_at=m.created_at.isoformat() if hasattr(m.created_at, "isoformat") else str(m.created_at),
                    updated_at=m.updated_at.isoformat() if hasattr(m.updated_at, "isoformat") else str(m.updated_at),
                )
                for m in items
            ],
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more,
        )

    async def get_medication_by_id(
        self,
        db: AsyncSession,
        user_id: str,
        medication_id: str,
    ) -> Optional[UserMedicationResponse]:
        """Truy xuất chi tiết một thuốc và đối soát quyền sở hữu."""
        stmt = select(UserMedicationModel).where(
            UserMedicationModel.id == medication_id,
            UserMedicationModel.user_id == user_id,
        )
        result = await db.execute(stmt)
        m = result.scalar_one_or_none()
        if not m:
            return None

        return UserMedicationResponse(
            id=m.id,
            user_id=m.user_id,
            brand_name=m.brand_name,
            active_ingredient=m.active_ingredient,
            strength=m.strength,
            dosage_instruction=m.dosage_instruction,
            duration_days=m.duration_days,
            is_active=m.is_active,
            notes=m.notes,
            created_at=m.created_at.isoformat() if hasattr(m.created_at, "isoformat") else str(m.created_at),
            updated_at=m.updated_at.isoformat() if hasattr(m.updated_at, "isoformat") else str(m.updated_at),
        )

    async def create_medication(
        self,
        db: AsyncSession,
        user_id: str,
        data: UserMedicationCreate,
    ) -> UserMedicationResponse:
        """Thêm mới một thuốc vào Tủ thuốc của user."""
        now = datetime.now(timezone.utc)
        record = UserMedicationModel(
            id=f"med_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            brand_name=data.brand_name.strip(),
            active_ingredient=data.active_ingredient.strip() if data.active_ingredient else None,
            strength=data.strength.strip() if data.strength else None,
            dosage_instruction=data.dosage_instruction.strip() if data.dosage_instruction else None,
            duration_days=data.duration_days,
            is_active=data.is_active,
            notes=data.notes.strip() if data.notes else None,
            created_at=now,
            updated_at=now,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        return UserMedicationResponse(
            id=record.id,
            user_id=record.user_id,
            brand_name=record.brand_name,
            active_ingredient=record.active_ingredient,
            strength=record.strength,
            dosage_instruction=record.dosage_instruction,
            duration_days=record.duration_days,
            is_active=record.is_active,
            notes=record.notes,
            created_at=record.created_at.isoformat(),
            updated_at=record.updated_at.isoformat(),
        )

    async def update_medication(
        self,
        db: AsyncSession,
        user_id: str,
        medication_id: str,
        data: UserMedicationUpdate,
    ) -> Optional[UserMedicationResponse]:
        """Cập nhật thông tin thuốc trong Tủ thuốc."""
        stmt = select(UserMedicationModel).where(
            UserMedicationModel.id == medication_id,
            UserMedicationModel.user_id == user_id,
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return None

        if data.brand_name is not None:
            record.brand_name = data.brand_name.strip()
        if data.active_ingredient is not None:
            record.active_ingredient = data.active_ingredient.strip()
        if data.strength is not None:
            record.strength = data.strength.strip()
        if data.dosage_instruction is not None:
            record.dosage_instruction = data.dosage_instruction.strip()
        if data.duration_days is not None:
            record.duration_days = data.duration_days
        if data.is_active is not None:
            record.is_active = data.is_active
        if data.notes is not None:
            record.notes = data.notes.strip()

        record.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(record)

        return UserMedicationResponse(
            id=record.id,
            user_id=record.user_id,
            brand_name=record.brand_name,
            active_ingredient=record.active_ingredient,
            strength=record.strength,
            dosage_instruction=record.dosage_instruction,
            duration_days=record.duration_days,
            is_active=record.is_active,
            notes=record.notes,
            created_at=record.created_at.isoformat(),
            updated_at=record.updated_at.isoformat(),
        )

    async def delete_medication(
        self,
        db: AsyncSession,
        user_id: str,
        medication_id: str,
    ) -> bool:
        """Xóa thuốc khỏi Tủ thuốc (tự động cascade xóa nhắc nhở liên quan)."""
        stmt = select(UserMedicationModel).where(
            UserMedicationModel.id == medication_id,
            UserMedicationModel.user_id == user_id,
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return False

        await db.delete(record)
        await db.commit()
        return True


medication_service = MedicationService()
