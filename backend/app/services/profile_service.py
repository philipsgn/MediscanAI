"""
Profile Service — Quản lý Hồ sơ Y tế Cá nhân hóa lưu trữ trong PostgreSQL.
Tự động tính toán chỉ số BMI và kích hoạt cờ is_profile_completed = True cho User.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import UserProfileModel
from app.models.user import User
from app.schemas.user_profile_schema import (
    UserProfileCreate,
    UserProfileResponse,
    UserProfileUpdate,
)

logger = logging.getLogger(__name__)


def calculate_bmi(weight_kg: Optional[float], height_cm: Optional[float]) -> Optional[float]:
    """Tính chỉ số khối cơ thể BMI = weight_kg / (height_m ^ 2). Làm tròn 1 chữ số thập phân."""
    if weight_kg and height_cm and height_cm > 0:
        height_m = height_cm / 100.0
        return round(weight_kg / (height_m * height_m), 1)
    return None


class ProfileService:
    async def get_profile(self, db: AsyncSession, user_id: str) -> Optional[UserProfileResponse]:
        """Lấy hồ sơ y tế theo ID người dùng."""
        stmt = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
        result = await db.execute(stmt)
        p = result.scalar_one_or_none()
        if not p:
            return None
        return UserProfileResponse(
            user_id=p.user_id,
            age=p.age,
            birth_year=p.birth_year,
            gender=p.gender,
            weight_kg=p.weight_kg,
            height_cm=p.height_cm,
            bmi=p.bmi,
            conditions=p.conditions or [],
            allergies=p.allergies or [],
            is_pregnant=p.is_pregnant,
            is_breastfeeding=p.is_breastfeeding,
            updated_at=p.updated_at.isoformat() if hasattr(p.updated_at, "isoformat") else str(p.updated_at),
        )

    async def upsert_profile(self, db: AsyncSession, user_id: str, data: UserProfileCreate) -> UserProfileResponse:
        """Tạo mới hoặc cập nhật hồ sơ y tế cho người dùng và đánh dấu user.is_profile_completed = True."""
        bmi = calculate_bmi(data.weight_kg, data.height_cm)
        now = datetime.now(timezone.utc)

        stmt = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            profile = UserProfileModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                age=data.age,
                birth_year=data.birth_year,
                gender=data.gender,
                weight_kg=data.weight_kg,
                height_cm=data.height_cm,
                bmi=bmi,
                conditions=data.conditions,
                allergies=data.allergies,
                is_pregnant=data.is_pregnant or False,
                is_breastfeeding=data.is_breastfeeding or False,
                updated_at=now,
            )
            db.add(profile)
        else:
            profile.age = data.age
            profile.birth_year = data.birth_year
            profile.gender = data.gender
            profile.weight_kg = data.weight_kg
            profile.height_cm = data.height_cm
            profile.bmi = bmi
            profile.conditions = data.conditions
            profile.allergies = data.allergies
            profile.is_pregnant = data.is_pregnant or False
            profile.is_breastfeeding = data.is_breastfeeding or False
            profile.updated_at = now

        # Cập nhật cờ is_profile_completed = True trên bảng users
        user_stmt = select(User).where(User.id == user_id)
        user_res = await db.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if user:
            user.is_profile_completed = True
            user.updated_at = now

        await db.commit()
        await db.refresh(profile)

        return UserProfileResponse(
            user_id=profile.user_id,
            age=profile.age,
            birth_year=profile.birth_year,
            gender=profile.gender,
            weight_kg=profile.weight_kg,
            height_cm=profile.height_cm,
            bmi=profile.bmi,
            conditions=profile.conditions or [],
            allergies=profile.allergies or [],
            is_pregnant=profile.is_pregnant,
            is_breastfeeding=profile.is_breastfeeding,
            updated_at=profile.updated_at.isoformat(),
        )

    async def update_profile(self, db: AsyncSession, user_id: str, data: UserProfileUpdate) -> UserProfileResponse:
        """Cập nhật một phần hồ sơ y tế."""
        stmt = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            create_data = UserProfileCreate(
                age=data.age if data.age is not None else 30,
                birth_year=data.birth_year,
                gender=data.gender,
                weight_kg=data.weight_kg,
                height_cm=data.height_cm,
                conditions=data.conditions if data.conditions is not None else [],
                allergies=data.allergies if data.allergies is not None else [],
                is_pregnant=data.is_pregnant or False,
                is_breastfeeding=data.is_breastfeeding or False,
            )
            return await self.upsert_profile(db, user_id, create_data)

        if data.age is not None:
            profile.age = data.age
        if data.birth_year is not None:
            profile.birth_year = data.birth_year
        if data.gender is not None:
            profile.gender = data.gender
        if data.weight_kg is not None:
            profile.weight_kg = data.weight_kg
        if data.height_cm is not None:
            profile.height_cm = data.height_cm
        if data.conditions is not None:
            profile.conditions = data.conditions
        if data.allergies is not None:
            profile.allergies = data.allergies
        if data.is_pregnant is not None:
            profile.is_pregnant = data.is_pregnant
        if data.is_breastfeeding is not None:
            profile.is_breastfeeding = data.is_breastfeeding

        profile.bmi = calculate_bmi(profile.weight_kg, profile.height_cm)
        profile.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(profile)

        return UserProfileResponse(
            user_id=profile.user_id,
            age=profile.age,
            birth_year=profile.birth_year,
            gender=profile.gender,
            weight_kg=profile.weight_kg,
            height_cm=profile.height_cm,
            bmi=profile.bmi,
            conditions=profile.conditions or [],
            allergies=profile.allergies or [],
            is_pregnant=profile.is_pregnant,
            is_breastfeeding=profile.is_breastfeeding,
            updated_at=profile.updated_at.isoformat(),
        )


profile_service = ProfileService()
