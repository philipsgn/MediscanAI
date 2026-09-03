"""
Unit & Security Integration tests cho Medication History, Cabinet & Smart Reminders System (Stage 10).
Kiểm thử chi tiết:
1. Auto-create History nội bộ sau khi POST /evaluate thành công cho authenticated user
2. Phân trang (Pagination) và bộ lọc Severity trên GET /history/me
3. Lấy chi tiết lịch sử (GET /history/{id}) và xóa lịch sử (DELETE /history/{id})
4. Quản lý Tủ thuốc (Cabinet /medications CRUD) và IDOR isolation
5. Liên kết Reminder với Medication và chặn IDOR cross-user linking
6. Validation định dạng giờ HH:MM và log taken/skipped với tính toán tỉ lệ tuân thủ
7. Cascade delete khi xóa thuốc khỏi Tủ thuốc
8. Rejection unauthenticated & disabled users trên toàn bộ endpoints
9. Unified 6-Key Error Contract trên các lỗi 404
"""

import uuid
from typing import Set
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.limiter import limiter
from app.db.session import get_db
from app.main import app
from app.models.user import User

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


def test_evaluate_auto_creates_history_for_authenticated_user():
    """Kiểm thử: Khi authenticated user gọi POST /evaluate, hệ thống tự động lưu Lịch sử (Internal Write)."""
    uid = uuid.uuid4().hex[:6]
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"eval_hist_{uid}@mediscan.ai",
            "username": f"user_eval_{uid}",
            "password": "SecurePassword123!",
        },
    )
    assert reg_resp.status_code == 201
    token = reg_resp.json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Kiểm tra ban đầu history rỗng
    init_hist = client.get("/api/v1/history/me", headers=headers)
    assert init_hist.status_code == 200
    assert init_hist.json()["total"] == 0
    assert init_hist.json()["items"] == []

    # 2. Gọi POST /evaluate với Bearer Token
    eval_payload = {
        "drugs": [
            {"brandName": "Paracetamol 500mg", "activeIngredient": "Paracetamol", "strength": "500mg"},
            {"brandName": "Panadol Extra", "activeIngredient": "Paracetamol", "strength": "500mg"},
        ],
        "userProfile": {"age": 30, "conditions": [], "allergies": []},
    }
    eval_resp = client.post("/api/v1/evaluate", json=eval_payload, headers=headers)
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["totalDrugsAnalyzed"] == 2

    # 3. Lấy lại history qua GET /history/me -> Đã được tự động lưu!
    after_hist = client.get("/api/v1/history/me", headers=headers)
    assert after_hist.status_code == 200
    data = after_hist.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert "Paracetamol 500mg" in item["drugNames"]
    assert "Panadol Extra" in item["drugNames"]
    assert item["sourceType"] == "manual"
    assert item["highestSeverity"] in {"HIGH", "MEDIUM", "LOW", "NONE"}


def test_history_pagination_and_severity_filtering():
    """Kiểm thử: Phân trang và lọc theo severity trên GET /history/me."""
    uid = uuid.uuid4().hex[:6]
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"page_hist_{uid}@mediscan.ai",
            "username": f"user_page_{uid}",
            "password": "SecurePassword123!",
        },
    )
    token = reg_resp.json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    # Tạo 3 lần evaluate
    for i in range(3):
        client.post(
            "/api/v1/evaluate",
            json={
                "drugs": [{"brandName": f"Thuoc_{i}", "activeIngredient": f"HoatChat_{i}", "strength": "100mg"}],
                "userProfile": {"age": 30},
            },
            headers=headers,
        )

    # Test limit=2, offset=0
    p1 = client.get("/api/v1/history/me?limit=2&offset=0", headers=headers)
    assert p1.status_code == 200
    res1 = p1.json()
    assert res1["total"] == 3
    assert len(res1["items"]) == 2
    assert res1["hasMore"] is True

    # Test limit=2, offset=2
    p2 = client.get("/api/v1/history/me?limit=2&offset=2", headers=headers)
    assert p2.status_code == 200
    res2 = p2.json()
    assert res2["total"] == 3
    assert len(res2["items"]) == 1
    assert res2["hasMore"] is False


