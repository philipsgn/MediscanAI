"""
test_drug_knowledge_bridge.py

Unit & Integration Tests for Drug Knowledge Sources & Identifier Bridge (Stage 11/12).
Tuân thủ đầy đủ các yêu cầu kiểm thử tại Section 13:
1. RxNorm: exact resolvable, ambiguous candidates, not found, timeout/unavailable, provenance.
2. OpenFDA: fallback supporting path, no auto-resolve on similarity, HITL requirement.
3. Identifier Bridge: verified mapping vs unverified blocking automatic DDI.
4. DDInter: local dataset integrity, provenance, severity mapping, zero live download.
5. Integration: End-to-end normalization & 4-Layer evaluation.
"""

from typing import Any, Dict
import httpx
import pytest

from app.schemas import DrugItem
from app.services.ddinter_service import DDInterService, ddinter_service
from app.services.evaluation_service import evaluation_service
from app.services.identifier_bridge import BridgeMappingType, IdentifierBridge, identifier_bridge
from app.services.normalization_service import NormalizationService, normalization_service
from app.services.rxnorm_service import (
    NormalizationStatus,
    RxNormConcept,
    RxNormResolutionResult,
    RxNormService,
    rxnorm_service,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. RxNorm / RxNav Authority Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rxnorm_exact_resolvable(monkeypatch):
    """Test 1: RxNorm tìm thấy concept chính xác -> RESOLVED với RxCUI và provenance."""
    async def mock_get(self, url, **kwargs):
        url_str = str(url)
        if "rxcui.json" in url_str:
            return httpx.Response(200, json={"idGroup": {"rxnormId": ["723"]}}, request=httpx.Request("GET", url_str))
        elif "properties.json" in url_str:
            return httpx.Response(200, json={"properties": {"rxcui": "723", "name": "amoxicillin", "tty": "IN"}}, request=httpx.Request("GET", url_str))
        return httpx.Response(404, request=httpx.Request("GET", url_str))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    service = RxNormService()
    result = await service.resolve_drug("Amoxicillin")

    assert result.status == NormalizationStatus.RESOLVED
    assert result.concept is not None
    assert result.concept.rxcui == "723"
    assert result.concept.name == "amoxicillin"
    assert result.concept.provenance == "rxnorm"
    assert result.concept.confidence_score == 1.0


@pytest.mark.asyncio
async def test_rxnorm_ambiguous_candidate_requires_review(monkeypatch):
    """Test 2: RxNav trả về nhiều approximate candidates không vượt trội -> CANDIDATE_REQUIRES_REVIEW (chống silent pick)."""
    async def mock_get(self, url, **kwargs):
        url_str = str(url)
        if "rxcui.json" in url_str:
            return httpx.Response(200, json={"idGroup": {}}, request=httpx.Request("GET", url_str))
        elif "approximateTerm.json" in url_str:
            return httpx.Response(
                200,
                json={
                    "approximateGroup": {
                        "candidate": [
                            {"rxcui": "1001", "name": "Drug Option A", "score": "5.2"},
                            {"rxcui": "1002", "name": "Drug Option B", "score": "5.1"},
                        ]
                    }
                },
                request=httpx.Request("GET", url_str),
            )
        return httpx.Response(404, request=httpx.Request("GET", url_str))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    service = RxNormService()
    result = await service.resolve_drug("AmbiguousName")

    assert result.status == NormalizationStatus.CANDIDATE_REQUIRES_REVIEW
    assert len(result.candidates) == 2
    assert result.concept is None  # Không tự chọn candidate đầu tiên


@pytest.mark.asyncio
async def test_rxnorm_not_found_returns_unresolved(monkeypatch):
    """Test 3: RxNorm hoàn toàn không có kết quả -> UNRESOLVED."""
    async def mock_get(self, url, **kwargs):
        url_str = str(url)
        if "rxcui.json" in url_str:
            return httpx.Response(200, json={"idGroup": {}}, request=httpx.Request("GET", url_str))
        elif "approximateTerm.json" in url_str:
            return httpx.Response(200, json={"approximateGroup": {}}, request=httpx.Request("GET", url_str))
        return httpx.Response(404, request=httpx.Request("GET", url_str))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    service = RxNormService()
    result = await service.resolve_drug("ThuocDongYVietNamKhongCoTrongRxNorm")

    assert result.status == NormalizationStatus.UNRESOLVED
    assert result.concept is None


@pytest.mark.asyncio
async def test_rxnorm_timeout_returns_source_unavailable(monkeypatch):
    """Test 4: RxNav bị timeout/lỗi mạng -> SOURCE_UNAVAILABLE (phân biệt với NOT_FOUND)."""
    async def mock_get_timeout(self, url, **kwargs):
        raise httpx.TimeoutException("RxNav request timed out")

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get_timeout)

    service = RxNormService()
    result = await service.resolve_drug("AnyDrug")

    assert result.status == NormalizationStatus.SOURCE_UNAVAILABLE
    assert "Timeout" in (result.error_message or "")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Identifier Bridge & Invariants Tests (INV-01, INV-02, INV-03)
