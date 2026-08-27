"""
Unit tests cho Authentication System (Stage 8).
Kiểm thử toàn bộ các endpoint register, login, me, token verification & error cases.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_auth_full_flow():
    # 1. Đăng ký tài khoản mới thành công
    uid = uuid.uuid4().hex[:6]
    username = f"user_{uid}"
    email = f"doc_{uid}@mediscan.ai"

    user_payload = {
        "email": email,
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
    assert data_reg["user"]["email"] == email
    assert data_reg["user"]["fullName"] == "Bác Sĩ Test"

    access_token = data_reg["accessToken"]

    # 2. Thử đăng ký lại email/username bị trùng -> 400 Bad Request
    resp_dup = client.post("/api/v1/auth/register", json=user_payload)
    assert resp_dup.status_code == 400

    # 3. Đăng nhập đúng bằng Username -> 200 OK
    login_payload_user = {
        "usernameOrEmail": username,
        "password": "SecurePassword123!",
    }
    resp_login1 = client.post("/api/v1/auth/login", json=login_payload_user)
    assert resp_login1.status_code == 200
    assert "accessToken" in resp_login1.json()

    # 4. Đăng nhập đúng bằng Email -> 200 OK
    login_payload_email = {
        "usernameOrEmail": email,
        "password": "SecurePassword123!",
    }
    resp_login2 = client.post("/api/v1/auth/login", json=login_payload_email)
    assert resp_login2.status_code == 200

    # 5. Đăng nhập sai Mật khẩu -> 401 Unauthorized
    login_wrong = {
        "usernameOrEmail": username,
        "password": "WrongPassword!",
    }
    resp_wrong = client.post("/api/v1/auth/login", json=login_wrong)
    assert resp_wrong.status_code == 401

    # 6. Truy cập GET /me với Token hợp lệ -> 200 OK
    headers = {"Authorization": f"Bearer {access_token}"}
    resp_me = client.get("/api/v1/auth/me", headers=headers)
    assert resp_me.status_code == 200
    assert resp_me.json()["username"] == username

    # 7. Truy cập GET /me không có Token / Token giả -> 401 Unauthorized
    resp_unauth = client.get("/api/v1/auth/me")
    assert resp_unauth.status_code == 401

    resp_bad = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token_xyz"})
    assert resp_bad.status_code == 401
