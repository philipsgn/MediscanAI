"""
Personalized Clinical Health Profile Endpoints (Stage 9/10).
Quản lý các API: GET /profile/me, POST /profile, PUT /profile.
Tích hợp AsyncSession kết nối PostgreSQL Database.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.schemas.user_profile_schema import (
    UserProfileCreate,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.schemas.user_schema import UserResponse
from app.services.profile_service import profile_service

router = APIRouter(prefix="/profile", tags=["Personalized Health Profile"])


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy thông tin hồ sơ y tế người dùng hiện tại",
)
async def get_my_profile(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Truy xuất hồ sơ bệnh nền, dị ứng và chỉ số cơ thể từ PostgreSQL."""
    profile = await profile_service.get_profile(db, current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tài khoản chưa khai báo hồ sơ y tế cá nhân.",
        )
    return profile


@router.post(
    "",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Tạo mới hoặc ghi đè hồ sơ y tế",
)
async def create_or_replace_profile(
    payload: UserProfileCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Tạo mới hoặc cập nhật hồ sơ y tế vào PostgreSQL và kích hoạt is_profile_completed = True."""
    return await profile_service.upsert_profile(db, current_user.id, payload)


@router.put(
    "",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật hồ sơ y tế",
)
async def update_profile(
    payload: UserProfileUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Cập nhật một số thông tin y tế trong PostgreSQL."""
    return await profile_service.update_profile(db, current_user.id, payload)
