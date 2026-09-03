"""
Unit tests cho Authentication System (Stage 8/10).
Kiểm thử toàn bộ các endpoint register, login, me, token verification & unified 6-key error contract.
"""

import uuid
from typing import Set
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.limiter import limiter

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_limiter():
    """Reset storage limiter trước và sau mỗi test case."""
    limiter.reset()
    yield
    limiter.reset()

REQUIRED_ERROR_KEYS: Set[str] = {
    "error_code",
    "message",
    "service",
    "stage",
    "request_id",
    "retryable",
}


def test_auth_full_flow():
    # 1. Đăng ký tài khoản mới thành công
    uid = uuid.uuid4().hex[:6]
    username = f"user_{uid}"
    email = f"doc_{uid}@mediscan.ai"

    user_payload = {
        "email": f"  {email.upper()}  ",  # Test email trimming and lowercasing
        "username": username,
        "password": "SecurePassword123!",
        "fullName": "Bác Sĩ Test",
    }
    resp_reg = client.post("/api/v1/auth/register", json=user_payload)
    assert resp_reg.status_code == 201
    data_reg = resp_reg.json()
    assert "accessToken" in data_reg
    assert "refreshToken" in data_reg
    assert data_reg["user"]["username"] == username
    assert data_reg["user"]["email"] == email.lower()
    assert data_reg["user"]["fullName"] == "Bác Sĩ Test"

    access_token = data_reg["accessToken"]

    # 2. Thử đăng ký lại email/username bị trùng -> 409 Conflict với Unified 6-Key Error Contract
    resp_dup = client.post("/api/v1/auth/register", json=user_payload)
    assert resp_dup.status_code == 409
    err_dup = resp_dup.json()["detail"]
    assert REQUIRED_ERROR_KEYS.issubset(err_dup.keys())
    assert err_dup["error_code"] == "USER_ALREADY_EXISTS"
    assert err_dup["service"] == "auth"
    assert err_dup["stage"] == "authentication"
    assert err_dup["retryable"] is False

    # 3. Đăng nhập đúng bằng Username (dạng usernameOrEmail) -> 200 OK
    login_payload_user = {
        "usernameOrEmail": username,
        "password": "SecurePassword123!",
    }
    resp_login1 = client.post("/api/v1/auth/login", json=login_payload_user)
    assert resp_login1.status_code == 200
    assert "accessToken" in resp_login1.json()

    # 3.1. Đăng nhập đúng bằng Username (dạng JSON username) -> 200 OK
    login_payload_direct_user = {
        "username": username,
        "password": "SecurePassword123!",
    }
    resp_login_direct = client.post("/api/v1/auth/login", json=login_payload_direct_user)
    assert resp_login_direct.status_code == 200

    # 3.2. Đăng nhập bằng Form Data (OAuth2 standard) -> 200 OK
    resp_form = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": "SecurePassword123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp_form.status_code == 200

    # 4. Đăng nhập đúng bằng Email -> 200 OK
    login_payload_email = {
        "usernameOrEmail": email,
        "password": "SecurePassword123!",
    }
    resp_login2 = client.post("/api/v1/auth/login", json=login_payload_email)
    assert resp_login2.status_code == 200

    # 5. Đăng nhập sai Mật khẩu -> 401 Unauthorized với 6-Key Error Contract và message generic
    login_wrong = {
        "usernameOrEmail": username,
        "password": "WrongPassword!",
    }
    resp_wrong = client.post("/api/v1/auth/login", json=login_wrong)
    assert resp_wrong.status_code == 401
    err_wrong = resp_wrong.json()["detail"]
    assert REQUIRED_ERROR_KEYS.issubset(err_wrong.keys())
    assert err_wrong["error_code"] == "INVALID_CREDENTIALS"
    assert "không chính xác" in err_wrong["message"]

    # 6. Truy cập GET /me với Token hợp lệ -> 200 OK
    headers = {"Authorization": f"Bearer {access_token}"}
    resp_me = client.get("/api/v1/auth/me", headers=headers)
    assert resp_me.status_code == 200
    assert resp_me.json()["username"] == username

    # 7. Truy cập GET /me không có Token / Token giả -> 401 Unauthorized với 6-Key Error Contract
    resp_unauth = client.get("/api/v1/auth/me")
    assert resp_unauth.status_code == 401
    err_unauth = resp_unauth.json()["detail"]
    assert REQUIRED_ERROR_KEYS.issubset(err_unauth.keys())
    assert err_unauth["error_code"] == "UNAUTHORIZED"

    resp_bad = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token_xyz"})
    assert resp_bad.status_code == 401
    err_bad = resp_bad.json()["detail"]
    assert REQUIRED_ERROR_KEYS.issubset(err_bad.keys())
    assert err_bad["error_code"] == "INVALID_TOKEN"


def test_auth_account_enumeration_protection():
    """Kiểm thử đăng nhập tài khoản không tồn tại trả về đúng 401 và message generic giống sai password."""
    login_unknown = {
        "usernameOrEmail": f"non_existent_{uuid.uuid4().hex[:6]}@mediscan.ai",
        "password": "SomePassword123!",
    }
    resp_unknown = client.post("/api/v1/auth/login", json=login_unknown)
    assert resp_unknown.status_code == 401
    err_unknown = resp_unknown.json()["detail"]
    assert REQUIRED_ERROR_KEYS.issubset(err_unknown.keys())
    assert err_unknown["error_code"] == "INVALID_CREDENTIALS"
    assert err_unknown["message"] == "Tên đăng nhập hoặc mật khẩu không chính xác."


def test_auth_password_minimum_length():
    """Kiểm thử mật khẩu dưới 6 ký tự bị Pydantic validation reject (HTTP 422)."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"short_pwd_{uuid.uuid4().hex[:6]}@mediscan.ai",
            "username": f"short_{uuid.uuid4().hex[:6]}",
            "password": "123",
            "fullName": "Short Pwd",
        },
    )
    assert resp.status_code == 422

