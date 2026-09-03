"""
test_clinical_governance_coverage.py

Unit & Integration Tests for Stage 12: Clinical Knowledge Dataset Governance & DDI Coverage.
Xác minh toàn bộ các Bất biến An toàn Lâm sàng (Clinical Safety Invariants):
- INV-12-01: UNKNOWN IS NOT SAFE (Không đồng nhất thiếu dữ liệu với an toàn)
- INV-12-02: DATASET ABSENCE IS NOT CLINICAL NEGATIVE (Không suy diễn phủ định tuyệt đối từ dataset dương tính)
- INV-12-03: NORMALIZATION != COVERAGE (Chuẩn hóa RxNorm/Local không tự động tương đương với DDI coverage)
- INV-12-04: UNVERIFIED SOURCE CANNOT PROMOTE CLINICAL CONFIDENCE (OpenFDA unverified không được promote lên COVERED)
- Governance Validator: Schema, duplicate IDs, self-pairs, severity, manifest checksum, rollback safety.
- Zero Image Persistence Regression: Không rò rỉ dữ liệu ảnh vào provenance/response.
"""

from pathlib import Path
import pytest
import json

from app.schemas import DrugItem, UserProfile
from app.schemas.ocr_schema import (
    DatasetProvenanceInfo,
    DrugCoverageItem,
    DrugCoverageStatus,
    EvaluationResponse,
)
from app.services.ddinter_service import ddinter_service
from app.services.evaluation_service import evaluation_service
from app.governance.dataset_validator import dataset_validator, DatasetValidator


# ─────────────────────────────────────────────────────────────────────────────
# 1. Coverage State Machine Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_coverage_fully_covered_drugs():
    """Test 1: Cả 2 thuốc đều có trong CSDL DDInter -> coverage_status == 'FULL'."""
    drug1 = DrugItem(brand_name="Aspirin 81mg", active_ingredient="Aspirin", strength="81mg")
    drug2 = DrugItem(brand_name="Brufen 400mg", active_ingredient="Ibuprofen", strength="400mg")

    resp = evaluation_service.evaluate_medications([drug1, drug2])

    assert resp.coverage_status == "FULL"
    assert len(resp.drug_coverage_details) == 2
    for item in resp.drug_coverage_details:
        assert item.status == DrugCoverageStatus.COVERED
        assert item.canonical_ingredient in ("aspirin", "ibuprofen")


def test_coverage_partially_covered_drugs():
    """Test 2 (INV-12-03): Thuốc chuẩn hóa được nhưng nằm ngoài CSDL DDInter -> 'PARTIAL'."""
    # Aspirin có trong DDInter, Pantoprazole có trong synonym bridge nhưng chưa có pair trong DDInter
    drug1 = DrugItem(brand_name="Aspirin 81mg", active_ingredient="Aspirin", strength="81mg")
    drug2 = DrugItem(brand_name="Pantoloc 40mg", active_ingredient="Pantoprazole", strength="40mg")

    resp = evaluation_service.evaluate_medications([drug1, drug2])

    assert resp.coverage_status == "PARTIAL"
    assert len(resp.drug_coverage_details) == 2
    covered_item = next(d for d in resp.drug_coverage_details if d.drug_name == "Aspirin 81mg")
    uncovered_item = next(d for d in resp.drug_coverage_details if d.drug_name == "Pantoloc 40mg")

    assert covered_item.status == DrugCoverageStatus.COVERED
    assert uncovered_item.status == DrugCoverageStatus.NOT_COVERED_IN_DATASET
    assert "chưa có dữ liệu tương tác" in resp.final_summary


