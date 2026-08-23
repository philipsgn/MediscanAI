"""[S4-Closeout/F4.3] Tests cho GET /api/v1/drugs/search — autocomplete endpoint.

Verify bằng DB thật (vietnam_drugs_db.json, 100 thuốc) — không mock data:
- camelCase wire-format khớp IDrugSearchResult frontend (AGENTS §3.A).
- Brand fuzzy + ingredient substring đều hoạt động.
- limit param override Settings default; query quá ngắn bị 422.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

EXPECTED_KEYS = {"drugId", "brandName", "activeIngredient", "strength"}


def test_search_by_brand_fuzzy_returns_suggestions():
    resp = client.get("/api/v1/drugs/search", params={"q": "panadol"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0, "DB thật 100 thuốc phải match được 'panadol'"
    for item in data:
        assert set(item.keys()) == EXPECTED_KEYS, f"wire-format sai: {item.keys()}"
    assert any("panadol" in item["brandName"].lower() for item in data)


def test_search_by_ingredient_substring():
    resp = client.get("/api/v1/drugs/search", params={"q": "paracetamol"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0, "Hoạt chất Paracetamol phải có trong DB thật"
    assert any(
        "paracetamol" in (item["activeIngredient"] or "").lower() for item in data
    )


def test_search_no_match_returns_empty_list():
    resp = client.get("/api/v1/drugs/search", params={"q": "zzzzkhongcotthuocnay"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_search_rejects_too_short_query():
    resp = client.get("/api/v1/drugs/search", params={"q": "p"})
    assert resp.status_code == 422


def test_search_limit_param_overrides_default():
    # 'par' fuzzy-match nhiều brand + ingredient substring → đủ lớn để cắt
    resp = client.get("/api/v1/drugs/search", params={"q": "par", "limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()) <= 2


def test_search_limit_bounds_enforced():
    # limit > 50 phải bị 422 (giới hạn cứng ở router, chống abuse)
    resp = client.get("/api/v1/drugs/search", params={"q": "par", "limit": 999})
    assert resp.status_code == 422
