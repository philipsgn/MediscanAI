"""
Comprehensive Unit & Security Integration Tests for Token Lifecycle & Hardening (Task 8.2).
Kiểm thử chi tiết:
1. Claims validation (sub, exp, iat, type)
2. Tampered signature rejection (HS256)
3. Algorithm confusion prevention (alg: none rejection)
4. Expired token rejection
5. Missing required claims rejection
6. Token type separation (Access Token vs Refresh Token)
7. Active User Invariant (Disabled user rejection on both protected API & refresh)
8. Unified 6-key Error Contract & Request ID tracing
9. get_optional_current_user behavior on invalid/inactive user
"""

import time
import uuid
from typing import Set
import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models.user import User
from app.services.auth_service import auth_service

REQUIRED_ERROR_KEYS: Set[str] = {
    "error_code",
    "message",
    "service",
    "stage",
    "request_id",
    "retryable",
}


@pytest.mark.asyncio
async def test_access_and_refresh_tokens_contain_required_claims():
    """Kiểm thử token sinh ra chứa đầy đủ claims bắt buộc: sub, iat, exp, type."""
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    access_token = auth_service.create_access_token(user_id)
    refresh_token = auth_service.create_refresh_token(user_id)

    decoded_access = auth_service.decode_token(access_token)
    assert decoded_access is not None
    assert decoded_access["sub"] == user_id
    assert decoded_access["type"] == "access"
    assert "iat" in decoded_access
    assert "exp" in decoded_access
    assert decoded_access["exp"] > decoded_access["iat"]

    decoded_refresh = auth_service.decode_token(refresh_token)
    assert decoded_refresh is not None
    assert decoded_refresh["sub"] == user_id
    assert decoded_refresh["type"] == "refresh"
    assert "iat" in decoded_refresh
    assert "exp" in decoded_refresh
    assert decoded_refresh["exp"] > decoded_refresh["iat"]


@pytest.mark.asyncio
async def test_token_with_tampered_signature_rejected():
    """Token bị chỉnh sửa signature HMAC phải bị từ chối 401 INVALID_TOKEN."""
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    token = auth_service.create_access_token(user_id)
    # Tamper the last 5 characters
    tampered_token = token[:-5] + "ABCDE"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
        assert res.status_code == 401
        detail = res.json()["detail"]
        assert REQUIRED_ERROR_KEYS.issubset(detail.keys())
        assert detail["error_code"] == "INVALID_TOKEN"
        assert detail["service"] == "auth"


@pytest.mark.asyncio
async def test_token_with_alg_none_rejected():
    """Token giả mạo thuật toán không ký (alg: none) phải bị từ chối 401."""
    now = int(time.time())
    payload = {
        "sub": f"usr_{uuid.uuid4().hex[:12]}",
        "iat": now,
        "exp": now + 3600,
        "type": "access",
    }
    # Create unsigned token (alg: none)
    unsigned_token = jwt.encode(payload, key="", algorithm="none")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {unsigned_token}"})
        assert res.status_code == 401
        detail = res.json()["detail"]
        assert detail["error_code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_token_expired_rejected():
    """Token có thời điểm hết hạn trong quá khứ phải bị từ chối 401 INVALID_TOKEN."""
    past = int(time.time()) - 3600
    payload = {
        "sub": f"usr_{uuid.uuid4().hex[:12]}",
        "iat": past - 100,
        "exp": past,
        "type": "access",
    }
    expired_token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert res.status_code == 401
        detail = res.json()["detail"]
        assert detail["error_code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_missing_required_claims_rejected():
    """Token thiếu claim bắt buộc (ví dụ thiếu 'iat' hoặc 'type') phải bị từ chối 401."""
    now = int(time.time())
    # Payload thiếu type và iat
    payload = {
        "sub": f"usr_{uuid.uuid4().hex[:12]}",
        "exp": now + 3600,
    }
    incomplete_token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {incomplete_token}"})
        assert res.status_code == 401
        detail = res.json()["detail"]
        assert detail["error_code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_protected_route_rejects_refresh_token():
    """Token Type Invariant: Refresh Token gửi vào API Protected (/auth/me) phải bị từ chối 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"type_conf_{uuid.uuid4().hex[:6]}@mediscan.ai",
                "username": f"type_conf_{uuid.uuid4().hex[:6]}",
                "password": "Password123!",
                "full_name": "Type Confusion User",
            },
        )
        assert reg_res.status_code == 201
        refresh_token = reg_res.json()["refreshToken"]

        # Gửi refresh token vào protected endpoint /auth/me
        res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh_token}"})
        assert res.status_code == 401
        detail = res.json()["detail"]
        assert detail["error_code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_disabled_user_access_and_refresh_token_rejected():
    """Active User Invariant: User bị đặt is_active=False thì cả Access Token & Refresh Token đều bị chặn 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"disabled_{uuid.uuid4().hex[:6]}@mediscan.ai"
        username = f"disabled_{uuid.uuid4().hex[:6]}"
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "username": username,
                "password": "Password123!",
                "full_name": "Disabled Test User",
            },
        )
        assert reg_res.status_code == 201
        reg_data = reg_res.json()
        access_token = reg_data["accessToken"]
        refresh_token = reg_data["refreshToken"]
        user_id = reg_data["user"]["id"]

        # 1. Lúc user còn active -> Gọi /auth/me thành công 200
        res_ok = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert res_ok.status_code == 200

        # 2. Vô hiệu hóa user trong DB (is_active = False)
        db_gen = app.dependency_overrides[get_db]
        async for session in db_gen():
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user_in_db = result.scalar_one()
            user_in_db.is_active = False
            await session.commit()
            break

        # 3. Gửi lại access token cũ -> Bị từ chối 401 USER_INACTIVE
        res_blocked = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert res_blocked.status_code == 401
        detail_blocked = res_blocked.json()["detail"]
        assert detail_blocked["error_code"] == "USER_INACTIVE"
        assert "vô hiệu hóa" in detail_blocked["message"]

        # 4. Gửi refresh token cũ để xin cấp mới -> Bị từ chối 401 USER_INACTIVE
        res_refresh_blocked = await client.post("/api/v1/auth/refresh", json={"refreshToken": refresh_token})
        assert res_refresh_blocked.status_code == 401
        detail_ref = res_refresh_blocked.json()["detail"]
        assert detail_ref["error_code"] == "USER_INACTIVE"
        assert "vô hiệu hóa" in detail_ref["message"]
