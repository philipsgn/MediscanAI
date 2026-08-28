"""
Unit tests for Fuzzy String Matching & Medical Typo Normalization.
Verifies correction of noisy OCR strings against standard pharmaceutical terms.
"""

import pytest
from ai.normalization.fuzzy_matcher import (
    FuzzyMatcher,
    clean_ocr_typos,
    normalize_vietnamese_text,
    levenshtein_distance,
    similarity_ratio,
)
from ai.normalization.drug_mapper import DrugMapper


def test_clean_ocr_typos():
    assert clean_ocr_typos("P4nadol") == "Panadol"
    assert clean_ocr_typos("Augmentln") == "Augmentin"
    assert clean_ocr_typos("Amoxlcillln") == "Amoxicillin"
    assert clean_ocr_typos("Gluc0phage") == "Glucophage"


def test_similarity_ratio():
    assert similarity_ratio("Panadol Extra", "Panadol Extra") == 1.0
    assert similarity_ratio("P4nadol Extra", "Panadol Extra") >= 0.85
    assert similarity_ratio("Augmentln 19", "Augmentin 1g") >= 0.75
    assert similarity_ratio("Nexlum 40", "Nexium 40mg") >= 0.70


def test_fuzzy_matcher_lookup():
    matcher = FuzzyMatcher(default_threshold=0.70)
    sample_db = [
        {
            "id": "DRUG_001",
            "brand_name": "Panadol Extra",
            "aliases": ["Panadol", "Panadol Do", "P4nadol"],
            "active_ingredient": "Paracetamol + Caffeine"
        },
        {
            "id": "DRUG_005",
            "brand_name": "Augmentin 1g",
            "aliases": ["Augmentin", "Augmentine", "Agumentin"],
            "active_ingredient": "Amoxicillin + Clavulanic Acid"
        }
    ]

    # Test exact match
    drug, score, mtype = matcher.find_best_drug_match("Panadol Extra", sample_db)
    assert drug is not None
    assert drug["brand_name"] == "Panadol Extra"
    assert score == 1.0

    # Test noisy OCR string match
    drug_noisy, score_noisy, _ = matcher.find_best_drug_match("P4nadol Extr4", sample_db)
    assert drug_noisy is not None
    assert drug_noisy["brand_name"] == "Panadol Extra"
    assert score_noisy >= 0.75

    # Test Augmentin typo
    drug_aug, score_aug, _ = matcher.find_best_drug_match("Augmentln 19", sample_db)
    assert drug_aug is not None
    assert drug_aug["brand_name"] == "Augmentin 1g"


def test_drug_mapper_resolution():
    mapper = DrugMapper()
    
    # Test real dictionary resolution
    res_panadol = mapper.map_raw_text("Panadol Extra 500mg/65mg")
    assert res_panadol["matched"] is True
    assert "Paracetamol" in res_panadol["active_ingredient"]

    res_nexium = mapper.map_raw_text("Nexlum 40mg")
    assert res_nexium["matched"] is True
    assert res_nexium["active_ingredient"] == "Esomeprazole"

    res_unknown = mapper.map_raw_text("Thuoc Khong Co That 12345")
    assert res_unknown["matched"] is False
    assert res_unknown["match_method"] == "raw_fallback"
