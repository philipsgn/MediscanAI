"""
Unit Tests for Rate Limiting on Authentication Endpoints (Stage 8/10).
Kiểm thử:
1. Gọi POST /api/v1/auth/login quá 5 lần / phút -> Lần thứ 6 nhận HTTP 429 kèm header Retry-After & message tiếng Việt.
2. Xác nhận rate limit không ảnh hưởng nhầm sang các endpoint khác (/drugs/search, /evaluate...).
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.limiter import limiter


@pytest.fixture(autouse=True)
def reset_limiter():
    """Reset storage limiter trước mỗi test case."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.mark.asyncio
async def test_login_rate_limit_exceeded():
    """Gọi /auth/login sai mật khẩu 5 lần liên tiếp -> lần thứ 6 phải trả HTTP 429."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 5 lần đầu: nhận 401 UNAUTHORIZED (hoặc 400 nếu user không tồn tại)
        for i in range(5):
            res = await client.post(
                "/api/v1/auth/login",
                json={"username": f"brute_force_user_{i}", "password": "wrong_password"},
            )
            assert res.status_code in (400, 401, 404), f"Lần {i+1} trả về {res.status_code}"

        # Lần thứ 6: BẮT BUỘC trả về 429 Too Many Requests
        res_blocked = await client.post(
            "/api/v1/auth/login",
            json={"username": "brute_force_user_6", "password": "wrong_password"},
        )
        assert res_blocked.status_code == 429, f"Lần 6 phải trả 429, thực tế nhận: {res_blocked.status_code}"
        
        data = res_blocked.json()
        assert "Quá nhiều yêu cầu" in data.get("detail", "")
        assert data.get("error") == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in res_blocked.headers


@pytest.mark.asyncio
async def test_register_rate_limit_exceeded():
    """Gọi /auth/register 5 lần liên tiếp -> lần thứ 6 phải trả HTTP 429."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for i in range(5):
            await client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"test_rate_{i}@mediscan.ai",
                    "username": f"rate_user_{i}",
                    "password": "Password123!",
                    "full_name": f"User {i}",
                },
            )

        # Lần 6 bị chặn 429
        res_blocked = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test_rate_blocked@mediscan.ai",
                "username": "rate_user_blocked",
                "password": "Password123!",
                "full_name": "User Blocked",
            },
        )
        assert res_blocked.status_code == 429
        assert "Retry-After" in res_blocked.headers


@pytest.mark.asyncio
async def test_other_endpoints_not_affected_by_auth_rate_limit():
    """Xác nhận các endpoint công khai khác không bị chặn bởi auth rate limit."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Gọi search thuốc 8 lần liên tiếp (vượt quá 5) -> không bị 429
        for _ in range(8):
            res = await client.get("/api/v1/drugs/search?q=panadol")
            assert res.status_code == 200, f"Search drug không được bị 429, nhận: {res.status_code}"
