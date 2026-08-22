"""[Audit-S3 / P1 / F3.2] Test fail-safe severity clamp.

Yêu cầu Audit: giả lập LLM trả severity="CRITICAL" (và các biến thể lệch chuẩn khác)
phải được clamp lên "HIGH" — tuyệt đối KHÔNG rơi xuống "LOW", KHÔNG raise exception
làm chết pipeline (AGENTS.md §B.4, §5).
"""

import pytest

from app.schemas import InteractionAlert
from app.schemas.ocr_schema import (
    ClinicalAssessmentResponse,
    DrugConditionAlert,
    DrugInteractionAlert,
    OverdoseAlert,
    clamp_severity,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("CRITICAL", "HIGH"),      # alias nguy hiểm → nâng HIGH (case chính từ audit)
        ("severe", "HIGH"),
        ("EXTREME", "HIGH"),
        ("URGENT", "HIGH"),
        ("moderate", "MEDIUM"),
        ("caution", "MEDIUM"),
        ("minor", "LOW"),
        ("info", "LOW"),
        ("HIGH", "HIGH"),          # giá trị chuẩn pass-through
        ("Medium", "MEDIUM"),
        ("low", "LOW"),
        ("", "HIGH"),              # chuỗi rỗng → fail-safe HIGH
        ("   ", "HIGH"),
        ("garbage!!", "HIGH"),     # vô nghĩa → fail-safe HIGH
        ("critical ", "HIGH"),     # whitespace
        (None, "HIGH"),            # sai kiểu → fail-safe HIGH
        (123, "HIGH"),
        (["HIGH"], "HIGH"),
    ],
)
def test_clamp_failsafe_never_downgrades(raw, expected):
    assert clamp_severity(raw) == expected


@pytest.mark.parametrize("raw", ["CRITICAL", "", "xyz", None])
def test_llm_critical_becomes_high_not_low(raw):
    """Case trọng tâm của audit: CRITICAL/garbage phải thành HIGH, không bao giờ LOW."""
    alert = DrugInteractionAlert(
        severity=raw, title="t", description="d", recommendation="r"
    )
    assert alert.severity == "HIGH"


def test_all_three_clinical_models_have_fail_safe():
    common = dict(title="t", description="d", recommendation="r")
    assert DrugInteractionAlert(severity="CRITICAL", **common).severity == "HIGH"
    assert DrugConditionAlert(
        severity="SEVERE", drug_name="X", condition="Y", **common
    ).severity == "HIGH"
    assert OverdoseAlert(
        severity="whatever", ingredient="Paracetamol", total_daily_mg=9000.0, **common
    ).severity == "HIGH"


def test_interaction_alert_contract_model_clamped():
    """InteractionAlert (contract /evaluate) cũng phải có fail-safe."""
    alert = InteractionAlert(
        severity="critical", title="t", description="d", recommendation="r"
    )
    assert alert.severity == "HIGH"


def test_valid_severities_pass_through_unchanged():
    common = dict(title="t", description="d", recommendation="r")
    for level in ("HIGH", "MEDIUM", "LOW"):
        assert DrugInteractionAlert(severity=level, **common).severity == level
        assert InteractionAlert(severity=level, **common).severity == level


def test_summary_counts_directly_after_clamp():
    """[P1/F3.2] _summarize_clinical đếm trực tiếp: alert 'CRITICAL' sau clamp
    phải nằm trong high_count, KHÔNG rơi vào low_count như bug cũ."""
    from app.api.v1.endpoints.ocr import _summarize_clinical

    assessment = ClinicalAssessmentResponse(
        drug_drug_interactions=[
            DrugInteractionAlert(severity="CRITICAL", title="t1", description="d", recommendation="r")
        ],
        overdose_duplication_alerts=[
            OverdoseAlert(
                severity="MEDIUM",
                title="t2",
                description="d",
                recommendation="r",
                ingredient="Paracetamol",
                total_daily_mg=5000.0,
            )
        ],
    )
    summary = _summarize_clinical(assessment)
    assert summary.high_count == 1      # CRITICAL đã clamp → HIGH
    assert summary.medium_count == 1
    assert summary.low_count == 0       # không còn bucket LOW ma
    assert summary.total_alerts == 2