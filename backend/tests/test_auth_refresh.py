"""
Unit Tests for /auth/refresh Endpoint (Stage 8/10).
Kiểm thử:
1. Gửi refresh_token hợp lệ -> Trả về access_token mới (200 OK) và dùng access_token mới gọi /auth/me thành công.
2. Gửi refresh_token giả mạo / hết hạn -> Nhận 401 UNAUTHORIZED.
3. Gửi access_token nhầm vào endpoint refresh -> Bị từ chối 401 UNAUTHORIZED (chỉ chấp nhận token type="refresh").
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_refresh_token_success():
    """Kiểm thử cấp mới Access Token thành công bằng Refresh Token hợp lệ."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Đăng ký tài khoản
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "refresh_user_test@mediscan.ai",
                "username": "refresh_user",
                "password": "Password123!",
                "full_name": "Refresh User Test",
            },
        )
        assert reg_res.status_code == 201
        reg_data = reg_res.json()
        refresh_token = reg_data["refreshToken"]
        old_access_token = reg_data["accessToken"]
        assert refresh_token is not None

        # 2. Gọi POST /api/v1/auth/refresh
        refresh_res = await client.post(
            "/api/v1/auth/refresh",
            json={"refreshToken": refresh_token},
        )
        assert refresh_res.status_code == 200
        refresh_data = refresh_res.json()
        new_access_token = refresh_data["accessToken"]
        assert new_access_token is not None
        assert refresh_data["user"]["username"] == "refresh_user"

        # 3. Dùng new_access_token gọi /auth/me
        me_res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert me_res.status_code == 200
        assert me_res.json()["email"] == "refresh_user_test@mediscan.ai"


@pytest.mark.asyncio
async def test_refresh_token_invalid():
    """Gửi refresh token không hợp lệ -> nhận 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/refresh",
            json={"refreshToken": "invalid.jwt.token.here"},
        )
        assert res.status_code == 401
        assert "Refresh Token không hợp lệ" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_refresh_token_rejects_access_token():
    """Gửi access token vào endpoint refresh -> bị từ chối 401 vì sai loại token (type != 'refresh')."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Đăng ký lấy access_token
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "access_reject_user@mediscan.ai",
                "username": "reject_user",
                "password": "Password123!",
                "full_name": "Reject User",
            },
        )
        assert reg_res.status_code == 201
        access_token = reg_res.json()["accessToken"]

        # 2. Cố tình gửi access_token vào /auth/refresh
        res = await client.post(
            "/api/v1/auth/refresh",
            json={"refreshToken": access_token},
        )
        assert res.status_code == 401
        assert "Refresh Token không hợp lệ" in res.json().get("detail", "")
