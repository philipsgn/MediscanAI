"""
Auth Service — Xử lý Hashing Mật khẩu, JWT Encoding/Decoding, và Lưu trữ User vào PostgreSQL.
Tuân thủ PEP 8 & strict type hints.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.schemas.user_schema import UserLogin, UserRegister, UserResponse

logger = logging.getLogger(__name__)


class AuthService:
    def hash_password(self, password: str) -> str:
        """Băm mật khẩu bằng bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Xác minh mật khẩu thuần với chuỗi hash bcrypt."""
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            return False

    def create_access_token(self, user_id: str) -> str:
        """Tạo JWT Access Token (hết hạn sau ACCESS_TOKEN_EXPIRE_MINUTES)."""
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": user_id,
            "exp": int(expire.timestamp()),
            "type": "access",
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    def create_refresh_token(self, user_id: str) -> str:
        """Tạo JWT Refresh Token (hết hạn sau REFRESH_TOKEN_EXPIRE_DAYS)."""
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user_id,
            "exp": int(expire.timestamp()),
            "type": "refresh",
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Giải mã & xác minh chữ ký + thời gian của JWT Token."""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except (jwt.PyJWTError, ValueError):
            return None

    async def get_user_by_id(self, db: AsyncSession, user_id: str) -> Optional[UserResponse]:
        """Lấy thông tin người dùng theo ID từ Database."""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            return None
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_profile_completed=user.is_profile_completed,
            created_at=user.created_at.isoformat() if hasattr(user.created_at, "isoformat") else str(user.created_at),
        )

    async def register_user(self, db: AsyncSession, data: UserRegister) -> UserResponse:
        """Tạo tài khoản người dùng mới trong Database. Quăng ValueError nếu username/email đã tồn tại."""
        clean_email = data.email.strip().lower()
        clean_username = data.username.strip().lower()

        # Kiểm tra trùng email hoặc username
        stmt = select(User).where(
            or_(
                User.email.ilike(clean_email),
                User.username.ilike(clean_username),
            )
        )
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            if existing_user.email.lower() == clean_email:
                raise ValueError("Email này đã được sử dụng.")
            if existing_user.username.lower() == clean_username:
                raise ValueError("Tên đăng nhập này đã được sử dụng.")

        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        hashed_pwd = self.hash_password(data.password)

        new_user = User(
            id=user_id,
            email=data.email.strip(),
            username=data.username.strip(),
            full_name=data.full_name.strip() if data.full_name else None,
            hashed_password=hashed_pwd,
            is_active=True,
            is_profile_completed=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        return UserResponse(
            id=new_user.id,
            email=new_user.email,
            username=new_user.username,
            full_name=new_user.full_name,
            is_profile_completed=new_user.is_profile_completed,
            created_at=new_user.created_at.isoformat(),
        )

    async def authenticate_user(self, db: AsyncSession, data: UserLogin) -> UserResponse:
        """Xác thực người dùng qua Username hoặc Email + Password. Quăng ValueError nếu thất bại."""
        identifier = data.get_identifier().lower()

        stmt = select(User).where(
            or_(
                User.email.ilike(identifier),
                User.username.ilike(identifier),
            )
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not self.verify_password(data.password, user.hashed_password):
            raise ValueError("Tên đăng nhập hoặc mật khẩu không chính xác.")

        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_profile_completed=user.is_profile_completed,
            created_at=user.created_at.isoformat() if hasattr(user.created_at, "isoformat") else str(user.created_at),
        )


auth_service = AuthService()