def test_history_get_detail_and_delete():
    """Kiểm thử: Lấy chi tiết snapshot (GET /history/{id}) và Xóa (DELETE /history/{id})."""
    uid = uuid.uuid4().hex[:6]
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"detail_hist_{uid}@mediscan.ai",
            "username": f"user_detail_{uid}",
            "password": "SecurePassword123!",
        },
    )
    token = reg_resp.json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/v1/evaluate",
        json={
            "drugs": [{"brandName": "Aspirin 100mg", "activeIngredient": "Aspirin", "strength": "100mg"}],
            "userProfile": {"age": 40},
        },
        headers=headers,
    )

    hist_list = client.get("/api/v1/history/me", headers=headers).json()
    hist_id = hist_list["items"][0]["id"]

    # 1. Lấy chi tiết -> 200 OK
    detail_res = client.get(f"/api/v1/history/{hist_id}", headers=headers)
    assert detail_res.status_code == 200
    d_data = detail_res.json()
    assert d_data["id"] == hist_id
    assert "rawPayload" in d_data
    # Đảm bảo KHÔNG có trường ảnh
    assert "image_bytes" not in d_data["rawPayload"]
    assert "base64" not in d_data["rawPayload"]

    # 2. Xóa lịch sử -> 200 OK
    del_res = client.delete(f"/api/v1/history/{hist_id}", headers=headers)
    assert del_res.status_code == 200

    # 3. Lấy lại -> 404 HISTORY_NOT_FOUND (6-key error contract)
    get_again = client.get(f"/api/v1/history/{hist_id}", headers=headers)
    assert get_again.status_code == 404
    err = get_again.json()["detail"]
    assert REQUIRED_ERROR_KEYS.issubset(err.keys())
    assert err["error_code"] == "HISTORY_NOT_FOUND"


