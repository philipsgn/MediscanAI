"""
Personalized Clinical Health Profile Endpoints (Stage 9).
Quản lý các API: GET /profile/me, POST /profile, PUT /profile.
Yêu cầu Bearer Token xác thực người dùng.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.api.v1.endpoints.auth import get_current_user
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
) -> UserProfileResponse:
    """Truy xuất hồ sơ bệnh nền, dị ứng và chỉ số cơ thể của tài khoản hiện tại."""
    profile = profile_service.get_profile(current_user.id)
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
) -> UserProfileResponse:
    """Tạo mới hoặc cập nhật toàn bộ hồ sơ y tế cá nhân hóa gắn liền với user_id."""
    return profile_service.upsert_profile(current_user.id, payload)


@router.put(
    "",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật hồ sơ y tế",
)
async def update_profile(
    payload: UserProfileUpdate,
    current_user: UserResponse = Depends(get_current_user),
) -> UserProfileResponse:
    """Cập nhật một số thông tin y tế (bệnh nền, dị ứng, chiều cao, cân nặng)."""
    return profile_service.update_profile(current_user.id, payload)