def test_coverage_unresolved_drug():
    """Test 3 (INV-12-01): Thuốc không trích xuất/chuẩn hóa được hoạt chất -> 'UNRESOLVED'."""
    drug1 = DrugItem(brand_name="Panadol", active_ingredient="Paracetamol", strength="500mg")
    drug2 = DrugItem(brand_name="ThuocLaKhongRoHoatChat", active_ingredient=None, strength="")

    resp = evaluation_service.evaluate_medications([drug1, drug2])

    assert resp.coverage_status == "UNRESOLVED"
    unresolved_item = next(d for d in resp.drug_coverage_details if d.drug_name == "ThuocLaKhongRoHoatChat")
    assert unresolved_item.status == DrugCoverageStatus.UNRESOLVED
    assert "chưa được định danh rõ ràng" in resp.final_summary


def test_coverage_ambiguous_candidate_requires_review():
    """Test 4: Thuốc có match_method 'rxnorm_approximate' -> AMBIGUOUS_REVIEW_REQUIRED."""
    drug1 = DrugItem(
        brand_name="AmbiguousBrand",
        active_ingredient="CandidateDrug",
        strength="10mg",
        match_method="rxnorm_approximate",
        is_verified=False,
    )
    resp = evaluation_service.evaluate_medications([drug1])

    assert resp.coverage_status == "UNRESOLVED"
    ambiguous_item = resp.drug_coverage_details[0]
    assert ambiguous_item.status == DrugCoverageStatus.AMBIGUOUS_REVIEW_REQUIRED


# ─────────────────────────────────────────────────────────────────────────────
# 2. Clinical Safety Invariants & Final Summary Gate Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_inv_12_01_unknown_is_not_safe():
    """INV-12-01: Danh sách có thuốc unresolvable KHÔNG bao giờ sinh summary vô điều kiện 'An toàn'."""
    drug1 = DrugItem(brand_name="ThuocX", active_ingredient=None, strength="10mg")
    drug2 = DrugItem(brand_name="ThuocY", active_ingredient=None, strength="20mg")

    resp = evaluation_service.evaluate_medications([drug1, drug2])

    assert len(resp.alerts) == 0  # Không có alert vì chưa verify
    assert "Không ghi nhận bản ghi tương tác nguy hiểm" not in resp.final_summary
    assert "Hệ thống không thể kiểm tra tương tác tự động" in resp.final_summary


def test_inv_12_02_dataset_absence_is_scoped():
    """INV-12-02: Cặp thuốc trong CSDL không có tương tác sinh summary rõ phạm vi CSDL, không khẳng định tuyệt đối."""
    # Ciprofloxacin + Paracetamol: Cả 2 có trong CSDL DDInter nhưng không có tương tác đối kháng trực tiếp
    drug1 = DrugItem(brand_name="Ciprobay 500mg", active_ingredient="Ciprofloxacin", strength="500mg")
    drug2 = DrugItem(brand_name="Panadol 500mg", active_ingredient="Paracetamol", strength="500mg")

    resp = evaluation_service.evaluate_medications([drug1, drug2])

    assert resp.coverage_status == "FULL"
    assert "trong phạm vi CSDL" in resp.final_summary or "trong phạm vi dữ liệu" in resp.final_summary


def test_inv_12_04_provenance_metadata_populated():
    """INV-12-04 & Provenance: Response mang đầy đủ thông tin metadata thật từ CSDL active."""
    drug1 = DrugItem(brand_name="Aspirin 81mg", active_ingredient="Aspirin", strength="81mg")
    resp = evaluation_service.evaluate_medications([drug1])

    assert resp.provenance_metadata is not None
    assert "DDInter" in resp.provenance_metadata.dataset_name
    assert resp.provenance_metadata.active_version == "2.0"
    assert resp.provenance_metadata.total_interaction_pairs == 20
    assert resp.provenance_metadata.covered_ingredients_count == 28
    assert "CC BY-NC-SA 4.0" in resp.provenance_metadata.license
    assert resp.provenance_metadata.sha256_checksum is not None
    assert len(resp.provenance_metadata.sha256_checksum) == 64