def test_cabinet_medications_crud_and_isolation():
    """Kiểm thử: Quản lý Tủ thuốc (/medications) và cách ly dữ liệu giữa User A và User B."""
    # User A
    uid_a = uuid.uuid4().hex[:6]
    resp_a = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"med_a_{uid_a}@mediscan.ai",
            "username": f"user_med_a_{uid_a}",
            "password": "PasswordA123!",
        },
    )
    token_a = resp_a.json()["accessToken"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User B
    uid_b = uuid.uuid4().hex[:6]
    resp_b = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"med_b_{uid_b}@mediscan.ai",
            "username": f"user_med_b_{uid_b}",
            "password": "PasswordB123!",
        },
    )
    token_b = resp_b.json()["accessToken"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A thêm thuốc vào Cabinet
    med_payload = {
        "brandName": "Glucophage 500mg",
        "activeIngredient": "Metformin",
        "strength": "500mg",
        "dosageInstruction": "1 viên sau ăn sáng",
        "durationDays": 30,
        "isActive": True,
    }
    create_res = client.post("/api/v1/medications", json=med_payload, headers=headers_a)
    assert create_res.status_code == 201
    med_a_id = create_res.json()["id"]

    # User A lấy danh sách -> có thuốc
    get_a = client.get("/api/v1/medications/me", headers=headers_a)
    assert get_a.status_code == 200
    assert get_a.json()["total"] == 1
    assert get_a.json()["items"][0]["brandName"] == "Glucophage 500mg"

    # User B lấy danh sách -> Tủ thuốc rỗng!
    get_b = client.get("/api/v1/medications/me", headers=headers_b)
    assert get_b.status_code == 200
    assert get_b.json()["total"] == 0

    # User B cố tình sửa/xem/xóa thuốc của User A -> 404 MEDICATION_NOT_FOUND
    b_view = client.get(f"/api/v1/medications/{med_a_id}", headers=headers_b)
    assert b_view.status_code == 404
    assert b_view.json()["detail"]["error_code"] == "MEDICATION_NOT_FOUND"

    b_del = client.delete(f"/api/v1/medications/{med_a_id}", headers=headers_b)
    assert b_del.status_code == 404
    assert b_del.json()["detail"]["error_code"] == "MEDICATION_NOT_FOUND"


def test_reminder_creation_with_medication_linking_and_idor_protection():
    """Kiểm thử: Tạo Reminder gắn medication_id; chặn cross-user medication linking."""
    # User A
    uid_a = uuid.uuid4().hex[:6]
    resp_a = client.post(
        "/api/v1/auth/register",
        json={"email": f"rem_a_{uid_a}@mediscan.ai", "username": f"user_rem_a_{uid_a}", "password": "PasswordA123!"},
    )
    token_a = resp_a.json()["accessToken"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User B
    uid_b = uuid.uuid4().hex[:6]
    resp_b = client.post(
        "/api/v1/auth/register",
        json={"email": f"rem_b_{uid_b}@mediscan.ai", "username": f"user_rem_b_{uid_b}", "password": "PasswordB123!"},
    )
    token_b = resp_b.json()["accessToken"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A tạo thuốc
    med_res = client.post(
        "/api/v1/medications",
        json={"brandName": "Amlodipine 5mg", "activeIngredient": "Amlodipine"},
        headers=headers_a,
    )
    med_a_id = med_res.json()["id"]

    # 1. User A tạo Reminder liên kết đúng thuốc của mình -> 201 Created
    rem_res = client.post(
        "/api/v1/reminders",
        json={
            "medicationId": med_a_id,
            "drugName": "Amlodipine 5mg",
            "dosageInstruction": "1 viên buổi sáng",
            "timeOfDay": "morning",
            "reminderTime": "07:30",
            "isActive": True,
        },
        headers=headers_a,
    )
    assert rem_res.status_code == 201
    rem_id = rem_res.json()["id"]
    assert rem_res.json()["medicationId"] == med_a_id

    # 2. User B cố tình liên kết Reminder của mình với thuốc của User A -> 404 MEDICATION_NOT_FOUND
    rem_b_res = client.post(
        "/api/v1/reminders",
        json={
            "medicationId": med_a_id,
            "drugName": "Amlodipine 5mg",
            "timeOfDay": "morning",
            "reminderTime": "08:00",
        },
        headers=headers_b,
    )
    assert rem_b_res.status_code == 404
    assert rem_b_res.json()["detail"]["error_code"] == "MEDICATION_NOT_FOUND"

    # 3. User B cố tình cập nhật/xóa/log reminder của User A -> 404 REMINDER_NOT_FOUND
    b_put = client.put(f"/api/v1/reminders/{rem_id}", json={"isActive": False}, headers=headers_b)
    assert b_put.status_code == 404
    assert b_put.json()["detail"]["error_code"] == "REMINDER_NOT_FOUND"

    b_log = client.post(f"/api/v1/reminders/{rem_id}/log", json={"status": "taken"}, headers=headers_b)
    assert b_log.status_code == 404
    assert b_log.json()["detail"]["error_code"] == "REMINDER_NOT_FOUND"


def test_reminder_time_validation_and_adherence_calculation():
    """Kiểm thử: Validation định dạng giờ HH:MM và tính toán Adherence Rate."""
    uid = uuid.uuid4().hex[:6]
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": f"time_rem_{uid}@mediscan.ai", "username": f"user_time_{uid}", "password": "Password123!"},
    )
    token = reg_resp.json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Giờ không hợp lệ: "25:00", "08:60", "abc" -> 422
    assert client.post("/api/v1/reminders", json={"drugName": "T1", "timeOfDay": "morning", "reminderTime": "25:00"}, headers=headers).status_code == 422
    assert client.post("/api/v1/reminders", json={"drugName": "T1", "timeOfDay": "morning", "reminderTime": "08:60"}, headers=headers).status_code == 422
    assert client.post("/api/v1/reminders", json={"drugName": "T1", "timeOfDay": "morning", "reminderTime": "abc"}, headers=headers).status_code == 422

    # 2. Tạo 4 nhắc nhở hợp lệ cho 4 cữ trong ngày
    rem_ids = []
    slots = [("morning", "08:00"), ("noon", "12:00"), ("afternoon", "17:00"), ("evening", "20:00")]
    for slot, rtime in slots:
        r = client.post(
            "/api/v1/reminders",
            json={"drugName": f"Vitamin {slot}", "timeOfDay": slot, "reminderTime": rtime},
            headers=headers,
        )
        assert r.status_code == 201
        rem_ids.append(r.json()["id"])

    # 3. Log 3 cữ 'taken', 1 cữ 'skipped' -> Adherence rate = 3/4 = 75.0%
    for rem_id in rem_ids[:3]:
        client.post(f"/api/v1/reminders/{rem_id}/log", json={"status": "taken"}, headers=headers)
        # Bấm lại cùng ngày -> chỉ cập nhật, không tăng số lần
        client.post(f"/api/v1/reminders/{rem_id}/log", json={"status": "taken"}, headers=headers)

    client.post(f"/api/v1/reminders/{rem_ids[3]}/log", json={"status": "skipped"}, headers=headers)

    overview = client.get("/api/v1/reminders/me", headers=headers).json()
    assert overview["stats"]["takenCount"] == 3
    assert overview["stats"]["skippedCount"] == 1
    assert overview["stats"]["adherenceRate"] == 75.0
    assert overview["stats"]["todayTakenCount"] == 3
    assert overview["stats"]["todaySkippedCount"] == 1
    assert overview["stats"]["todayTotalScheduled"] == 4
    assert overview["stats"]["todayAdherenceRate"] == 75.0


def test_medication_deletion_cascades_reminders():
    """Kiểm thử: Xóa thuốc trong Cabinet tự động xóa các reminders liên kết."""
    uid = uuid.uuid4().hex[:6]
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": f"casc_{uid}@mediscan.ai", "username": f"user_casc_{uid}", "password": "Password123!"},
    )
    token = reg_resp.json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    # Tạo thuốc & reminder
    med_id = client.post("/api/v1/medications", json={"brandName": "Thuoc Tam"}, headers=headers).json()["id"]
    rem_id = client.post("/api/v1/reminders", json={"medicationId": med_id, "drugName": "Thuoc Tam", "timeOfDay": "morning", "reminderTime": "08:00"}, headers=headers).json()["id"]

    # Xóa thuốc
    del_res = client.delete(f"/api/v1/medications/{med_id}", headers=headers)
    assert del_res.status_code == 200

    # Lấy danh sách reminders -> không còn
    rems = client.get("/api/v1/reminders/me", headers=headers).json()
    assert len(rems["items"]) == 0


@pytest.mark.asyncio
async def test_unauthenticated_and_disabled_user_rejected():
    """Kiểm thử: Unauthenticated và Disabled user bị từ chối trên toàn bộ endpoints Stage 10."""
    # Unauthenticated
    assert client.get("/api/v1/history/me").status_code == 401
    assert client.get("/api/v1/reminders/me").status_code == 401
    assert client.get("/api/v1/medications/me").status_code == 401

    # Disabled User
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        uid = uuid.uuid4().hex[:6]
        reg_resp = await async_client.post(
            "/api/v1/auth/register",
            json={"email": f"inact_{uid}@mediscan.ai", "username": f"inact_{uid}", "password": "Password123!"},
        )
        token = reg_resp.json()["accessToken"]
        user_id = reg_resp.json()["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Vô hiệu hóa
        db_gen = app.dependency_overrides[get_db]
        async for session in db_gen():
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            u = result.scalar_one()
            u.is_active = False
            await session.commit()
            break

        res_h = await async_client.get("/api/v1/history/me", headers=headers)
        assert res_h.status_code == 401
        assert res_h.json()["detail"]["error_code"] == "USER_INACTIVE"

        res_r = await async_client.get("/api/v1/reminders/me", headers=headers)
        assert res_r.status_code == 401
        assert res_r.json()["detail"]["error_code"] == "USER_INACTIVE"

        res_m = await async_client.get("/api/v1/medications/me", headers=headers)
        assert res_m.status_code == 401
        assert res_m.json()["detail"]["error_code"] == "USER_INACTIVE"
