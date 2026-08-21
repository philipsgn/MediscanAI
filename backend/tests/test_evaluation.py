"""
Unit Tests cho Evaluation Service - Stage 4
Test kịch bản: Overdose Paracetamol, Drug-Drug, Drug-Condition
"""
import pytest
from app.schemas import DrugItem, UserProfile
from app.services.evaluation_service import EvaluationService


@pytest.fixture
def svc() -> EvaluationService:
    return EvaluationService()


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 1: Overdose Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_paracetamol_overdose_dual_product(svc: EvaluationService):
    """
    Test kịch bản chính:
    Panadol 500mg (2 viên x 3 lần/ngày = 3000mg) + Efferalgan 500mg (2 viên x 2 lần/ngày = 2000mg)
    Tổng: 5000mg > 4000mg max → phải tạo HIGH alert
    """
    drugs = [
        DrugItem(
            brand_name="Panadol Extra",
            active_ingredient="Paracetamol / Caffeine",
            strength="500mg",
            dosage_instruction="Uống 2 viên/lần x 3 lần/ngày sau ăn",
            confidence_score=0.98,
            is_verified=True
        ),
        DrugItem(
            brand_name="Efferalgan 500mg",
            active_ingredient="Paracetamol",
            strength="500mg",
            dosage_instruction="Uống 2 viên/lần x 2 lần/ngày",
            confidence_score=0.95,
            is_verified=True
        )
    ]
    result = svc.evaluate_medications(drugs)
    
    # Phải có ít nhất 1 HIGH alert
    high_alerts = [a for a in result.alerts if a.severity == "HIGH"]
    assert len(high_alerts) >= 1, "Phải có ít nhất 1 HIGH alert khi vượt ngưỡng Paracetamol"
    
    # Alert phải đề cập đến Paracetamol
    paracetamol_alert = next(
        (a for a in high_alerts if "paracetamol" in a.title.lower()),
        None
    )
    assert paracetamol_alert is not None, "Phải có HIGH alert cụ thể về Paracetamol overdose"


def test_single_drug_within_safe_dose(svc: EvaluationService):
    """Một loại Paracetamol dùng đúng liều → không có overdose alert"""
    drugs = [
        DrugItem(
            brand_name="Panadol Extra",
            active_ingredient="Paracetamol",
            strength="500mg",
            dosage_instruction="Uống 1 viên/lần x 3 lần/ngày",
            confidence_score=0.98,
            is_verified=True
        )
    ]
    result = svc.evaluate_medications(drugs)
    overdose_alerts = [a for a in result.alerts if "quá liều" in a.title.lower() or "overdose" in a.title.lower()]
    assert len(overdose_alerts) == 0, "Không có overdose alert khi dùng đúng liều"


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 2: Drug-Drug Interaction Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_aspirin_ibuprofen_interaction(svc: EvaluationService):
    """Aspirin + Ibuprofen → HIGH alert"""
    drugs = [
        DrugItem(brand_name="Aspirin", active_ingredient="Aspirin", strength="100mg",
                 dosage_instruction="1 viên/ngày", confidence_score=0.95, is_verified=True),
        DrugItem(brand_name="Ibuprofen 400", active_ingredient="Ibuprofen", strength="400mg",
                 dosage_instruction="1 viên/lần x 2 lần/ngày", confidence_score=0.95, is_verified=True),
    ]
    result = svc.evaluate_medications(drugs)
    high_alerts = [a for a in result.alerts if a.severity == "HIGH"]
    assert len(high_alerts) >= 1, "Phải có HIGH alert cho Aspirin + Ibuprofen"