# ─────────────────────────────────────────────────────────────────────────────
# 3. Dataset Governance & Validator Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_validator_passes_on_active_production_dataset():
    """Test 7: Active dataset và manifest thật trên đĩa vượt qua kiểm định 100% không có lỗi."""
    data_path = Path(__file__).parent.parent / "app" / "data" / "ddinter_interactions.json"
    manifest_path = Path(__file__).parent.parent / "app" / "data" / "manifest.json"

    res = dataset_validator.validate_file(data_path, manifest_path)

    assert res.is_valid is True
    assert res.total_pairs_checked == 20
    assert res.total_ingredients_checked == 28
    assert len(res.errors) == 0
    assert len(res.checksum) == 64


def test_validator_detects_corrupted_json(tmp_path):
    """Test 8: Validator phát hiện file JSON lỗi cú pháp."""
    bad_file = tmp_path / "bad_dataset.json"
    bad_file.write_text("{ unclosed json", encoding="utf-8")

    res = dataset_validator.validate_file(bad_file)
    assert res.is_valid is False
    assert any("Failed to parse JSON" in e for e in res.errors)


def test_validator_detects_duplicate_ddinter_id(tmp_path):
    """Test 9: Validator phát hiện trùng lặp ddinter_id."""
    dup_file = tmp_path / "dup_id.json"
    payload = {
        "metadata": {"dataset_name": "Test", "dataset_version": "1.0", "license": "MIT"},
        "interactions": [
            {
                "ddinter_id": "DDInter100001",
                "drug_a": "aspirin",
                "drug_b": "ibuprofen",
                "severity": "HIGH",
                "mechanism": "A",
                "management": "B",
                "recommendation": "C",
            },
            {
                "ddinter_id": "DDInter100001",  # TRÙNG ID
                "drug_a": "warfarin",
                "drug_b": "aspirin",
                "severity": "HIGH",
                "mechanism": "A",
                "management": "B",
                "recommendation": "C",
            },
        ],
    }
    dup_file.write_text(json.dumps(payload), encoding="utf-8")

    res = dataset_validator.validate_file(dup_file)
    assert res.is_valid is False
    assert any("Duplicate ddinter_id" in e for e in res.errors)


def test_validator_detects_self_pair(tmp_path):
    """Test 10: Validator phát hiện lỗi cặp thuốc tự tương tác (drug_a == drug_b)."""
    self_pair_file = tmp_path / "self_pair.json"
    payload = {
        "metadata": {"dataset_name": "Test", "dataset_version": "1.0", "license": "MIT"},
        "interactions": [
            {
                "ddinter_id": "DDInter100002",
                "drug_a": "aspirin",
                "drug_b": "aspirin",  # SELF-PAIR
                "severity": "HIGH",
                "mechanism": "A",
                "management": "B",
                "recommendation": "C",
            }
        ],
    }
    self_pair_file.write_text(json.dumps(payload), encoding="utf-8")

    res = dataset_validator.validate_file(self_pair_file)
    assert res.is_valid is False
    assert any("Self-pair detected" in e for e in res.errors)


def test_validator_detects_invalid_severity(tmp_path):
    """Test 11: Validator phát hiện mức severity không hợp lệ."""
    invalid_sev_file = tmp_path / "invalid_sev.json"
    payload = {
        "metadata": {"dataset_name": "Test", "dataset_version": "1.0", "license": "MIT"},
        "interactions": [
            {
                "ddinter_id": "DDInter100003",
                "drug_a": "aspirin",
                "drug_b": "ibuprofen",
                "severity": "CATASTROPHIC_UNKNOWN",  # INVALID
                "mechanism": "A",
                "management": "B",
                "recommendation": "C",
            }
        ],
    }
    invalid_sev_file.write_text(json.dumps(payload), encoding="utf-8")

    res = dataset_validator.validate_file(invalid_sev_file)
    assert res.is_valid is False
    assert any("invalid severity" in e for e in res.errors)


