"""
Personalized Clinical Health Profile Endpoints (Stage 9/10).
Quản lý các API: GET/POST/PUT /profile/me và /profile.
Tích hợp AsyncSession kết nối PostgreSQL Database.
"""

import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
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


def _get_request_id(request: Request) -> str:
    """Trích xuất hoặc khởi tạo correlation request_id."""
    if request:
        return (
            request.headers.get("X-Request-ID")
            or getattr(getattr(request, "state", None), "request_id", None)
            or str(uuid.uuid4())
        )
    return str(uuid.uuid4())


def _make_profile_error_detail(
    error_code: str,
    message: str,
    request_id: str,
    retryable: bool = False,
) -> Dict[str, Any]:
    """Unified 6-Key Error Contract cho phân hệ Profile."""
    return {
        "error_code": error_code,
        "message": message,
        "service": "profile",
        "stage": "profile_management",
        "request_id": request_id,
        "retryable": retryable,
    }


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy thông tin hồ sơ y tế người dùng hiện tại",
)
async def get_my_profile(
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Truy xuất hồ sơ bệnh nền, dị ứng và chỉ số cơ thể từ PostgreSQL."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id

    profile = await profile_service.get_profile(db, current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_profile_error_detail(
                error_code="PROFILE_NOT_FOUND",
                message="Tài khoản chưa khai báo hồ sơ y tế cá nhân.",
                request_id=request_id,
            ),
        )
    return profile


@router.post(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Tạo mới hoặc ghi đè hồ sơ y tế (/profile/me)",
)
@router.post(
    "",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Tạo mới hoặc ghi đè hồ sơ y tế (/profile)",
)
async def create_or_replace_profile(
    request: Request,
    response: Response,
    payload: UserProfileCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Tạo mới hoặc cập nhật hồ sơ y tế vào PostgreSQL và kích hoạt is_profile_completed = True."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id
    return await profile_service.upsert_profile(db, current_user.id, payload)


@router.put(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật hồ sơ y tế (/profile/me)",
)
@router.put(
    "",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật hồ sơ y tế (/profile)",
)
async def update_profile(
    request: Request,
    response: Response,
    payload: UserProfileUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Cập nhật một số thông tin y tế trong PostgreSQL."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id
    return await profile_service.update_profile(db, current_user.id, payload)

