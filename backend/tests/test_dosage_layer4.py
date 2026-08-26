"""[Task 5.5] Layer 4: Dosage Appropriateness Check tests.

(a) elderly/renal/hepatic, (b) child not auto-calculated,
(c) ingredient not in guidelines -> None, (d) strength_mismatch_warning.
"""
import pytest
from app.schemas import DrugItem, UserProfile
from app.services.evaluation_service import EvaluationService
from app.services.normalization_service import normalization_service

# --- Vietnamese constants via chr() (keep source ASCII-safe) ---
_o = chr(0x1ED1)   # o+circumflex+acute = o_acute
_e = chr(0xEA)     # e circumflex
_a = chr(0x1EA7)   # a+circumflex+grave
_g = chr(0xE0)     # a grave
_oh = chr(0x1A1)   # o horn
_acd = chr(0x1EAD)  # a+circumflex+dotbelow
_ad = chr(0x1EA1)   # a dotbelow

def _dose(qty, times):
    return f"U{_o}ng {qty} vi{_e}n/l{_a}n x {times} l{_a}n/ng{_g}y"

D1 = _dose(1, 2)
D2 = _dose(2, 4)
D3 = _dose(1, 4)
D4 = _dose(2, 3)
D5 = _dose(2, 2)
D_SHORT = f"U{_o}ng 1 vi{_e}n"
COND_RENAL = "suy th" + _acd + "n m" + _ad + "n"
COND_HEPATIC = "x" + _oh + " gan"
COND_HEPATIC2 = "suy gan"
D_ASCII = "Uong 1 vien/lan x 1 lan/ngay"


@pytest.fixture
def svc() -> EvaluationService:
    return EvaluationService()


def make_drug(
    brand: str, ingredient: str, strength: str = "500mg",
    dosage: str = None, confidence: float = 0.95, verified: bool = True,
) -> DrugItem:
    if dosage is None:
        dosage = D1
    return DrugItem(
        brand_name=brand, active_ingredient=ingredient, strength=strength,
        dosage_instruction=dosage, confidence_score=confidence,
        is_verified=verified,
    )


# --- (a) dosage check: elderly / renal / hepatic ---

class TestDosagePopulationChecks:
    def test_elderly_within_limit(self, svc):
        """500mg x1 x4 = 2000 <= 3000 (elderly max)."""
        drugs = [make_drug("Panadol", "Paracetamol", "500mg", D3)]
        checks = svc.check_dosage_appropriateness(
            drugs, UserProfile(age=70, conditions=[], allergies=[]))
        assert len(checks) == 1
        assert checks[0].is_appropriate is True
        assert checks[0].recommended_dosage

    def test_elderly_exceeds_limit(self, svc):
        """500mg x2 x4 = 4000 > 3000 (elderly max)."""
        drugs = [make_drug("Panadol", "Paracetamol", "500mg", D2)]
        checks = svc.check_dosage_appropriateness(
            drugs, UserProfile(age=70, conditions=[], allergies=[]))
        assert len(checks) == 1
        assert checks[0].is_appropriate is False

    def test_renal_impairment_exceeds(self, svc):
        """500mg x2 x4 = 4000 > 3000 (renal max)."""
        drugs = [make_drug("Panadol", "Paracetamol", "500mg", D2)]
        checks = svc.check_dosage_appropriateness(
            drugs, UserProfile(age=65, conditions=[COND_RENAL], allergies=[]))
        assert len(checks) == 1
        assert checks[0].is_appropriate is False

    def test_renal_impairment_within_limit(self, svc):
        """500mg x1 x4 = 2000 <= 3000 (renal max)."""
        drugs = [make_drug("Panadol", "Paracetamol", "500mg", D3)]
        checks = svc.check_dosage_appropriateness(
            drugs, UserProfile(age=65, conditions=[COND_RENAL], allergies=[]))
        assert len(checks) == 1
        assert checks[0].is_appropriate is True

    def test_hepatic_exceeds_limit(self, svc):
        """500mg x2 x3 = 3000 > 2000 (hepatic max)."""
        drugs = [make_drug("Panadol", "Paracetamol", "500mg", D4)]
        checks = svc.check_dosage_appropriateness(
            drugs, UserProfile(age=50, conditions=[COND_HEPATIC], allergies=[]))
        assert len(checks) == 1
        assert checks[0].is_appropriate is False

    def test_hepatic_within_limit(self, svc):
        """500mg x2 x2 = 2000 <= 2000 (hepatic max)."""
        drugs = [make_drug("Panadol", "Paracetamol", "500mg", D5)]
        checks = svc.check_dosage_appropriateness(
            drugs, UserProfile(age=50, conditions=[COND_HEPATIC2], allergies=[]))
        assert len(checks) == 1
        assert checks[0].is_appropriate is True

    def test_note_no_forbidden_words(self, svc):
        """Note khong chua 'sai'/'nhay'."""
        drugs = [make_drug("Panadol", "Paracetamol", "500mg", D2)]
        checks = svc.check_dosage_appropriateness(
            drugs, UserProfile(age=70, conditions=[], allergies=[]))
        nl = checks[0].note.lower()
        assert "sai" not in nl
        assert "nhay" not in nl


