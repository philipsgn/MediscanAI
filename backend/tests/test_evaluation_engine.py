"""
Unit & Integration Tests - Stage 5 (Task 5.2)
Kiểm thử toàn diện Engine Đánh Giá Tương Tác 3 Lớp với 20+ kịch bản đơn thuốc thực tế.
Bao phủ: Overdose/Trùng lặp hoạt chất, Drug-Drug Interaction, Drug-Condition Conflict,
chuẩn hóa Fuzzy Match và các trường hợp biên (edge cases).
"""
import pytest
from app.schemas import DrugItem, UserProfile
from app.services.evaluation_service import EvaluationService
from app.services.normalization_service import normalization_service


@pytest.fixture
def svc() -> EvaluationService:
    return EvaluationService()


# ─────────────────────────────────────────────────────────────────────────────
# HELPER - Tạo DrugItem nhanh
# ─────────────────────────────────────────────────────────────────────────────

def make_drug(
    brand: str,
    ingredient: str,
    strength: str = "500mg",
    dosage: str = "Uống 1 viên/lần x 2 lần/ngày",
    confidence: float = 0.95,
    verified: bool = True,
) -> DrugItem:
    return DrugItem(
        brand_name=brand,
        active_ingredient=ingredient,
        strength=strength,
        dosage_instruction=dosage,
        confidence_score=confidence,
        is_verified=verified,
    )


def high_alerts(result):
    return [a for a in result.alerts if a.severity == "HIGH"]


def medium_alerts(result):
    return [a for a in result.alerts if a.severity == "MEDIUM"]


# ═════════════════════════════════════════════════════════════════════════════
# LAYER 1: TRÙNG LẶP & QUÁ LIỀU HOẠT CHẤT (Overdose)
# ═════════════════════════════════════════════════════════════════════════════

def test_overdose_paracetamol_dual_product(svc: EvaluationService):
    """Panadol 500mg x2viên x3lần + Efferalgan 500mg x2viên x2lần = 5000mg > 4000mg."""
    drugs = [
        make_drug("Panadol Extra", "Paracetamol", "500mg", "Uống 2 viên/lần x 3 lần/ngày"),
        make_drug("Efferalgan 500mg", "Paracetamol", "500mg", "Uống 2 viên/lần x 2 lần/ngày"),
    ]
    result = svc.evaluate_medications(drugs)
    assert any(a.severity == "HIGH" and "quá liều" in a.title.lower() for a in result.alerts)


def test_single_drug_within_safe_dose(svc: EvaluationService):
    """1 loại Paracetamol đúng liều -> không có cảnh báo quá liều."""
    drugs = [make_drug("Panadol", "Paracetamol", "500mg", "Uống 1 viên/lần x 3 lần/ngày")]
    result = svc.evaluate_medications(drugs)
    assert not any("quá liều" in a.title.lower() for a in result.alerts)


def test_single_drug_over_max_daily_dose(svc: EvaluationService):
    """Paracetamol dùng 5000mg/ngày (vượt 4000mg) -> HIGH alert."""
    drugs = [make_drug("Panadol", "Paracetamol", "500mg", "Uống 2 viên/lần x 5 lần/ngày")]
    result = svc.evaluate_medications(drugs)
    assert any(a.severity == "HIGH" and "quá liều" in a.title.lower() for a in result.alerts)


def test_duplicate_ingredient_within_dose_is_medium(svc: EvaluationService):
    """2 sản phẩm cùng hoạt chất nhưng trong ngưỡng an toàn -> MEDIUM (trùng lặp)."""
    drugs = [
        make_drug("Panadol", "Paracetamol", "500mg", "Uống 1 viên/lần x 2 lần/ngày"),
        make_drug("Hapacol", "Paracetamol", "500mg", "Uống 1 viên/lần x 1 lần/ngày"),
    ]
    result = svc.evaluate_medications(drugs)
    medium = medium_alerts(result)
    assert any("trùng lặp" in a.title.lower() for a in medium)
    assert not any("quá liều" in a.title.lower() for a in medium)