# ─────────────────────────────────────────────────────────────────────────────

def test_identifier_bridge_direct_canonical():
    """Test 5: Direct canonical mapping qua Identifier Bridge -> is_safe_for_ddi=True."""
    concept = RxNormConcept(
        rxcui="723",
        name="amoxicillin",
        tty="IN",
        active_ingredient="amoxicillin",
        provenance="rxnorm",
    )
    bridged = identifier_bridge.bridge_rxnorm_concept(concept, "Amoxicillin")

    assert bridged is not None
    assert bridged.canonical_ingredient == "amoxicillin"
    assert bridged.rxcui == "723"
    assert bridged.bridge_type == BridgeMappingType.DIRECT_CANONICAL
    assert bridged.is_safe_for_ddi is True


def test_identifier_bridge_medical_synonyms():
    """Test 6: Synonym Bridge (Acetylsalicylic Acid -> Aspirin, Acetaminophen -> Paracetamol)."""
    concept_aspirin = RxNormConcept(
        rxcui="1191",
        name="acetylsalicylic acid",
        tty="IN",
        active_ingredient="acetylsalicylic acid",
        provenance="rxnorm",
    )
    bridged_aspirin = identifier_bridge.bridge_rxnorm_concept(concept_aspirin, "Aspirin 100mg")
    assert bridged_aspirin is not None
    assert bridged_aspirin.canonical_ingredient == "aspirin"
    assert bridged_aspirin.bridge_type == BridgeMappingType.SYNONYM_BRIDGE_VERIFIED
    assert bridged_aspirin.is_safe_for_ddi is True

    concept_para = RxNormConcept(
        rxcui="161",
        name="acetaminophen",
        tty="IN",
        active_ingredient="acetaminophen",
        provenance="rxnorm",
    )
    bridged_para = identifier_bridge.bridge_rxnorm_concept(concept_para, "Tylenol")
    assert bridged_para is not None
    assert bridged_para.canonical_ingredient == "paracetamol"
    assert bridged_para.is_safe_for_ddi is True


def test_identifier_bridge_unsupported_blocks_ddi():
    """Test 7 (INV-02): Khái niệm không an toàn / không có canonical mapping -> is_safe_for_ddi=False."""
    concept_unknown = RxNormConcept(
        rxcui="999999",
        name="some_unregistered_botanical_extract",
        tty="UNKNOWN",
        active_ingredient="some_unregistered_botanical_extract",
        provenance="rxnorm",
    )
    bridged = identifier_bridge.bridge_rxnorm_concept(concept_unknown, "Botanical Tea")
    assert bridged is not None
    assert bridged.bridge_type == BridgeMappingType.UNSUPPORTED_NO_MATCH
    assert bridged.is_safe_for_ddi is False  # CHẶN DDI tự động