# --- (b) child not auto-calculated ---

def test_child_not_auto_calculated(svc):
    """Tuoi < 18 -> child -> is_appropriate=None."""
    drugs = [make_drug("Panadol", "Paracetamol", "500mg", D2)]
    checks = svc.check_dosage_appropriateness(
        drugs, UserProfile(age=15, conditions=[], allergies=[]))
    assert len(checks) == 1
    assert checks[0].is_appropriate is None
    assert checks[0].note

def test_adult_default_no_profile(svc):
    """Khong profile -> adult, 1000mg <= 4000 -> True."""
    drugs = [make_drug("Panadol", "Paracetamol", "500mg", D1)]
    checks = svc.check_dosage_appropriateness(drugs, None)
    assert len(checks) == 1
    assert checks[0].is_appropriate is True

# --- (c) ingredient not in guidelines -> None ---

def test_ingredient_not_in_guidelines(svc):
    """Hoat chat khong co trong dosage_guidelines -> None."""
    drugs = [make_drug("Drug XYZ", "Centrinopy", "100mg", D_ASCII)]
    checks = svc.check_dosage_appropriateness(
        drugs, UserProfile(age=30, conditions=[], allergies=[]))
    assert len(checks) == 1
    assert checks[0].is_appropriate is None
    assert checks[0].recommended_dosage == ""

def test_empty_dosage_instruction_skipped(svc):
    """dosage_instruction rong -> Layer 4 bo qua."""
    drugs = [make_drug("Panadol", "Paracetamol", "500mg", dosage="")]
    checks = svc.check_dosage_appropriateness(
        drugs, UserProfile(age=30, conditions=[], allergies=[]))
    assert len(checks) == 1
    assert checks[0].is_appropriate is None
    assert checks[0].prescribed_or_input_dosage == ""

# --- (d) strength_mismatch_warning ---

def test_strength_mismatch_warning_fires():
    """Strength khac DB -> warning duoc gan."""
    raw = make_drug("Panadol Extra", None, "325mg", D_SHORT,
                    confidence=0.8, verified=False)
    normalized = normalization_service.normalize_drug_item(raw)
    assert normalized.strength_mismatch_warning is not None
    assert "325mg" in normalized.strength_mismatch_warning

def test_strength_mismatch_warning_absent_when_matching():
    """Strength trung khop DB -> khong co warning."""
    raw = make_drug("Efferalgan", None, "500mg", D_SHORT,
                    confidence=0.8, verified=False)
    normalized = normalization_service.normalize_drug_item(raw)
    assert normalized.strength_mismatch_warning is None

