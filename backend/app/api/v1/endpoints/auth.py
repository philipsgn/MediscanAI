"""
Authentication API Endpoints (Stage 8/10).
Cung cấp các API: Register (201), Login (200), Get Current User Profile (200).
Tích hợp AsyncSession kết nối PostgreSQL Database.
"""

from typing import Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.schemas.user_schema import (
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication System"])
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Dependency trích xuất và xác thực JWT token từ Header Authorization: Bearer <token>."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu Token xác thực hoặc Token không hợp lệ.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = auth_service.decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token chứa thông tin người dùng không hợp lệ.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tài khoản người dùng không còn tồn tại trên hệ thống.",
        )

    return user


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản mới",
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def register(
    request: Request,
    payload: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Tạo tài khoản mới trong PostgreSQL, tự động băm mật khẩu và trả về JWT Session."""
    try:
        user = await auth_service.register_user(db, payload)
        access_token = auth_service.create_access_token(user.id)
        refresh_token = auth_service.create_refresh_token(user.id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user,
        )
    except ValueError as err:
        err_msg = str(err)
        status_code = status.HTTP_409_CONFLICT if "đã được sử dụng" in err_msg else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail=err_msg,
        ) from err


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Đăng nhập tài khoản",
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Xác thực Username/Email + Mật khẩu từ PostgreSQL và trả về JWT Session."""
    content_type = request.headers.get("content-type", "")
    login_data: Optional[UserLogin] = None

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form_data = await request.form()
        username_val = str(form_data.get("username") or form_data.get("usernameOrEmail") or "")
        password_val = str(form_data.get("password") or "")
        login_data = UserLogin(username=username_val, password=password_val)
    else:
        try:
            body_json = await request.json()
            login_data = UserLogin.model_validate(body_json)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Thiếu hoặc sai định dạng dữ liệu đăng nhập.",
            )

    try:
        user = await auth_service.authenticate_user(db, login_data)
        access_token = auth_service.create_access_token(user.id)
        refresh_token = auth_service.create_refresh_token(user.id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user,
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(err),
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy thông tin tài khoản hiện tại",
)
async def get_me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Trả về thông tin chi tiết người dùng (bao gồm cờ is_profile_completed)."""
    return current_user
