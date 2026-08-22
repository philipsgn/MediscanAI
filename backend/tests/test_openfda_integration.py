"""[Audit-S3 / P2 / F3.4] Integration tests luồng Local-miss → OpenFDA tier-4.

Mock ở tầng httpx.AsyncClient.get (KHÔNG gọi mạng thật) — xác nhận:
1. Sau khi xóa gate API key, fetcher OpenFDA chạy được ở chế độ keyless
   (đã xác minh thực nghiệm OpenFDA 200 keyless trong remediation P2).
2. Local DB miss toàn bộ 3 tầng → get_drug_full_info rơi xuống OpenFDA.
3. DrugItem được populate từ OpenFDA: match_method="openfda",
   is_verified=False (bắt buộc HITL), confidence trần 0.6.
"""

from typing import Any

import httpx
import pytest

from app.schemas import DrugItem
from app.services import drug_database as db_mod
from app.services.drug_database import drug_database
from app.services.normalization_service import NormalizationService

pytestmark = pytest.mark.asyncio

_FDA_RESPONSE = {
    "results": [
        {
            "openfda": {
                "brand_name": ["TESTAMOL"],
                "generic_name": ["ACETAMINOPHEN"],
                "substance_name": ["ACETAMINOPHEN"],
                "strength": ["500 mg/1"],
                "route": ["ORAL"],
                "dosage_form": ["TABLET"],
                "spl_id": ["abc-123"],
            },
            "warnings": ["Keep out of reach of children"],
            "id": "abc-123",
        }
    ]
}


class _FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return _FDA_RESPONSE


@pytest.fixture
def patch_openfda_http(monkeypatch):
    """Chặn mọi GET ra api.fda.gov, trả response giả lập."""

    async def fake_get(self, url, **kwargs):  # type: ignore[no-untyped-def]
        assert "api.fda.gov" in url
        return _FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)


@pytest.fixture(autouse=True)
def force_keyless(monkeypatch):
    """Kịch bản keyless: gate API key đã xóa, fetcher vẫn phải chạy."""
    monkeypatch.setattr(db_mod.settings, "OPENFDA_API_KEY", "")


async def test_openfda_works_keyless_after_gate_removal(patch_openfda_http):
    info = await drug_database.fetch_openfda_by_brand("Totally Unknown Brand XZ")
    assert info is not None
    assert info["source"] == "openfda"
    assert info["brand_name"] == "TESTAMOL"
    assert info["active_ingredient"] == ["ACETAMINOPHEN"]


async def test_full_info_falls_through_to_openfda_when_local_misses(patch_openfda_http):
    info = await drug_database.get_drug_full_info("Totally Unknown Brand XZ")
    assert info is not None
    assert str(info["source"]).startswith("openfda")


async def test_normalization_tier4_populates_drug_item(patch_openfda_http):
    raw = DrugItem(
        brand_name="Totally Unknown Brand XZ",
        strength="",
        confidence_score=0.7,
    )
    normalized = await NormalizationService().normalize_drug_item_full(raw)
    assert normalized.match_method == "openfda"
    assert normalized.active_ingredient == "ACETAMINOPHEN"
    assert normalized.brand_name == "TESTAMOL"
    assert normalized.strength == "500 mg/1"
    assert normalized.drug_id == "openfda:abc-123"
    assert normalized.warnings == ["Keep out of reach of children"]
    assert normalized.is_verified is False  # HITL bắt buộc với nguồn ngoài
    assert normalized.confidence_score <= 0.6  # trần nguồn ngoài


async def test_local_match_skips_openfda_call(patch_openfda_http, monkeypatch):
    """Local match (exact hoặc fuzzy) phải chặn trước OpenFDA — không network call."""
    called = {"count": 0}

    async def fail_get(self, url, **kwargs):  # type: ignore[no-untyped-def]
        called["count"] += 1
        return _FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", fail_get)
    raw = DrugItem(brand_name="Panadol", strength="", confidence_score=0.9)
    normalized = await NormalizationService().normalize_drug_item_full(raw)
    # DB VN có "Panadol Extra" chứ không có "Panadol" thuần → kỳ vọng fuzzy là hợp lý
    assert normalized.match_method in ("exact", "fuzzy")
    assert normalized.active_ingredient is not None
    assert "Paracetamol" in normalized.active_ingredient
    assert called["count"] == 0  # bất biến cốt lõi: local match ⇒ không gọi OpenFDA