def test_validator_rollback_target_safely_rejected():
    """Test 12 (Governance): Rollback target không tồn tại trên đĩa bị từ chối an toàn, không fake."""
    data_dir = Path(__file__).parent.parent / "app" / "data"
    res = dataset_validator.validate_rollback_target("1.0", data_dir)

    assert res.is_valid is False
    assert any("NOT AVAILABLE" in e for e in res.errors)
    assert any("does not physically exist" in e for e in res.errors)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Zero Image Persistence Regression
# ─────────────────────────────────────────────────────────────────────────────

def test_zero_image_persistence_in_evaluation_and_provenance():
    """Test 13: Bảo đảm tuyệt đối không chứa dữ liệu ảnh thô / base64 / binary trong response và provenance."""
    drug1 = DrugItem(brand_name="Aspirin", active_ingredient="Aspirin", strength="81mg")
    resp = evaluation_service.evaluate_medications([drug1])

    resp_dict = resp.model_dump()
    resp_str = json.dumps(resp_dict)

    assert "data:image" not in resp_str
    assert "base64" not in resp_str
    assert ".jpg" not in resp_str
    assert ".png" not in resp_str
    assert ".webp" not in resp_str
    assert "/storage/" not in resp_str


# ─────────────────────────────────────────────────────────────────────────────
# 5. Red-Team Adversarial & Boundary Safety Tests (Audit Phase 11)
# ─────────────────────────────────────────────────────────────────────────────

def test_dataset_checksum_mismatch_fails_closed(tmp_path):
    """Test 14: Dataset bị sửa đổi trái phép (checksum mismatch) khiến runtime đánh dấu integrity_verified=False."""
    from app.services.ddinter_service import DDInterService
    bad_data = tmp_path / "ddinter_tampered.json"
    bad_manifest = tmp_path / "manifest.json"

    bad_data.write_text(json.dumps({
        "metadata": {"dataset_name": "DDInter", "dataset_version": "2.0", "license": "CC BY-NC-SA 4.0"},
        "interactions": []
    }), encoding="utf-8")

    bad_manifest.write_text(json.dumps({
        "active_dataset": {"filename": "ddinter_tampered.json", "sha256": "fake_hash_1234567890"}
    }), encoding="utf-8")

    tampered_service = DDInterService(data_path=bad_data, manifest_path=bad_manifest)
    assert tampered_service.integrity_verified is False


def test_dataset_missing_or_corrupt_does_not_return_safe_summary(tmp_path):
    """Test 15: Nếu dataset bị mất hoặc rỗng, evaluation không bao giờ tự xưng 'An toàn / Không có tương tác'."""
    from app.services.ddinter_service import DDInterService
    empty_data = tmp_path / "non_existent_ddinter.json"
    broken_service = DDInterService(data_path=empty_data)

    drug1 = DrugItem(brand_name="Aspirin 81mg", active_ingredient="Aspirin", strength="81mg")
    drug2 = DrugItem(brand_name="Brufen 400mg", active_ingredient="Ibuprofen", strength="400mg")

    # Khi không có universe hoặc integrity hỏng, các thuốc chuyển thành UNAVAILABLE
    coverage_status, details = evaluation_service._evaluate_drug_coverage([drug1, drug2], dd_service=broken_service)
    # Tự động phản ánh limitation trong summary
    summary = evaluation_service._build_final_summary([], [], coverage_status, details)

    assert "CSDL tương tác thuốc DDInter không khả dụng" in summary or "Fail-Closed" in summary or "chưa có dữ liệu" in summary
    assert "Không ghi nhận bản ghi tương tác nguy hiểm" not in summary


