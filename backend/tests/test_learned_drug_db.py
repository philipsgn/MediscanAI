"""
Unit Tests for Stage 18: Enterprise Active Drug Knowledge Store & AI Telemetry.
Bao phủ:
1. Đồng bộ hóa CSDL & Tăng hit_count nguyên tử (Atomic Counter).
2. Vòng lặp Active Learning & Chống ngộ độc cache (Anti-Poisoning Verification).
3. Đo lường Telemetry (Cache Hit Ratio, Tokens Saved, ROI).
4. Kiểm thử REST API: POST /api/v1/drugs/verify-learned & GET /api/v1/metrics/ai-cache.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.learned_drug import LearnedDrugModel
from app.services.ai_telemetry_service import ai_telemetry_service
from app.services.drug_database import drug_database
from tests.conftest import TestingSessionLocal, test_engine
from app.db.base import Base


async def _ensure_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_learned_drug_db_sync_and_hit_increment():
    """Kiểm tra lưu thuốc tự học vào CSDL và tự động tăng hit_count khi tái sử dụng."""
    await _ensure_tables()
    brand = "Test Herb Collagen"
    drug_payload = {
        "brand_name": brand,
        "active_ingredient": "Collagen Type II / Glucosamine",
        "strength": "500mg",
        "category": "Thực phẩm bảo vệ sức khỏe - Khớp",
        "is_supplement": True,
        "confidence_score": 0.75,
        "verification_status": "PENDING_REVIEW",
        "notes": "Hỗ trợ tái tạo sụn khớp",
        "contraindications": ["Dị ứng hải sản"],
        "source": "ai_llm_inference",
    }

    async with TestingSessionLocal() as db_session:
        # 1. Đồng bộ lần đầu vào DB
        await drug_database.sync_learned_to_db(drug_payload, session=db_session)

        query = select(LearnedDrugModel).where(LearnedDrugModel.brand_name_normalized == brand.lower())
        res = await db_session.execute(query)
        row = res.scalar_one_or_none()
        assert row is not None
        assert row.active_ingredient == "Collagen Type II / Glucosamine"
        assert row.verification_status == "PENDING_REVIEW"
        assert row.hit_count == 1
        assert row.is_supplement is True

        # 2. Đồng bộ lần hai (khi người khác quét lại thuốc đó) -> hit_count tăng lên 2
        await drug_database.sync_learned_to_db(drug_payload, session=db_session)
        res2 = await db_session.execute(query)
        row2 = res2.scalar_one_or_none()
        assert row2 is not None
        assert row2.hit_count == 2


@pytest.mark.asyncio
async def test_active_learning_anti_poisoning_feedback():
    """
    Kiểm thử vòng lặp Active Learning & Anti-Poisoning:
    - Nếu người dùng xác nhận đúng -> VERIFIED.
    - Nếu AI phỏng đoán sai và người dùng sửa lại -> USER_CORRECTED + Cập nhật hoạt chất mới.
    """
    await _ensure_tables()
    brand = "NutraFlex Rare Formula"
    initial_payload = {
        "brand_name": brand,
        "active_ingredient": "Hoạt chất AI đoán sai",
        "strength": "200mg",
        "category": "Thực phẩm chức năng",
        "is_supplement": True,
        "confidence_score": 0.70,
        "verification_status": "PENDING_REVIEW",
    }
    async with TestingSessionLocal() as db_session:
        drug_database.save_learned_drug(initial_payload)
        await drug_database.sync_learned_to_db(initial_payload, session=db_session)

        # Người dùng phát hiện sai và sửa lại hoạt chất chuẩn
        confirmed_ingredient = "Curcumin Phospholipid / Piperine"
        updated = await drug_database.verify_and_update_learned_drug(
            brand_name=brand,
            confirmed_active_ingredient=confirmed_ingredient,
            strength="250mg",
            category="Hỗ trợ giảm đau khớp sinh học",
            is_supplement=True,
            user_notes="Bác sĩ xác nhận thành phần theo tem phụ",
            session=db_session,
        )

        # Khẳng định cơ chế Anti-Poisoning: Trạng thái chuyển thành USER_CORRECTED
        assert updated["verification_status"] == "USER_CORRECTED"
        assert updated["active_ingredient"] == confirmed_ingredient
        assert updated["verified_count"] >= 1

        # Kiểm tra trong CSDL
        query = select(LearnedDrugModel).where(LearnedDrugModel.brand_name_normalized == brand.lower())
        res = await db_session.execute(query)
        db_row = res.scalar_one_or_none()
        assert db_row is not None
        assert db_row.active_ingredient == confirmed_ingredient
        assert db_row.verification_status == "USER_CORRECTED"
        assert db_row.verified_count >= 1

    # Kiểm tra lần tra cứu tiếp theo trong RAM đã được sửa thành hoạt chất đúng
    cached_ram = drug_database.find_by_brand_exact(brand)
    assert cached_ram is not None
    assert cached_ram["active_ingredient"] == confirmed_ingredient


@pytest.mark.asyncio
async def test_ai_telemetry_service_metrics():
    """Kiểm tra dịch vụ Telemetry đo lường Tokens Saved, Cache Hit Ratio và ROI."""
    await _ensure_tables()
    # Giả lập 10 lần tra cứu (8 lần hit, 2 lần miss)
    for i in range(8):
        ai_telemetry_service.record_cache_hit(f"Drug_{i}")
    for j in range(2):
        ai_telemetry_service.record_cache_miss(f"Unknown_{j}")

    async with TestingSessionLocal() as db_session:
        metrics = await ai_telemetry_service.get_metrics(session=db_session)
        assert metrics["total_lookups"] >= 10
        assert metrics["cache_hits"] >= 8
        assert metrics["cache_misses"] >= 2
        assert metrics["cache_hit_ratio_percent"] >= 70.0
        assert metrics["estimated_tokens_saved_session"] >= 8 * 350
        assert metrics["estimated_cost_saved_usd"] > 0
        assert "storage_stats" in metrics
        assert "top_reused_drugs" in metrics


@pytest.mark.asyncio
async def test_api_endpoints_verify_and_metrics():
    """Kiểm thử API endpoints: POST /drugs/verify-learned và GET /metrics/ai-cache."""
    await _ensure_tables()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Test POST /api/v1/drugs/verify-learned
        verify_payload = {
            "brand_name": "Tendoactive API Test",
            "confirmed_active_ingredient": "Mucopolysaccharides / Collagen Type I / Vitamin C",
            "strength": "430mg",
            "category": "Thực phẩm bảo vệ sức khỏe",
            "is_supplement": True,
            "user_notes": "Xác nhận bởi Dược sĩ bệnh viện",
        }
        res_verify = await ac.post("/api/v1/drugs/verify-learned", json=verify_payload)
        assert res_verify.status_code == 200
        data = res_verify.json()
        assert data["success"] is True
        assert data["data"]["brand_name"] == "Tendoactive API Test"
        assert data["data"]["active_ingredient"] == verify_payload["confirmed_active_ingredient"]

        # 2. Test GET /api/v1/metrics/ai-cache
        res_metrics = await ac.get("/api/v1/metrics/ai-cache")
        assert res_metrics.status_code == 200
        metrics_data = res_metrics.json()
        assert "cache_hit_ratio_percent" in metrics_data
        assert "estimated_tokens_saved_all_time" in metrics_data
        assert "storage_stats" in metrics_data
        assert "top_reused_drugs" in metrics_data
