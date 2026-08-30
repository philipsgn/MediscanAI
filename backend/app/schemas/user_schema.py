"""
Pydantic Schemas cho Authentication System (Stage 8/10).
Đồng bộ 100% Data Contract với Frontend TypeScript Interfaces (frontend/src/types/auth.ts).
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Tên đăng nhập (chữ và số)")
    email: EmailStr = Field(..., description="Email người dùng")
    password: str = Field(..., min_length=6, description="Mật khẩu (ít nhất 6 ký tự)")
    full_name: Optional[str] = Field(None, description="Họ và tên người dùng")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel, extra="ignore")


class UserLogin(BaseModel):
    username: Optional[str] = Field(None, description="Tên đăng nhập hoặc Email")
    username_or_email: Optional[str] = Field(None, alias="usernameOrEmail", description="Tên đăng nhập hoặc Email")
    password: str = Field(..., description="Mật khẩu")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel, extra="ignore")

    def get_identifier(self) -> str:
        ident = (self.username or self.username_or_email or "").strip()
        if not ident:
            raise ValueError("Vui lòng nhập tên đăng nhập hoặc email.")
        return ident


class UserResponse(BaseModel):
    id: str = Field(..., description="ID định danh người dùng")
    email: str = Field(..., description="Email người dùng")
    username: str = Field(..., description="Tên đăng nhập")
    full_name: Optional[str] = Field(None, description="Họ và tên người dùng")
    is_profile_completed: bool = Field(False, description="Đã hoàn thành hồ sơ y tế /onboarding")
    created_at: str = Field(..., description="Thời gian tạo tài khoản (ISO 8601 string)")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel, extra="ignore")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Access Token (24h)")
    refresh_token: str = Field(..., description="JWT Refresh Token (7d)")
    token_type: str = Field("bearer", description="Loại token")
    user: UserResponse = Field(..., description="Thông tin chi tiết người dùng")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel, extra="ignore")


class TokenPayload(BaseModel):
    sub: str = Field(..., description="Subject - User ID")
    exp: int = Field(..., description="Thời gian hết hạn (Unix timestamp)")
    type: str = Field("access", description="Loại token ('access' | 'refresh')")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="JWT Refresh Token để xin cấp Access Token mới")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel, extra="ignore")

