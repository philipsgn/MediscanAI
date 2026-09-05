"""
Unit & Integration Tests for Unified Drug Identity Resolver (Stage 14 Baseline).
Kiểm thử toàn bộ các ràng buộc chất lượng và an toàn từ Senior Architect:
1. Traversal RxNorm TTY (BN -> IN / MIN) cho cả thuốc đơn chất và phối hợp.
2. Xử lý Multi-RxCUI resolution.
3. Disambiguation bằng Strength (giải quyết biến thể Augmentin).
4. Phát hiện mâu thuẫn CONFLICTING_EVIDENCE giữa các ảnh/nguồn.
5. Tách biệt tường minh SOURCE_UNAVAILABLE (lỗi mạng) khỏi UNRESOLVED (khuyết dữ liệu).
6. Multi-image evidence aggregation.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.identity_resolver import (
    UnifiedDrugIdentityResolver,
    DrugObservation,
    DrugObservationSet,
    EvidenceField,
    IdentityResolutionStatus,
    unified_identity_resolver,
)
from app.services.rxnorm_service import (
    rxnorm_service,
    NormalizationStatus,
    RxNormConcept,
    RxNormResolutionResult,
)


@pytest.mark.asyncio
async def test_rxnorm_brand_traversal_to_active_ingredient():
    """Kiểm tra RxNav Traversal API: Brand name Lipitor suy ra hoạt chất atorvastatin."""
    # Mocking RxNav API responses to ensure offline/CI reliability
    mock_allrelated = {
        "allRelatedGroup": {
            "conceptGroup": [
                {
                    "tty": "IN",
                    "conceptProperties": [
                        {"rxcui": "83367", "name": "atorvastatin"}
                    ]
                }
            ]
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_allrelated

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        ings = await rxnorm_service.get_related_ingredients("617314")
        assert len(ings) == 1
        assert ings[0].name == "atorvastatin"
        assert ings[0].tty == "IN"


@pytest.mark.asyncio
async def test_rxnorm_combination_drug_multi_ingredients():
    """Kiểm tra thuốc phối hợp (Augmentin): Traversal trả về đủ cả 2 hoạt chất Amoxicillin + Clavulanate."""
    mock_allrelated = {
        "allRelatedGroup": {
            "conceptGroup": [
                {
                    "tty": "IN",
                    "conceptProperties": [
                        {"rxcui": "723", "name": "amoxicillin"},
                        {"rxcui": "2599", "name": "clavulanate"}
                    ]
                }
            ]
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_allrelated

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        ings = await rxnorm_service.get_related_ingredients("153744")
        assert len(ings) == 2
        ing_names = [i.name for i in ings]
        assert "amoxicillin" in ing_names
        assert "clavulanate" in ing_names


@pytest.mark.asyncio
async def test_resolve_multi_rxcui():
    """Kiểm tra giải mã mảng Multi-RxCUI từ nhiều quy cách SBD về canonical ingredient chung."""
    mock_concept1 = RxNormConcept(rxcui="83367", name="atorvastatin", tty="IN")
    with patch.object(rxnorm_service, "get_related_ingredients", new_callable=AsyncMock) as mock_rel:
        mock_rel.return_value = [mock_concept1]
        unique_ings = await rxnorm_service.resolve_multi_rxcui(["259255", "262095", "617310"])
        assert unique_ings == ["atorvastatin"]


@pytest.mark.asyncio
async def test_disambiguation_by_strength():
    """Kiểm tra sử dụng Strength làm bằng chứng giải quyết biến thể (Augmentin 625mg vs 1g)."""
    obs = DrugObservation(
        observation_id="obs_1",
        observed_brand_name=EvidenceField(value="Augmentin", source_image="front", ocr_confidence=0.98),
        observed_strength=EvidenceField(value="625mg", source_image="front", ocr_confidence=0.95),
    )

    res = await unified_identity_resolver.resolve_observation(obs)
    assert res.status == IdentityResolutionStatus.RESOLVED
    assert res.resolved_identity is not None
    assert "Augmentin" in res.resolved_identity.canonical_brand_name
    assert "Amoxicillin" in res.resolved_identity.canonical_active_ingredient
    assert res.resolved_identity.canonical_strength == "625mg"


@pytest.mark.asyncio
async def test_conflicting_evidence_between_images():
    """Kiểm tra phát hiện CONFLICTING_EVIDENCE khi mặt trước và mặt sau mâu thuẫn hoạt chất."""
    # Mặt trước là Panadol (Paracetamol), nhưng mặt sau lại đọc được Ibuprofen
    obs = DrugObservation(
        observation_id="obs_conflict",
        observed_brand_name=EvidenceField(value="Panadol", source_image="front", ocr_confidence=0.98),
        observed_active_ingredient=EvidenceField(value="Ibuprofen", source_image="back", ocr_confidence=0.95),
    )

    res = await unified_identity_resolver.resolve_observation(obs)
    assert res.status == IdentityResolutionStatus.CONFLICTING_EVIDENCE
    assert res.conflict_reason is not None
    assert "Mâu thuẫn bằng chứng" in res.conflict_reason
    assert res.resolved_identity is None  # Bị chặn, không cho tự ý resolve


@pytest.mark.asyncio
async def test_distinguish_source_unavailable_from_unresolved():
    """Kiểm tra phân biệt rành mạch lỗi mạng (SOURCE_UNAVAILABLE) và khuyết thiếu dữ liệu (UNRESOLVED)."""
    # Case 1: Thuốc không tồn tại trong bất kỳ nguồn nào -> UNRESOLVED
    obs_nonexistent = DrugObservation(
        observation_id="obs_fake",
        observed_brand_name=EvidenceField(value="NonExistentDrugXYZ999", source_image="front", ocr_confidence=0.90),
    )
    res1 = await unified_identity_resolver.resolve_observation(obs_nonexistent)
    assert res1.status == IdentityResolutionStatus.UNRESOLVED

    # Case 2: Lỗi mạng timeout -> SOURCE_UNAVAILABLE
    with patch.object(rxnorm_service, "resolve_drug", new_callable=AsyncMock) as mock_rx:
        mock_rx.return_value = RxNormResolutionResult(
            status=NormalizationStatus.SOURCE_UNAVAILABLE,
            query_term="NetworkErrorDrug",
            error_message="Lỗi kết nối tới dịch vụ RxNav: ConnectTimeout",
        )
        obs_net = DrugObservation(
            observation_id="obs_net",
            observed_brand_name=EvidenceField(value="NetworkErrorDrug", source_image="front", ocr_confidence=0.90),
        )
        res2 = await unified_identity_resolver.resolve_observation(obs_net)
        assert res2.status == IdentityResolutionStatus.SOURCE_UNAVAILABLE
        assert "Không thể kết nối" in (res2.error_message or "")


@pytest.mark.asyncio
async def test_multi_image_observation_set_aggregation():
    """Kiểm tra xử lý danh sách quan sát đa ảnh không bị merge chuỗi ngây thơ."""
    obs_set = DrugObservationSet(
        session_id="sess_123",
        source_stream="packaging",
        observations=[
            DrugObservation(
                observation_id="obs_a",
                observed_brand_name=EvidenceField(value="Lipitor", source_image="front", ocr_confidence=0.99),
            ),
            DrugObservation(
                observation_id="obs_b",
                observed_brand_name=EvidenceField(value="Smecta", source_image="front", ocr_confidence=0.97),
            )
        ]
    )

    results = await unified_identity_resolver.aggregate_and_resolve(obs_set)
    assert len(results) == 2
    assert results[0].status in (IdentityResolutionStatus.RESOLVED, IdentityResolutionStatus.SOURCE_UNAVAILABLE)
    assert results[1].status == IdentityResolutionStatus.RESOLVED
    assert results[1].resolved_identity.canonical_brand_name == "Smecta 3g"
