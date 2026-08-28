"""
Unit tests for AI Clinical Pipeline & 4-Layer Rule Engine.
Verifies Clinical NER parsing and multi-layer interaction analysis.
"""

import pytest
from ai.pipelines.clinical_ner_parser import ClinicalNERParser
from ai.clinical_evaluator.rule_engine import ClinicalRuleEngine


def test_clinical_ner_strength_extraction():
    parser = ClinicalNERParser()
    
    assert parser.extract_strength("Augmentin 1000mg vien nen") == "1000mg"
    assert parser.extract_strength("Nexium 40 mg uong sang") == "40 mg"
    assert parser.extract_strength("Panadol Extra 500mg/65mg") == "500mg/65mg"
    assert parser.extract_strength("Aspirin 81mg pH8") == "81mg"


def test_clinical_ner_time_slots_extraction():
    parser = ClinicalNERParser()
    
    # Explicit slots
    slots1, times1, ext1 = parser.extract_time_slots("Uống Sáng 1 viên, Tối 1 viên sau ăn")
    assert ext1 is True
    assert "morning" in slots1
    assert "evening" in slots1
    assert "08:00" in times1.values()
    assert "21:00" in times1.values()

    # Frequency pattern
    slots2, _, ext2 = parser.extract_time_slots("Ngày uống 3 lần sau ăn")
    assert ext2 is True
    assert slots2 == ["morning", "noon", "evening"]

    # No explicit slot
    slots3, _, ext3 = parser.extract_time_slots("Bảo quản nơi khô ráo thoáng mát")
    assert ext3 is False
    assert slots3 == []


def test_clinical_ner_duration_extraction():
    parser = ClinicalNERParser()
    
    assert parser.extract_duration_days("Uống trong 7 ngày liên tục") == 7
    assert parser.extract_duration_days("Dùng x 5 ngày") == 5
    assert parser.extract_duration_days("Đợt điều trị 14 ngày") == 14


def test_clinical_rule_engine_layer1_duplication():
    engine = ClinicalRuleEngine()
    
    # 2 thuốc cùng chứa Paracetamol
    drugs = [
        {"drug_name": "Panadol Extra", "active_ingredient": "Paracetamol + Caffeine"},
        {"drug_name": "Hapacol 650", "active_ingredient": "Paracetamol"},
    ]
    
    result = engine.evaluate(drugs)
    assert result["total_drugs_analyzed"] == 2
    assert len(result["alerts"]) >= 1
    
    dup_alerts = [a for a in result["alerts"] if "Trùng lặp hoạt chất" in a["title"]]
    assert len(dup_alerts) == 1
    assert dup_alerts[0]["severity"] == "HIGH"


def test_clinical_rule_engine_layer2_drug_interaction():
    engine = ClinicalRuleEngine()
    
    # Aspirin + Ibuprofen
    drugs = [
        {"drug_name": "Aspirin 81mg", "active_ingredient": "Aspirin"},
        {"drug_name": "Ibuprofen 400mg", "active_ingredient": "Ibuprofen"},
    ]
    
    result = engine.evaluate(drugs)
    assert len(result["alerts"]) >= 1
    ddi_alerts = [a for a in result["alerts"] if "xuất huyết" in a["title"].lower() or "ibuprofen" in a["title"].lower()]
    assert len(ddi_alerts) >= 1
    assert ddi_alerts[0]["severity"] == "HIGH"


def test_clinical_rule_engine_layer3_contraindication():
    engine = ClinicalRuleEngine()
    
    drugs = [
        {"drug_name": "Ibuprofen 400mg", "active_ingredient": "Ibuprofen"},
    ]
    user_profile = {
        "conditions": ["Peptic Ulcer", "Hypertension"]
    }
    
    result = engine.evaluate(drugs, user_profile=user_profile)
    assert len(result["alerts"]) >= 1
    con_alerts = [a for a in result["alerts"] if "loét dạ dày" in a["title"].lower()]
    assert len(con_alerts) == 1
    assert con_alerts[0]["severity"] == "HIGH"


def test_clinical_rule_engine_layer4_dosage_check():
    engine = ClinicalRuleEngine()
    
    drugs = [
        {"drug_name": "Augmentin 1g", "strength": "1000mg", "max_daily_dose_mg": 3000},
    ]
    
    result = engine.evaluate(drugs)
    assert len(result["dosage_checks"]) == 1
    assert result["dosage_checks"][0]["is_appropriate"] is True