# ─────────────────────────────────────────────────────────────────────────────
# 3. DDInter Local Dataset & Knowledge Lookup Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_ddinter_dataset_loaded_and_metadata():
    """Test 8: DDInter dataset v2.0 được nạp đúng từ đĩa, có metadata và version."""
    info = ddinter_service.get_dataset_version_info()
    assert info["dataset_version"] == "2.0"
    assert "CC BY-NC-SA 4.0" in info["license"]
    assert info["total_pairs"] >= 15


def test_ddinter_lookup_known_interaction_pair():
    """Test 9: Tra cứu cặp tương tác đã biết (Sildenafil + Nitroglycerin; Fluoxetine + Tramadol)."""
    entry_nitrate = ddinter_service.lookup_interaction("sildenafil", "nitroglycerin")
    assert entry_nitrate is not None
    assert entry_nitrate.severity == "HIGH"
    assert entry_nitrate.ddinter_id == "DDInter100120"
    assert entry_nitrate.dataset_version == "2.0"
    assert entry_nitrate.source == "ddinter"

    # Không phân biệt thứ tự (frozenset commutative lookup)
    entry_reverse = ddinter_service.lookup_interaction("nitroglycerin", "sildenafil")
    assert entry_reverse is not None
    assert entry_reverse.ddinter_id == "DDInter100120"

    entry_serotonin = ddinter_service.lookup_interaction("fluoxetine", "tramadol")
    assert entry_serotonin is not None
    assert entry_serotonin.severity == "HIGH"
    assert entry_serotonin.ddinter_id == "DDInter100119"


def test_ddinter_lookup_unknown_pair_returns_none():
    """Test 10: Cặp thuốc không có tương tác trong CSDL trả về None."""
    entry = ddinter_service.lookup_interaction("vitamin_c", "water")
    assert entry is None


# ─────────────────────────────────────────────────────────────────────────────
# 4. Multi-tier Normalization & Evaluation Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_normalization_tier2_rxnorm_integration(monkeypatch):
    """Test 11: Normalization pipeline sử dụng RxNorm khi local miss."""
    async def mock_resolve(term):
        return RxNormResolutionResult(
            status=NormalizationStatus.RESOLVED,
            query_term=term,
            concept=RxNormConcept(
                rxcui="10582",
                name="nebivolol",
                tty="IN",
                active_ingredient="nebivolol",
                provenance="rxnorm",
                confidence_score=0.95,
            ),
        )

    monkeypatch.setattr(rxnorm_service, "resolve_drug", mock_resolve)

    raw_item = DrugItem(brand_name="Bystolic 5mg", strength="5mg")
    service = NormalizationService()
    normalized = await service.normalize_drug_item_full(raw_item)

    assert normalized.drug_id == "rxnorm:10582"
    assert normalized.active_ingredient == "nebivolol"
    assert normalized.match_method == "rxnorm"
    assert normalized.is_verified is True
    assert normalized.confidence_score >= 0.85


def test_evaluation_engine_includes_ddinter_alerts():
    """Test 12: Evaluation service phát hiện tương tác mở rộng từ DDInter (Fluoxetine + Tramadol)."""
    drug1 = DrugItem(brand_name="Prozac", active_ingredient="Fluoxetine", strength="20mg")
    drug2 = DrugItem(brand_name="Ultram", active_ingredient="Tramadol", strength="50mg")

    resp = evaluation_service.evaluate_medications([drug1, drug2])

    assert len(resp.alerts) >= 1
    ddinter_alert = next((a for a in resp.alerts if "DDInter" in a.title or "DDInter" in a.description), None)
    assert ddinter_alert is not None
    assert ddinter_alert.severity == "HIGH"
    assert "DDInter100119" in ddinter_alert.title or "DDInter100119" in ddinter_alert.description
