"""[Audit-S3 / P0 / F3.1] Smoke tests chống regression schema-crash.

Bối cảnh: `ocr_schema.py` từng thiếu `from typing import Optional`. Trên Python 3.14
(PEP 649 — lazy annotations) import vẫn xanh nhưng Pydantic không build được core
schema; lỗi chỉ nổ khi instantiate (`PydanticUserError: ... is not fully defined`).
Trên Docker python:3.12 (annotation eager) sẽ là NameError ngay lúc import → container
crash. Suite này ép build + instantiate toàn bộ model public để CI đỏ ngay nếu ai
xóa import lần nữa, thay vì chờ Docker crash ở production.

Wire-format pin: envelope ngoài camelCase (to_camel), payload `clinical_assessment`
bên trong snake_case (4 model clinical không có alias — quyết định P0/F3.1).
"""

from app.schemas.ocr_schema import (
    ClinicalAlertSummary,
    ClinicalAssessmentResponse,
    DrugConditionAlert,
    DrugInteractionAlert,
    FullScanResponse,
    MappedDrugItem,
    OCRItem,
    OverdoseAlert,
)


def _dd_alert() -> DrugInteractionAlert:
    return DrugInteractionAlert(
        severity="HIGH",
        title="Tương tác thử nghiệm",
        description="Mô tả tương tác A+B",
        recommendation="Tham vấn bác sĩ",
        interacting_drugs=["A", "B"],
        evidence_level="A",
    )


def test_ocr_item_instantiates():
    item = OCRItem(text="Panadol 500mg", confidence=0.92, box=[1.0, 2.0, 3.0, 4.0])
    assert item.text == "Panadol 500mg"
    assert abs(item.confidence - 0.92) < 1e-9


def test_mapped_drug_item_instantiates():
    m = MappedDrugItem(
        brand_name="Panadol",
        active_ingredient="Paracetamol",
        strength="500mg",
        confidence_score=0.9,
        is_verified=False,
        match_method="exact",
    )
    assert m.drug_id is None
    assert m.match_method == "exact"


def test_clinical_alert_models_instantiate():
    dd = _dd_alert()
    dc = DrugConditionAlert(
        severity="MEDIUM",
        title="Thận trọng thử nghiệm",
        description="Mô tả",
        recommendation="Tham vấn bác sĩ",
        drug_name="Warfarin",
        condition="Suy thận",
        evidence_level="B",
    )
    od = OverdoseAlert(
        severity="LOW",
        title="Tham khảo thử nghiệm",
        description="Mô tả",
        recommendation="Theo dõi",
        ingredient="Paracetamol",
        total_daily_mg=3000.0,
        max_safe_mg=4000.0,
    )
    assert dd.interacting_drugs == ["A", "B"]
    assert dc.condition == "Suy thận"
    assert od.max_safe_mg == 4000.0


def test_clinical_assessment_response_instantiates_with_defaults():
    resp = ClinicalAssessmentResponse(drug_drug_interactions=[_dd_alert()])
    assert len(resp.drug_drug_interactions) == 1
    assert len(resp.drug_condition_interactions) == 0
    assert len(resp.overdose_duplication_alerts) == 0
    assert resp.disclaimer  # Disclaimer mặc định luôn tồn tại (AGENTS.md §B.3)


def test_full_scan_response_instantiates_and_preserves_wire_format():
    """Pin wire-format lịch sử (quyết định P0/F3.1):
    - Envelope ngoài: camelCase (FastAPI serialize response_model với by_alias=True).
    - Payload clinical_assessment: snake_case (4 model clinical không có alias).
    """
    assessment = ClinicalAssessmentResponse(drug_drug_interactions=[_dd_alert()])
    resp = FullScanResponse(
        engine="PP-OCRv6-ONNX",
        source_type="prescription",
        raw_ocr_items=[OCRItem(text="Panadol 500mg", confidence=0.9)],
        ocr_latency_ms=100,
        sla_exceeded=False,
        image_width=640,
        image_height=480,
        mapped_drugs=[
            MappedDrugItem(
                brand_name="Panadol",
                strength="500mg",
                confidence_score=0.9,
                is_verified=False,
            )
        ],
        clinical_assessment=assessment,
        clinical_summary=ClinicalAlertSummary(
            total_alerts=1,
            high_count=1,
            medium_count=0,
            low_count=0,
            drug_drug_interactions=1,
            drug_condition_interactions=0,
            overdose_duplication=0,
        ),
        total_latency_ms=150,
        normalization_latency_ms=10,
        clinical_latency_ms=40,
    )
    dumped = resp.model_dump(by_alias=True)  # FastAPI serialize_response dùng by_alias=True
    assert "rawOcrItems" in dumped
    assert "mappedDrugs" in dumped
    assert "clinicalSummary" in dumped
    inner = dumped["clinicalAssessment"]
    assert "drug_drug_interactions" in inner  # snake_case được bảo toàn
    assert "clinical_recommendations" in inner
    assert inner["drug_drug_interactions"][0]["severity"] == "HIGH"


def test_all_public_models_core_schema_built_not_mocked():
    """Tripwire chính: khi thiếu import (vd Optional), Pydantic giữ mock validator
    và raise `PydanticUserError: ... is not fully defined` khi build/validate.
    model_rebuild() phải thành công lặng lẽ trên mọi model public."""
    public_models = (
        OCRItem,
        MappedDrugItem,
        DrugInteractionAlert,
        DrugConditionAlert,
        OverdoseAlert,
        ClinicalAssessmentResponse,
        ClinicalAlertSummary,
        FullScanResponse,
    )
    for model in public_models:
        model.model_rebuild()  # raise PydanticUserError nếu names unresolvable
        assert model.__pydantic_core_schema__["type"] == "model"