def test_combined_ingredient_split_for_overdose(svc: EvaluationService):
    """Hoạt chất kép 'Paracetamol / Caffeine' được tách để tính tổng Paracetamol."""
    drugs = [
        make_drug("Panadol Extra", "Paracetamol / Caffeine", "500mg / 65mg", "Uống 2 viên/lần x 3 lần/ngày"),
        make_drug("Efferalgan", "Paracetamol", "500mg", "Uống 2 viên/lần x 2 lần/ngày"),
    ]
    result = svc.evaluate_medications(drugs)
    assert any("paracetamol" in a.title.lower() for a in high_alerts(result))


# ═════════════════════════════════════════════════════════════════════════════
# LAYER 2: TƯƠNG TÁC THUỐC - THUỐC (Drug-Drug)
# ═════════════════════════════════════════════════════════════════════════════

def test_aspirin_ibuprofen_high(svc: EvaluationService):
    drugs = [make_drug("Aspirin", "Aspirin", "100mg"), make_drug("Ibuprofen 400", "Ibuprofen", "400mg")]
    result = svc.evaluate_medications(drugs)
    assert any(a.severity == "HIGH" and "aspirin" in a.title.lower() for a in result.alerts)


def test_aspirin_naproxen_high(svc: EvaluationService):
    drugs = [make_drug("Aspirin Cardio", "Aspirin", "100mg"), make_drug("Naproxen", "Naproxen", "250mg")]
    result = svc.evaluate_medications(drugs)
    assert any(a.severity == "HIGH" for a in result.alerts)


def test_warfarin_aspirin_high(svc: EvaluationService):
    drugs = [make_drug("Sintrom", "Warfarin", "4mg"), make_drug("Aspirin Cardio", "Aspirin", "100mg")]
    result = svc.evaluate_medications(drugs)
    assert any(a.severity == "HIGH" and "warfarin" in a.title.lower() for a in result.alerts)


def test_warfarin_ibuprofen_high(svc: EvaluationService):
    drugs = [make_drug("Sintrom", "Warfarin", "4mg"), make_drug("Brufen", "Ibuprofen", "400mg")]
    result = svc.evaluate_medications(drugs)
    assert any(a.severity == "HIGH" and "warfarin" in a.title.lower() for a in result.alerts)


def test_warfarin_paracetamol_medium(svc: EvaluationService):
    drugs = [make_drug("Sintrom", "Warfarin", "4mg", "1 viên/ngày"), make_drug("Panadol", "Paracetamol", "500mg")]
    result = svc.evaluate_medications(drugs)
    assert any(a.severity == "MEDIUM" and "warfarin" in a.title.lower() for a in result.alerts)


def test_ciprofloxacin_calcium_medium(svc: EvaluationService):
    drugs = [make_drug("Ciprofloxacin 500", "Ciprofloxacin", "500mg"), make_drug("Calcium-D3", "Calcium", "500mg")]
    result = svc.evaluate_medications(drugs)
    assert any(a.severity == "MEDIUM" and "ciprofloxacin" in a.title.lower() for a in result.alerts)


def test_ciprofloxacin_iron_medium(svc: EvaluationService):
    drugs = [make_drug("Ciprofloxacin 500", "Ciprofloxacin", "500mg"), make_drug("Fefol", "Iron", "50mg")]
    result = svc.evaluate_medications(drugs)
    assert any(a.severity == "MEDIUM" and "ciprofloxacin" in a.title.lower() for a in result.alerts)


def test_amoxicillin_methotrexate_high(svc: EvaluationService):
    drugs = [make_drug("Amoxicillin 500", "Amoxicillin", "500mg"), make_drug("Methotrexate", "Methotrexate", "2.5mg")]
    result = svc.evaluate_medications(drugs)
    assert any(a.severity == "HIGH" and "methotrexate" in a.title.lower() for a in result.alerts)


def test_simvastatin_amiodarone_high(svc: EvaluationService):
    drugs = [make_drug("Zocor", "Simvastatin", "20mg"), make_drug("Amiodarone", "Amiodarone", "200mg")]
    result = svc.evaluate_medications(drugs)
    assert any(a.severity == "HIGH" and "simvastatin" in a.title.lower() for a in result.alerts)


