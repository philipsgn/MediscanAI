"""
Unit Tests for OpenFDA Query Gating & Safety Protection (Option 1).

Kiểm tra:
1. Gating rule is_valid_openfda_substance_query:
   - "S-ALA" -> Blocked (len(alpha)=4 < 5, segment "S" len=1 <= 3)
   - "AB-CD" -> Blocked (len(alpha)=4 < 5, segments len=2 <= 3)
   - "Vitamin-C" -> Blocked (segment "C" len=1 <= 3)
   - "X-ray" -> Blocked (segment "X" len=1 <= 3, segment "ray" len=3 <= 3)
   - "T-P" -> Blocked
   - "Tretinoin" -> Allowed (len=9 >= 5, no short hyphen)
   - "Amoxicillin" -> Allowed (len=11 >= 5, no short hyphen)
   - "Pseudoephedrine-Triprolidine" -> Allowed (segments len=15 and 12 > 3)
2. End-to-end normalization of "S-ALA":
   - KHÔNG gọi OpenFDA substance query.
   - KHÔNG trả về hoạt chất ung thư Cabozantinib.
   - Giữ nguyên brand_name="S-ALA", active_ingredient=None, match_method=None.
"""

import pytest
from app.services.drug_database import drug_database
from app.services.normalization_service import normalization_service
from app.schemas import DrugItem


def test_openfda_substance_query_gating_rules():
    """Kiểm tra các test cases biên cho rule gating OpenFDA substance query."""
    # Các case BỊ CHẶN (Blocked)
    assert drug_database.is_valid_openfda_substance_query("S-ALA") is False
    assert drug_database.is_valid_openfda_substance_query("AB-CD") is False
    assert drug_database.is_valid_openfda_substance_query("Vitamin-C") is False
    assert drug_database.is_valid_openfda_substance_query("X-ray") is False
    assert drug_database.is_valid_openfda_substance_query("T-P") is False
    assert drug_database.is_valid_openfda_substance_query("ALA") is False
    assert drug_database.is_valid_openfda_substance_query("12345") is False
    assert drug_database.is_valid_openfda_substance_query("") is False
    assert drug_database.is_valid_openfda_substance_query(None) is False

    # Các case ĐƯỢC CHO PHÉP (Allowed)
    assert drug_database.is_valid_openfda_substance_query("Tretinoin") is True
    assert drug_database.is_valid_openfda_substance_query("Amoxicillin") is True
    assert drug_database.is_valid_openfda_substance_query("Paracetamol") is True
    assert drug_database.is_valid_openfda_substance_query("Methylprednisolone") is True
    assert drug_database.is_valid_openfda_substance_query("Pseudoephedrine-Triprolidine") is True


@pytest.mark.asyncio
async def test_s_ala_normalization_blocks_oncology_false_match():
    """Xác nhận token S-ALA không bị match nhầm sang hoạt chất ung thư Cabozantinib."""
    raw_item = DrugItem(
        brand_name="S-ALA",
        strength="",
        confidence_score=0.9,
    )
    normalized = await normalization_service.normalize_drug_item_full(raw_item)

    # Khẳng định an toàn y tế:
    assert normalized.match_method is None
    assert normalized.active_ingredient is None
    assert normalized.brand_name == "S-ALA"
    assert normalized.is_verified is False
    assert "CABOZANTINIB" not in str(normalized.active_ingredient or "").upper()


@pytest.mark.asyncio
async def test_tretinoin_normalization_passes_gating():
    """Xác nhận hoạt chất Tretinoin hợp lệ vẫn qua gating bình thường."""
    raw_item = DrugItem(
        brand_name="Tretinoin",
        strength="0.05%",
        confidence_score=0.9,
    )
    normalized = await normalization_service.normalize_drug_item_full(raw_item)
    assert normalized.brand_name == "Tretinoin"
    assert normalized.active_ingredient == "TRETINOIN"
    assert normalized.match_method in ("openfda", "openfda_ingredient")
    assert normalized.is_verified is False