def test_openfda_unverified_cannot_promote_ddi_coverage():
    """Test 16 (INV-12-04 / ADV-04): Ứng viên OpenFDA unverified (is_verified=False) BỊ CHẶN khỏi COVERED và DDI."""
    fda_drug = DrugItem(
        brand_name="UnverifiedBrand",
        active_ingredient="Aspirin",
        strength="81mg",
        match_method="openfda:exact",
        is_verified=False,
    )
    normal_drug = DrugItem(brand_name="Panadol", active_ingredient="Paracetamol", strength="500mg")

    resp = evaluation_service.evaluate_medications([fda_drug, normal_drug])

    # fda_drug không được chuyển thành COVERED mà phải là AMBIGUOUS_REVIEW_REQUIRED
    fda_item = next(d for d in resp.drug_coverage_details if d.drug_name == "UnverifiedBrand")
    assert fda_item.status == DrugCoverageStatus.AMBIGUOUS_REVIEW_REQUIRED
    assert resp.coverage_status == "UNRESOLVED"
    assert "chưa được xác thực" in fda_item.note


def test_manifest_active_dataset_must_exist():
    """Test 17 (ADV-03): Tệp dataset được chỉ định trong manifest.json phải thực sự tồn tại trên đĩa."""
    manifest_path = Path(__file__).parent.parent / "app" / "data" / "manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    filename = manifest["active_dataset"]["filename"]
    data_file = Path(__file__).parent.parent / "app" / "data" / filename
    assert data_file.exists() is True
    assert data_file.is_file() is True


def test_empty_or_whitespace_canonical_identifier_cannot_match_ddi():
    """Test 18 (ADV-09): Chuỗi hoạt chất rỗng, whitespace hoặc None không được lọt vào DDI lookup."""
    drug1 = DrugItem(brand_name="Ghost1", active_ingredient="   ", strength="10mg")
    drug2 = DrugItem(brand_name="Ghost2", active_ingredient="", strength="10mg")

    resp = evaluation_service.evaluate_medications([drug1, drug2])

    assert len(resp.alerts) == 0
    assert resp.coverage_status == "UNRESOLVED"
    for item in resp.drug_coverage_details:
        assert item.status == DrugCoverageStatus.UNRESOLVED


def test_duplicate_drug_input_does_not_corrupt_pair_logic():
    """Test 19 (ADV-07): Nhập cùng 1 loại thuốc nhiều lần không gây crash frozenset hoặc nhầm thành tương tác thuốc-thuốc."""
    drug1 = DrugItem(brand_name="Panadol Extra", active_ingredient="Paracetamol", strength="500mg", dosage_instruction="1 viên / 3 lần ngày")
    drug2 = DrugItem(brand_name="Panadol Extra", active_ingredient="Paracetamol", strength="500mg", dosage_instruction="1 viên / 3 lần ngày")

    resp = evaluation_service.evaluate_medications([drug1, drug2])

    # Layer 1 phát hiện trùng lặp hoạt chất
    assert any("Trùng lặp" in a.title for a in resp.alerts)
    # Layer 2 không tạo tương tác self-pair
    assert not any("Paracetamol + Paracetamol" in a.title for a in resp.alerts)


def test_identifier_case_and_whitespace_normalization():
    """Test 20: Tên hoạt chất có khoảng trắng thừa và viết hoa/thường đều hội tụ về canonical identity."""
    drug1 = DrugItem(brand_name="Aspirin Cap", active_ingredient="  ASPIRIN  ", strength="81mg")
    drug2 = DrugItem(brand_name="Brufen", active_ingredient="ibuprofen", strength="400mg")

    resp = evaluation_service.evaluate_medications([drug1, drug2])

    assert resp.coverage_status == "FULL"
    assert len(resp.alerts) > 0  # Phát hiện tương tác Aspirin + Ibuprofen
    aspirin_item = next(d for d in resp.drug_coverage_details if "Aspirin" in d.drug_name)
    assert aspirin_item.canonical_ingredient == "aspirin"
    assert aspirin_item.status == DrugCoverageStatus.COVERED