def test_warfarin_aspirin_interaction(svc: EvaluationService):
    """Warfarin + Aspirin → HIGH alert"""
    drugs = [
        DrugItem(brand_name="Sintrom", active_ingredient="Warfarin", strength="4mg",
                 dosage_instruction="1 viên/ngày", confidence_score=0.98, is_verified=True),
        DrugItem(brand_name="Aspirin Cardio", active_ingredient="Aspirin", strength="100mg",
                 dosage_instruction="1 viên/ngày", confidence_score=0.98, is_verified=True),
    ]
    result = svc.evaluate_medications(drugs)
    high_alerts = [a for a in result.alerts if a.severity == "HIGH"]
    assert len(high_alerts) >= 1, "Phải có HIGH alert cho Warfarin + Aspirin"


def test_no_interaction_safe_combination(svc: EvaluationService):
    """Paracetamol + Amoxicillin → không có Drug-Drug interaction alert"""
    drugs = [
        DrugItem(brand_name="Panadol", active_ingredient="Paracetamol", strength="500mg",
                 dosage_instruction="1 viên/lần x 3 lần/ngày", confidence_score=0.98, is_verified=True),
        DrugItem(brand_name="Augmentin", active_ingredient="Amoxicillin / Clavulanic acid", strength="625mg",
                 dosage_instruction="1 viên/lần x 2 lần/ngày", confidence_score=0.97, is_verified=True),
    ]
    result = svc.evaluate_medications(drugs)
    # Không nên có HIGH từ Drug-Drug interaction
    high_drug_drug = [a for a in result.alerts if a.severity == "HIGH" and "warfarin" not in a.title.lower()]
    assert len(high_drug_drug) == 0, "Không có HIGH alert cho tổ hợp Paracetamol + Amoxicillin"


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 3: Drug-Condition Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_ibuprofen_contraindicated_with_gastric_ulcer(svc: EvaluationService):
    """Ibuprofen + Loét dạ dày → HIGH alert"""
    drugs = [
        DrugItem(brand_name="Brufen", active_ingredient="Ibuprofen", strength="400mg",
                 dosage_instruction="1 viên/lần x 2 lần/ngày", confidence_score=0.95, is_verified=True),
    ]
    profile = UserProfile(age=55, conditions=["viêm loét dạ dày"], allergies=[])
    result = svc.evaluate_medications(drugs, user_profile=profile)
    
    high_alerts = [a for a in result.alerts if a.severity == "HIGH"]
    assert len(high_alerts) >= 1, "Phải có HIGH alert khi dùng Ibuprofen với bệnh nhân loét dạ dày"


def test_pseudoephedrine_hypertension(svc: EvaluationService):
    """Pseudoephedrine + Cao huyết áp → HIGH alert"""
    drugs = [
        DrugItem(brand_name="Sudafed", active_ingredient="Pseudoephedrine", strength="60mg",
                 dosage_instruction="1 viên/lần x 2 lần/ngày", confidence_score=0.95, is_verified=True),
    ]
    profile = UserProfile(age=60, conditions=["cao huyết áp"], allergies=[])
    result = svc.evaluate_medications(drugs, user_profile=profile)
    
    high_alerts = [a for a in result.alerts if a.severity == "HIGH"]
    assert len(high_alerts) >= 1, "Phải có HIGH alert khi dùng Pseudoephedrine với bệnh nhân cao huyết áp"


def test_total_drugs_analyzed_count(svc: EvaluationService):
    """Kiểm tra số thuốc phân tích khớp đúng trong response"""
    drugs = [
        DrugItem(brand_name="Panadol", active_ingredient="Paracetamol", strength="500mg",
                 dosage_instruction="1 viên/lần x 3 lần/ngày", confidence_score=0.98, is_verified=True),
        DrugItem(brand_name="Augmentin", active_ingredient="Amoxicillin", strength="625mg",
                 dosage_instruction="1 viên/lần x 2 lần/ngày", confidence_score=0.97, is_verified=True),
        DrugItem(brand_name="Omeprazole", active_ingredient="Omeprazole", strength="20mg",
                 dosage_instruction="1 viên/ngày trước ăn", confidence_score=0.96, is_verified=True),
    ]
    result = svc.evaluate_medications(drugs)
    assert result.total_drugs_analyzed == 3