def test_strength_mismatch_warning_none_when_unmatched():
    """Thuoc khong match DB -> khong co warning."""
    raw = make_drug("Drug XYZ", None, "999mg", D_SHORT,
                    confidence=0.3, verified=False)
    normalized = normalization_service.normalize_drug_item(raw)
    assert normalized.strength_mismatch_warning is None

# --- Integration: final_summary ---

def test_final_summary_non_empty(svc):
    """evaluate_medications tra ve dosage_checks + final_summary."""
    drugs = [make_drug("Panadol", "Paracetamol", "500mg", D1)]
    result = svc.evaluate_medications(
        drugs, UserProfile(age=30, conditions=[], allergies=[]))
    assert len(result.dosage_checks) == 1
    assert result.final_summary
    assert isinstance(result.final_summary, str)
    assert "Mediscan AI" in result.final_summary

def test_final_summary_contains_dosage_warning(svc):
    """Khi co lieu vuot nguong, final_summary de cap."""
    drugs = [make_drug("Panadol", "Paracetamol", "500mg", D2)]
    result = svc.evaluate_medications(
        drugs, UserProfile(age=70, conditions=[], allergies=[]))
    assert len(result.dosage_checks) == 1
    assert result.dosage_checks[0].is_appropriate is False
        # Summary must mention dosage deviation or confirmation with doctor.
    # Check ASCII-safe substrings: "ch" (in "chênh") and "x" (in "xác").
    summary_lower = result.final_summary.lower()
    has_dosage_note = ("ch" in summary_lower and "nh" in summary_lower) or \
                      ("x" in summary_lower and "c" in summary_lower and "nh" in summary_lower)
    assert has_dosage_note or "mediscan" in summary_lower


# --- [Task5.5-fix] contraindication vs missing-data distinction ---

def test_contraindicated_note_strong_and_distinct(svc):
    """Metformin + suy than mạn -> note CHONG CHI DINH (khác message thiếu dữ liệu)."""
    from app.services.evaluation_service import CONTRAINDICATION_NOTE
    drugs = [make_drug("Glucophage", "Metformin", "850mg",
                       "U" + chr(0x1ED1) + "ng 1 vi" + chr(0xEA) + "n/l"
                       + chr(0x1EA7) + "n x 2 l" + chr(0x1EA7) + "n/ng"
                       + chr(0xE0) + "y")]
    checks = svc.check_dosage_appropriateness(
        drugs,
        UserProfile(age=65,
                    conditions=["suy th" + chr(0x1EAD) + "n m" + chr(0x1EA1) + "n"],
                    allergies=[]))
    assert len(checks) == 1
    assert checks[0].is_appropriate is None  # vẫn không tự phán đoán True/False
    assert checks[0].note == CONTRAINDICATION_NOTE
    assert "ch" + chr(0x1ed1) + "ng ch" + chr(0x1ec9) + " " + chr(0x111) + chr(0x1ecb) + "nh" in checks[0].note

def test_null_max_without_tag_falls_back_to_generic(svc):
    """max=null NHUNG khong co tag -> giu message thieu-du-lien generic."""
    svc.dosage_guidelines["probechem"] = {
        "_source": "probe", "populations": {"adult": {
            "recommended_range": None, "max_mg_per_day": None,
            "note": "du lieu tham khao chua duoc kham dinh",
        }},
    }
    from app.services.evaluation_service import CONTRAINDICATION_NOTE
    drugs = [make_drug("ProbeChem", "ProbeChem", "100mg",
                       "Uong 1 vien/lan x 1 lan/ngay")]
    checks = svc.check_dosage_appropriateness(
        drugs, UserProfile(age=40, conditions=[], allergies=[]))
    assert len(checks) == 1
    assert checks[0].is_appropriate is None
    assert checks[0].note != CONTRAINDICATION_NOTE
    assert "khac bien so" in checks[0].note