def test_metformin_alcohol_medium(svc: EvaluationService):
    drugs = [make_drug("Glucophage", "Metformin", "850mg"), make_drug("Sirô ho", "Alcohol", "10ml")]
    result = svc.evaluate_medications(drugs)
    assert any(a.severity == "MEDIUM" and "metformin" in a.title.lower() for a in result.alerts)


def test_clopidogrel_omeprazole_medium(svc: EvaluationService):
    drugs = [make_drug("Plavix", "Clopidogrel", "75mg"), make_drug("Losec", "Omeprazole", "20mg")]
    result = svc.evaluate_medications(drugs)
    assert any(a.severity == "MEDIUM" and "clopidogrel" in a.title.lower() for a in result.alerts)


def test_clarithromycin_simvastatin_high(svc: EvaluationService):
    drugs = [make_drug("Klacid", "Clarithromycin", "500mg"), make_drug("Zocor", "Simvastatin", "20mg")]
    result = svc.evaluate_medications(drugs)
    assert any(a.severity == "HIGH" and "clarithromycin" in a.title.lower() for a in result.alerts)


def test_safe_combination_no_drug_drug_high(svc: EvaluationService):
    """Paracetamol + Amoxicillin + Omeprazole -> không có Drug-Drug HIGH."""
    drugs = [
        make_drug("Panadol", "Paracetamol"),
        make_drug("Augmentin", "Amoxicillin / Clavulanic acid", "625mg"),
        make_drug("Losec", "Omeprazole", "20mg"),
    ]
    result = svc.evaluate_medications(drugs)
    # Chỉ chấp nhận HIGH đến từ Layer 1 (trùng/không có ở đây), không phải Drug-Drug
    assert not any("nguy hiểm" in a.title.lower() or "chống chỉ định" in a.title.lower() for a in high_alerts(result))


# ═════════════════════════════════════════════════════════════════════════════
# LAYER 3: THUỐC - BỆNH NỀN / DỊ ỨNG (Drug-Condition)
# ═════════════════════════════════════════════════════════════════════════════

def test_ibuprofen_gastric_ulcer_high(svc: EvaluationService):
    drugs = [make_drug("Brufen", "Ibuprofen", "400mg")]
    profile = UserProfile(age=55, conditions=["viêm loét dạ dày"], allergies=[])
    result = svc.evaluate_medications(drugs, user_profile=profile)
    assert any(a.severity == "HIGH" and "loét" in a.title.lower() for a in result.alerts)


def test_pseudoephedrine_hypertension_high(svc: EvaluationService):
    drugs = [make_drug("Sudafed", "Pseudoephedrine", "60mg")]
    profile = UserProfile(age=60, conditions=["Cao huyết áp"], allergies=[])
    result = svc.evaluate_medications(drugs, user_profile=profile)
    assert any(a.severity == "HIGH" and "huyết áp" in a.title.lower() for a in result.alerts)


def test_metformin_renal_failure_high(svc: EvaluationService):
    drugs = [make_drug("Glucophage", "Metformin", "850mg")]
    profile = UserProfile(age=65, conditions=["suy thận mạn"], allergies=[])
    result = svc.evaluate_medications(drugs, user_profile=profile)
    assert any(a.severity == "HIGH" and "thận" in a.title.lower() for a in result.alerts)


def test_statin_liver_disease_high(svc: EvaluationService):
    drugs = [make_drug("Zocor", "Simvastatin", "20mg")]
    profile = UserProfile(age=50, conditions=["xơ gan"], allergies=[])
    result = svc.evaluate_medications(drugs, user_profile=profile)
    assert any(a.severity == "HIGH" and "gan" in a.title.lower() for a in result.alerts)


def test_amoxicillin_penicillin_allergy_high(svc: EvaluationService):
    drugs = [make_drug("Amoxicillin 500", "Amoxicillin", "500mg")]
    profile = UserProfile(age=30, conditions=[], allergies=["Dị ứng Penicillin"])
    result = svc.evaluate_medications(drugs, user_profile=profile)
    assert any(a.severity == "HIGH" and "dị ứng" in a.title.lower() for a in result.alerts)


