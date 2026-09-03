"""
Authentication API Endpoints (Stage 8/10).
Cung cấp các API: Register (201), Login (200), Refresh (200), Get Current User Profile (200).
Chuẩn hóa 100% Unified 6-Key Error Contract (Stage 8.1).
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.schemas.user_schema import (
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication System"])
security = HTTPBearer(auto_error=False)


def _make_auth_error_detail(
    error_code: str,
    message: str,
    stage: str = "authentication",
    request_id: str = "",
    service: str = "auth",
    retryable: bool = False,
) -> dict:
    """Tạo cấu trúc lỗi chuẩn 6-key đồng nhất cho Auth phân hệ."""
    return {
        "error_code": error_code,
        "message": message,
        "service": service,
        "stage": stage,
        "request_id": request_id,
        "retryable": retryable,
    }


def _get_request_id(request: Optional[Request] = None) -> str:
    if request:
        return request.headers.get("X-Request-ID") or getattr(getattr(request, "state", None), "request_id", None) or str(uuid.uuid4())
    return str(uuid.uuid4())


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Dependency trích xuất và xác thực JWT token từ Header Authorization: Bearer <token>."""
    request_id = _get_request_id(request)

    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_make_auth_error_detail(
                error_code="UNAUTHORIZED",
                message="Thiếu Token xác thực hoặc Token không hợp lệ.",
                request_id=request_id,
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = auth_service.decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_make_auth_error_detail(
                error_code="INVALID_TOKEN",
                message="Token không hợp lệ hoặc đã hết hạn.",
                request_id=request_id,
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_make_auth_error_detail(
                error_code="INVALID_TOKEN",
                message="Token chứa thông tin người dùng không hợp lệ.",
                request_id=request_id,
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_service.get_user_model_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_auth_error_detail(
                error_code="USER_NOT_FOUND",
                message="Tài khoản người dùng không còn tồn tại trên hệ thống.",
                request_id=request_id,
            ),
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_make_auth_error_detail(
                error_code="USER_INACTIVE",
                message="Tài khoản người dùng đã bị vô hiệu hóa.",
                request_id=request_id,
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_profile_completed=user.is_profile_completed,
        created_at=user.created_at.isoformat() if hasattr(user.created_at, "isoformat") else str(user.created_at),
    )


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[UserResponse]:
    """Dependency trích xuất user nếu có token hợp lệ, trả về None nếu không gửi token hoặc token invalid/inactive."""
    if not credentials or not credentials.credentials:
        return None

    token = credentials.credentials
    payload = auth_service.decode_token(token)
    if not payload or payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = await auth_service.get_user_model_by_id(db, user_id)
    if not user or not user.is_active:
        return None

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_profile_completed=user.is_profile_completed,
        created_at=user.created_at.isoformat() if hasattr(user.created_at, "isoformat") else str(user.created_at),
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản mới",
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
async def register(
    request: Request,
    response: Response,
    payload: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Tạo tài khoản mới trong PostgreSQL, tự động băm mật khẩu và trả về JWT Session."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id

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
        is_dup = "đã được sử dụng" in err_msg
        status_code = status.HTTP_409_CONFLICT if is_dup else status.HTTP_400_BAD_REQUEST
        error_code = "USER_ALREADY_EXISTS" if is_dup else "REGISTRATION_FAILED"
        raise HTTPException(
            status_code=status_code,
            detail=_make_auth_error_detail(
                error_code=error_code,
                message=err_msg,
                request_id=request_id,
            ),
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
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Xác thực Username/Email + Mật khẩu từ PostgreSQL và trả về JWT Session."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id

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
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_make_auth_error_detail(
                    error_code="INVALID_REQUEST_PAYLOAD",
                    message="Thiếu hoặc sai định dạng dữ liệu đăng nhập.",
                    request_id=request_id,
                ),
            ) from exc

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
            detail=_make_auth_error_detail(
                error_code="INVALID_CREDENTIALS",
                message=str(err),
                request_id=request_id,
            ),
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Cấp mới Access Token từ Refresh Token",
)
async def refresh_access_token(
    request: Request,
    response: Response,
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Xác thực Refresh Token (7 ngày) và cấp mới Access Token (24 giờ)."""
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id

    token = payload.refresh_token.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_make_auth_error_detail(
                error_code="MISSING_REFRESH_TOKEN",
                message="Thiếu Refresh Token.",
                request_id=request_id,
            ),
        )

    decoded = auth_service.decode_token(token)
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_make_auth_error_detail(
                error_code="INVALID_REFRESH_TOKEN",
                message="Refresh Token không hợp lệ hoặc đã hết hạn.",
                request_id=request_id,
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decoded.get("sub")
    user = await auth_service.get_user_model_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_make_auth_error_detail(
                error_code="USER_NOT_FOUND",
                message="Tài khoản người dùng không còn tồn tại.",
                request_id=request_id,
            ),
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_make_auth_error_detail(
                error_code="USER_INACTIVE",
                message="Tài khoản người dùng đã bị vô hiệu hóa.",
                request_id=request_id,
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_response = UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_profile_completed=user.is_profile_completed,
        created_at=user.created_at.isoformat() if hasattr(user.created_at, "isoformat") else str(user.created_at),
    )

    new_access_token = auth_service.create_access_token(user.id)
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=token,
        token_type="bearer",
        user=user_response,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy thông tin tài khoản hiện tại",
)
async def get_me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Trả về thông tin chi tiết người dùng (bao gồm cờ is_profile_completed)."""
    return current_user


