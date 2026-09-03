"""
Test Suite for Stage 13: Packaging Multi-Variant Strength Governance & Graceful Clinical Evaluation
Covers:
- Graceful degradation when drug strength is missing / empty (Layer 1-3 still work, Layer 4 skips safely)
- Unique-strength auto-defaulting (Smecta 3g, Berberin 50mg)
- Multi-variant preservation (Augmentin, Oricox, Hapacol) without unsafe blind guessing
- Non-misleading summary reporting (chống false reassurance)
- Regression test for Task 5.5 contraindication and overdose rules
"""
import pytest
from app.schemas import DrugItem, Prescription, UserProfile
from app.services.drug_database import drug_database
from app.services.normalization_service import normalization_service
from app.services.evaluation_service import evaluation_service


class TestDosageGracefulEvaluation:
    def test_drug_catalog_variants_lookup(self):
        """Kiểm tra helper get_drug_variants trả về đúng danh mục biến thể."""
        variants_augmentin = drug_database.get_drug_variants("Augmentin")
        assert "500mg" in variants_augmentin or "625mg" in variants_augmentin or "1000mg" in variants_augmentin
        assert len(variants_augmentin) >= 2

        variants_berberin = drug_database.get_drug_variants("Berberin")
        assert variants_berberin == ["50mg"]

        variants_smecta = drug_database.get_drug_variants("Smecta")
        assert variants_smecta == ["3g"]

    def test_unique_strength_auto_defaults_safely(self):
        """Thuốc chỉ có 1 quy cách duy nhất (is_unique_strength=True) được tự động điền."""
        raw_berberin = DrugItem(brand_name="Berberin", strength="")
        normalized = normalization_service.normalize_drug_item(raw_berberin)
        assert normalized.strength == "50mg"
        assert normalized.active_ingredient.lower().startswith("berberin")
        assert "50mg" in normalized.variants

    def test_multi_variant_does_not_blindly_guess_strength(self):
        """Thuốc có nhiều biến thể (Augmentin, Oricox) KHÔNG được tự ý đoán liều khi OCR trống."""
        raw_aug = DrugItem(brand_name="Augmentin", strength="")
        normalized = normalization_service.normalize_drug_item(raw_aug)
        # Giữ trống để chờ User chọn qua Variant Pills trên UI
        assert normalized.strength == ""
        # Nhưng phải cung cấp danh sách variants cho UI
        assert len(normalized.variants) >= 2
        assert any("mg" in v for v in normalized.variants)

    def test_graceful_evaluation_when_strength_is_missing(self):
        """Đánh giá lâm sàng khi tất cả thuốc đều khuyết thông tin hàm lượng (mg).
        - Layer 1 (Trùng lặp hoạt chất) VẪN PHÁT HIỆN được.
        - Layer 4 (Kiểm tra liều) bỏ qua an toàn với is_appropriate=None và note rõ ràng.
        - final_summary cảnh báo minh bạch, không kết luận 'an toàn'.
        """
        drug1 = DrugItem(
            brand_name="Panadol Vỏ Hộp Cũ",
            active_ingredient="Paracetamol",
            strength="",  # Khuyết hàm lượng
            dosage_instruction="Ngày 3 lần, mỗi lần 1 viên",
            is_verified=True,
        )
        drug2 = DrugItem(
            brand_name="Hapacol Không Rõ Hàm Lượng",
            active_ingredient="Paracetamol",
            strength="",  # Khuyết hàm lượng
            dosage_instruction="Ngày 2 lần, mỗi lần 1 viên",
            is_verified=True,
        )

        response = evaluation_service.evaluate_medications([drug1, drug2])

        # 1. Layer 1 vẫn phát hiện trùng lặp hoạt chất Paracetamol
        overdose_alerts = [a for a in response.alerts if "trùng lặp" in a.title.lower() or "quá liều" in a.title.lower()]
        assert len(overdose_alerts) > 0

        # 2. Layer 4 ghi nhận is_appropriate=None kèm note an toàn
        assert len(response.dosage_checks) == 2
        for dc in response.dosage_checks:
            assert dc.is_appropriate is None
            assert "Bao bì không ghi rõ hàm lượng" in dc.note or "bỏ qua" in dc.note.lower()

        # 3. Final summary phản ánh việc bỏ qua Layer 4 do thiếu hàm lượng
        assert "chưa đủ dữ liệu hàm lượng" in response.final_summary.lower() or "bỏ qua" in response.final_summary.lower()

    def test_regression_task_5_5_contraindication_and_overdose(self):
        """Đảm bảo không phá vỡ logic kiểm tra liều và chống chỉ định đã audit ở Task 5.5."""
        # Case A: Paracetamol quá ngưỡng 4000mg/ngày
        drug_overdose = DrugItem(
            brand_name="Panadol 500mg",
            active_ingredient="Paracetamol",
            strength="500mg",
            dosage_instruction="Ngày uống 5 lần, mỗi lần 2 viên",  # 500 * 2 * 5 = 5000mg > 4000mg
            is_verified=True,
        )
        res = evaluation_service.evaluate_medications([drug_overdose])
        dc = res.dosage_checks[0]
        assert dc.is_appropriate is False
        assert "vuot khuyen cao" in dc.note.lower() or "vượt khuyến cáo" in dc.note.lower()

        # Case B: Metformin + suy thận -> contraindication tag
        user_renal = UserProfile(age=55, conditions=["Suy thận mạn tính"])
        drug_metformin = DrugItem(
            brand_name="Glucophage 500mg",
            active_ingredient="Metformin",
            strength="500mg",
            dosage_instruction="Ngày 2 lần, mỗi lần 1 viên",
            is_verified=True,
        )
        res_renal = evaluation_service.evaluate_medications([drug_metformin], user_profile=user_renal)
        dc_renal = res_renal.dosage_checks[0]
        assert dc_renal.is_appropriate is None
        assert "chống chỉ định" in dc_renal.note.lower() or "suy thận" in dc_renal.note.lower()
