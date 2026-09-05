"""
Unit tests for Stage 16: Extended Master Drug Registry & Dual-Tier Architecture.
Validates ingestion of 11,000+ medicines, O(1) in-memory lookup performance,
and active ingredient mapping for common pain relief, stomach, and generic drugs.
"""

import time
import pytest

from app.schemas import DrugItem
from app.services.drug_database import drug_database
from app.services.normalization_service import NormalizationService


def test_dual_tier_database_loaded():
    """Kiểm tra cả 2 tầng CSDL nạp thành công vào bộ nhớ."""
    assert len(drug_database.local_db) >= 105, "Tier 1 Gold Standard phải có ít nhất 105 thuốc"
    assert len(drug_database.extended_db) >= 10000, "Tier 2 Extended Master phải có ít nhất 10,000 thuốc"
    assert len(drug_database.brand_to_drug) >= 105
    assert len(drug_database.extended_brand_to_drug) >= 10000


def test_pain_relief_generics_resolution():
    """Kiểm tra các thuốc giảm đau generic phổ biến tìm đúng hoạt chất gốc."""
    cases = [
        ("Aldigesic-SP", "Paracetamol"),
        ("Acemiz Plus", "Paracetamol"),
        ("Ace Proxyvon", "Paracetamol"),
        ("Panadol Extra", "Paracetamol"),
    ]
    for brand, expected_ing in cases:
        drug = drug_database.find_by_brand_exact(brand)
        assert drug is not None, f"Không tìm thấy {brand} trong Dual-Tier DB"
        assert expected_ing.lower() in drug.get("active_ingredient", "").lower(), (
            f"Thuốc {brand} kỳ vọng chứa {expected_ing}, nhưng nhận {drug.get('active_ingredient')}"
        )


def test_stomach_ppi_generics_resolution():
    """Kiểm tra các thuốc dạ dày / tiêu hóa generic tìm đúng hoạt chất gốc."""
    cases = [
        ("Aciloc 150", "Ranitidine"),
        ("Aciloc", "Ranitidine"),
        ("Losec 20mg", "Omeprazole"),
        ("Nexium 40mg", "Esomeprazole"),
    ]
    for brand, expected_ing in cases:
        drug = drug_database.find_by_brand_exact(brand)
        assert drug is not None, f"Không tìm thấy {brand} trong Dual-Tier DB"
        assert expected_ing.lower() in drug.get("active_ingredient", "").lower(), (
            f"Thuốc {brand} kỳ vọng chứa {expected_ing}, nhưng nhận {drug.get('active_ingredient')}"
        )


def test_dual_tier_lookup_speed_sla():
    """Kiểm tra tốc độ tra cứu O(1) đạt chuẩn SLA < 1ms/lượt tra cứu."""
    sample_queries = ["Panadol Extra", "Aciloc 150", "Aldigesic-SP", "Augmentin 625 Duo", "Nexium 20mg"]
    t0 = time.perf_counter()
    iterations = 2000
    for i in range(iterations):
        q = sample_queries[i % len(sample_queries)]
        _ = drug_database.find_by_brand_exact(q)
    elapsed = time.perf_counter() - t0
    avg_ms = (elapsed / iterations) * 1000
    print(f"Average lookup latency: {avg_ms:.4f} ms")
    assert avg_ms < 1.0, f"Độ trễ tra cứu {avg_ms:.4f}ms vượt quá SLA 1ms"


def test_normalization_service_extended_integration():
    """Kiểm tra NormalizationService tích hợp mượt mà với Tier 2, gán đúng active_ingredient."""
    norm = NormalizationService()
    raw_item = DrugItem(brand_name="Aciloc 150", confidence_score=0.9)
    res = norm.normalize_drug_item(raw_item)
    assert res.is_verified is True
    assert res.match_method == "exact"
    assert res.active_ingredient == "Ranitidine"
    assert res.category is not None
    assert "Dạ dày" in res.category or "Tiêu hóa" in res.category or "acid" in res.category.lower()


def test_search_drugs_autocomplete_dual_tier():
    """Kiểm tra API tìm kiếm autocomplete gợi ý cả thuốc Tier 1 và Tier 2."""
    results_aciloc = drug_database.search_drugs("aciloc", limit=5)
    assert len(results_aciloc) > 0
    assert any("Ranitidine" in (d.get("active_ingredient") or "") for d in results_aciloc)

    results_para = drug_database.search_drugs("paracetamol", limit=5)
    assert len(results_para) > 0