def test_ibuprofen_asthma_medium(svc: EvaluationService):
    drugs = [make_drug("Brufen", "Ibuprofen", "400mg")]
    profile = UserProfile(age=25, conditions=["hen suyễn"], allergies=[])
    result = svc.evaluate_medications(drugs, user_profile=profile)
    assert any(a.severity == "MEDIUM" and "hen" in a.title.lower() for a in result.alerts)


def test_warfarin_pregnancy_high(svc: EvaluationService):
    drugs = [make_drug("Sintrom", "Warfarin", "4mg")]
    profile = UserProfile(age=28, conditions=["Mang thai"], allergies=[])
    result = svc.evaluate_medications(drugs, user_profile=profile)
    assert any(a.severity == "HIGH" and "thai" in a.title.lower() for a in result.alerts)


def test_no_condition_match_no_layer3_alert(svc: EvaluationService):
    """Bệnh nhân không có bệnh nền liên quan -> không có Drug-Condition alert."""
    drugs = [make_drug("Sudafed", "Pseudoephedrine", "60mg")]
    profile = UserProfile(age=40, conditions=["Viêm khớp"], allergies=[])
    result = svc.evaluate_medications(drugs, user_profile=profile)
    assert not any("huyết áp" in a.title.lower() for a in result.alerts)


# ═════════════════════════════════════════════════════════════════════════════
# EDGE CASES & TỔNG HỢP
# ═════════════════════════════════════════════════════════════════════════════

def test_empty_drug_list_no_crash(svc: EvaluationService):
    result = svc.evaluate_medications([])
    assert result.total_drugs_analyzed == 0
    assert result.alerts == []


def test_drug_without_active_ingredient_ignored(svc: EvaluationService):
    drugs = [make_drug("Không rõ", None)]
    result = svc.evaluate_medications(drugs)
    assert result.total_drugs_analyzed == 1
    assert result.alerts == []


def test_total_drugs_analyzed_count(svc: EvaluationService):
    drugs = [
        make_drug("Panadol", "Paracetamol"),
        make_drug("Augmentin", "Amoxicillin", "625mg"),
        make_drug("Losec", "Omeprazole", "20mg"),
    ]
    result = svc.evaluate_medications(drugs)
    assert result.total_drugs_analyzed == 3


def test_alerts_sorted_high_first(svc: EvaluationService):
    drugs = [
        make_drug("Brufen", "Ibuprofen", "400mg"),
        make_drug("Sintrom", "Warfarin", "4mg"),
    ]
    profile = UserProfile(age=60, conditions=["viêm loét dạ dày"], allergies=[])
    result = svc.evaluate_medications(drugs, user_profile=profile)
    if result.alerts:
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        severities = [severity_order[a.severity] for a in result.alerts]
        assert severities == sorted(severities)


def test_dosage_parsing_half_tablet(svc: EvaluationService):
    """Hỗ trợ liều 1/2 viên: 500mg x 0.5 viên x 2 lần = 500mg/ngày."""
    drugs = [make_drug("Panadol", "Paracetamol", "500mg", "Uống 0.5 viên/lần x 2 lần/ngày")]
    result = svc.evaluate_medications(drugs)
    assert result.total_drugs_analyzed == 1
    assert not any("quá liều" in a.title.lower() for a in result.alerts)


def test_schedule_suggestion_generated(svc: EvaluationService):
    drugs = [make_drug("Panadol", "Paracetamol")]
    result = svc.evaluate_medications(drugs)
    assert len(result.schedule_suggestions) >= 1


def test_normalization_fuzzy_match_panadol_extra():
    """Kiểm thử chuẩn hóa tên thương mại -> hoạt chất gốc bằng Fuzzy Match."""
    raw = make_drug("Panadol Extra", None, "500mg", "Uống 1 viên", confidence=0.8, verified=False)
    normalized = normalization_service.normalize_drug_item(raw)
    assert normalized.active_ingredient == "Paracetamol / Caffeine"
    assert normalized.strength == "500mg / 65mg"


def test_normalization_fuzzy_match_efferalgan():
    raw = make_drug("Efferalgan", None, "500mg", "Uống 1 viên", confidence=0.9, verified=False)
    normalized = normalization_service.normalize_drug_item(raw)
    assert "Paracetamol" in normalized.active_ingredient
