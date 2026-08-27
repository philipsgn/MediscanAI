"""
Auth Service — Xử lý Hashing Mật khẩu, JWT Encoding/Decoding, và Lưu trữ User.
Tuân thủ PEP 8 & strict type hints.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

import bcrypt
import jwt
from app.core.config import settings
from app.schemas.user_schema import UserLogin, UserRegister, UserResponse

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"


class AuthService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._users: Dict[str, Dict[str, Any]] = {}
        self._load_users()

    def _load_users(self) -> None:
        """Đọc danh sách users từ file JSON (nếu tồn tại)."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if USERS_FILE.exists():
            try:
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    self._users = json.load(f)
            except Exception as exc:
                logger.warning("Không thể đọc users.json, khởi tạo bộ nhớ trống: %s", exc)
                self._users = {}

    def _save_users(self) -> None:
        """Ghi danh sách users vào file JSON thread-safe."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._users, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error("Lỗi khi ghi users.json: %s", exc)

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

    def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Lấy thông tin người dùng theo ID."""
        with self._lock:
            user_data = self._users.get(user_id)
            if not user_data:
                return None
            return UserResponse(
                id=user_data["id"],
                email=user_data["email"],
                username=user_data["username"],
                full_name=user_data.get("full_name"),
                created_at=user_data["created_at"],
            )

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Tra cứu user thô theo Email (case-insensitive)."""
        clean_email = email.strip().lower()
        with self._lock:
            for u in self._users.values():
                if u["email"].lower() == clean_email:
                    return u
            return None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Tra cứu user thô theo Username (case-insensitive)."""
        clean_name = username.strip().lower()
        with self._lock:
            for u in self._users.values():
                if u["username"].lower() == clean_name:
                    return u
            return None

    def register_user(self, data: UserRegister) -> UserResponse:
        """Tạo tài khoản người dùng mới. Quăng ValueError nếu username/email đã tồn tại."""
        clean_email = data.email.strip().lower()
        clean_username = data.username.strip().lower()

        with self._lock:
            for u in self._users.values():
                if u["email"].lower() == clean_email:
                    raise ValueError("Email này đã được sử dụng.")
                if u["username"].lower() == clean_username:
                    raise ValueError("Tên đăng nhập này đã được sử dụng.")

            user_id = f"usr_{uuid.uuid4().hex[:12]}"
            hashed_pwd = self.hash_password(data.password)
            created_at = datetime.now(timezone.utc).isoformat()

            user_record = {
                "id": user_id,
                "email": data.email.strip(),
                "username": data.username.strip(),
                "full_name": data.full_name.strip() if data.full_name else None,
                "hashed_password": hashed_pwd,
                "created_at": created_at,
            }

            self._users[user_id] = user_record
            self._save_users()

            return UserResponse(
                id=user_id,
                email=user_record["email"],
                username=user_record["username"],
                full_name=user_record["full_name"],
                created_at=user_record["created_at"],
            )

    def authenticate_user(self, data: UserLogin) -> UserResponse:
        """Xác thực người dùng qua Username hoặc Email + Password. Quăng ValueError nếu thất bại."""
        identifier = data.username_or_email.strip().lower()
        matched_user: Optional[Dict[str, Any]] = None

        with self._lock:
            for u in self._users.values():
                if u["email"].lower() == identifier or u["username"].lower() == identifier:
                    matched_user = u
                    break

        if not matched_user:
            raise ValueError("Tên đăng nhập hoặc mật khẩu không chính xác.")

        if not self.verify_password(data.password, matched_user["hashed_password"]):
            raise ValueError("Tên đăng nhập hoặc mật khẩu không chính xác.")

        return UserResponse(
            id=matched_user["id"],
            email=matched_user["email"],
            username=matched_user["username"],
            full_name=matched_user.get("full_name"),
            created_at=matched_user["created_at"],
        )


auth_service = AuthService()