def test_mixed_covered_not_covered_with_positive_interaction():
    """Test 21 (ADV-05): 2 thuốc có tương tác + 1 thuốc un-covered -> phát hiện tương tác VÀ cảnh báo coverage."""
    # Sildenafil + Nitroglycerin (tương tác HIGH DDInter100120) + Pantoprazole (NOT_COVERED)
    drug1 = DrugItem(brand_name="Viagra 50mg", active_ingredient="Sildenafil", strength="50mg")
    drug2 = DrugItem(brand_name="Nitromint", active_ingredient="Nitroglycerin", strength="2.6mg")
    drug3 = DrugItem(brand_name="Pantoloc 40mg", active_ingredient="Pantoprazole", strength="40mg")

    resp = evaluation_service.evaluate_medications([drug1, drug2, drug3])

    assert resp.coverage_status == "PARTIAL"
    # Phát hiện được tương tác thật giữa Sildenafil và Nitroglycerin
    assert any("Sildenafil" in a.title and "Nitroglycerin" in a.title for a in resp.alerts)
    # Tóm tắt vừa nêu cảnh báo tương tác vừa nêu rõ giới hạn độ bao phủ
    assert "cảnh báo" in resp.final_summary
    assert "chưa có đủ dữ liệu" in resp.final_summary or "chưa có dữ liệu" in resp.final_summary


def test_three_drugs_pairwise_completeness():
    """Test 22 (ADV-08): Kiểm tra đầy đủ 3 cặp tương tác của 3 thuốc (A-B, A-C, B-C)."""
    # Aspirin + Ibuprofen (DDInter100101) + Warfarin (DDInter100103 + DDInter100104) -> 3 cặp đều tương tác
    drug_a = DrugItem(brand_name="Aspirin 81mg", active_ingredient="Aspirin", strength="81mg")
    drug_b = DrugItem(brand_name="Brufen 400mg", active_ingredient="Ibuprofen", strength="400mg")
    drug_c = DrugItem(brand_name="Sintrom 4mg", active_ingredient="Warfarin", strength="4mg")

    resp = evaluation_service.evaluate_medications([drug_a, drug_b, drug_c])

    assert resp.coverage_status == "FULL"
    assert len(resp.alerts) >= 3  # A-B, A-C, B-C đều có cảnh báo tương tác
    pair_mentions = [a.title for a in resp.alerts]
    assert any("Aspirin" in t and "Ibuprofen" in t for t in pair_mentions)
    assert any(("Aspirin" in t and "Warfarin" in t) or ("Warfarin + Aspirin" in t) for t in pair_mentions)
    assert any("Warfarin" in t and "Ibuprofen" in t for t in pair_mentions)


def test_openfda_case_variants_and_substring_cannot_bypass_gating():
    """Test 23 (ADV-O2): Match method dạng 'OpenFDA', 'OPENFDA:fuzzy', 'external:openfda' không thể bypass gating."""
    fda_upper = DrugItem(
        brand_name="AdversarialBrand1",
        active_ingredient="Aspirin",
        strength="81mg",
        match_method="OpenFDA:fuzzy",
        is_verified=False,
    )
    normal_drug = DrugItem(brand_name="Brufen", active_ingredient="Ibuprofen", strength="400mg")

    resp = evaluation_service.evaluate_medications([fda_upper, normal_drug])

    assert resp.coverage_status == "UNRESOLVED"
    # Không tạo cảnh báo tương tác tự động do nguồn OpenFDA unverified
    assert len(resp.alerts) == 0
    fda_item = next(d for d in resp.drug_coverage_details if d.drug_name == "AdversarialBrand1")
    assert fda_item.status == DrugCoverageStatus.AMBIGUOUS_REVIEW_REQUIRED


def test_external_match_method_unverified_fails_closed():
    """Test 24 (ADV-O3): Nguồn external match method unverified (is_verified=False) phải fail-closed."""
    fda_ext = DrugItem(
        brand_name="UncertainBrand",
        active_ingredient="Warfarin",
        strength="4mg",
        match_method="external:openfda_fallback",
        is_verified=False,
    )
    normal_drug = DrugItem(brand_name="Aspirin", active_ingredient="Aspirin", strength="81mg")

    resp = evaluation_service.evaluate_medications([fda_ext, normal_drug])
    assert resp.coverage_status == "UNRESOLVED"
    assert len(resp.alerts) == 0
    item = next(d for d in resp.drug_coverage_details if d.drug_name == "UncertainBrand")
    assert item.status == DrugCoverageStatus.AMBIGUOUS_REVIEW_REQUIRED


def test_manifest_empty_sha256_fails_closed(tmp_path):
    """Test 25: Manifest thiếu mã SHA256 hoặc rỗng phải fail-closed, không được tin cậy."""
    from app.services.ddinter_service import DDInterService
    bad_manifest = tmp_path / "manifest.json"
    bad_data = tmp_path / "ddinter.json"
    bad_manifest.write_text(json.dumps({"active_dataset": {"filename": "ddinter.json", "sha256": ""}}), encoding="utf-8")
    bad_data.write_text(json.dumps({"metadata": {}, "interactions": []}), encoding="utf-8")

    svc = DDInterService(data_path=bad_data, manifest_path=bad_manifest)
    assert svc.integrity_verified is False
    assert len(svc.get_covered_ingredients()) == 0
    assert svc.lookup_interaction("aspirin", "ibuprofen") is None


def test_tampered_dataset_locks_down_query_methods(tmp_path):
    """Test 26: Dataset sai checksum phải khóa toàn bộ lookup_interaction và find_all_interactions."""
    from app.services.ddinter_service import DDInterService
    bad_manifest = tmp_path / "manifest.json"
    bad_data = tmp_path / "ddinter.json"
    bad_manifest.write_text(json.dumps({"active_dataset": {"filename": "ddinter.json", "sha256": "0" * 64}}), encoding="utf-8")
    bad_data.write_text(json.dumps({
        "metadata": {"dataset_name": "DDInter", "dataset_version": "2.0", "license": "CC"},
        "interactions": [
            {"ddinter_id": "DDInter999", "drug_a": "aspirin", "drug_b": "ibuprofen", "severity": "HIGH", "mechanism": "m", "management": "m", "recommendation": "r"}
        ]
    }), encoding="utf-8")

    svc = DDInterService(data_path=bad_data, manifest_path=bad_manifest)
    assert svc.integrity_verified is False
    assert svc.lookup_interaction("aspirin", "ibuprofen") is None
    assert svc.find_all_interactions(["aspirin", "ibuprofen"]) == []
    assert svc.is_drug_in_universe("aspirin") is False


def test_api_evaluate_wire_contract_exposes_governance():
    """Test 27: Endpoint /api/v1/evaluate trả về đầy đủ governance fields (coverageStatus, drugCoverageDetails)."""
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from app.main import app

    client = TestClient(app)
    # Mock clinical_service.assess to skip external LLM network calls
    with patch("app.main.clinical_service.assess") as mock_assess:
        from app.schemas.ocr_schema import ClinicalAssessmentResponse
        mock_assess.return_value = ClinicalAssessmentResponse(
            drug_drug_interactions=[],
            drug_condition_interactions=[],
            overdose_duplication_alerts=[],
            clinical_recommendations=[],
        )
        resp = client.post("/api/v1/evaluate", json={
            "drugs": [{"brand_name": "GhostDrug", "active_ingredient": "GhostIng", "strength": "10mg"}]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "coverageStatus" in data
        assert data["coverageStatus"] == "UNRESOLVED"
        assert "drugCoverageDetails" in data
        assert len(data["drugCoverageDetails"]) == 1
        assert data["drugCoverageDetails"][0]["status"] == "UNRESOLVED"
        assert "provenanceMetadata" in data


