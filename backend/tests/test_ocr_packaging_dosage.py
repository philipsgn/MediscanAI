"""Unit tests cho Stage 2 Priority 2 — chống dosage_instruction rò vào Pipeline 1 (packaging).

Kiến trúc (ARCHITECTURE.md §3 / AGENTS.md B.1):
  - User Pipeline 1 (Vỏ hộp / Lọ thuốc): liều dùng PHẢI do User nhập tay ở Smart Form.
    OCR/mapper không bao giờ tự động gán dosage_instruction cho pipeline này.
  - User Pipeline 2 (Toa thuốc / Receipt): dosage_instruction được bổ sung ở Stage 3
    Normalization nếu text toa chứa hướng dẫn liều dùng.
"""
import types

import pytest

from app.api.v1.endpoints.ocr import _ocr_items_to_drug_items


def _stub(text: str, confidence: float = 0.9) -> types.SimpleNamespace:
    """OCRItem giả lập (chỉ cần .text/.confidence/.box)."""
    return types.SimpleNamespace(text=text, confidence=confidence, box=[0.0, 0.0, 0.0, 0.0])


def test_ocr_packaging_no_dosage_leak():
    """Pipeline 1 (packaging): dù OCR trả về dòng trông giống hướng dẫn liều dùng,
    dosage_instruction PHẢI luôn là None — ngăn chặn Normalization Stage 3 vô tình
    điền dosage cho vỏ hộp trong tương lai."""
    raw = [
        _stub("Paracetamol 500mg"),
        _stub("Uong 1 vien x 3 lan/ngay sau an"),  # text giống dosage instruction
        _stub("2 vien/lan"),
    ]
    items = _ocr_items_to_drug_items(raw, source_type="packaging")
    # 3 dòng đều chứa chữ cái -> đều được seed thành DrugItem
    assert len(items) == 3
    for drug in items:
        assert drug.dosage_instruction is None, (
            "dosage_instruction rò vào Pipeline 1 (packaging) — vi phạm kiến trúc"
        )


def test_ocr_prescription_route_allows_none_for_ocritem():
    """Pipeline 2 (prescription): OCRItem hiện chưa mang dosage, nên mặc định None.
    Test này khẳng định hành vi hiện tại — dosage sẽ được Normalization bổ sung sau."""
    raw = [_stub("Aspirin 100mg"), _stub("Uong 1 vien x 1 lan/ngay")]
    items = _ocr_items_to_drug_items(raw, source_type="prescription")
    assert len(items) == 2
    for drug in items:
        # OCRItem không có dosage_attribute -> getattr trả về None (được bổ sung Stage 3)
        assert drug.dosage_instruction is None


def test_ocr_packaging_filters_non_alpha():
    """Các dòng toàn số (không chữ cái) phải bị lọc — không seed thành DrugItem."""
    raw = [_stub("123.45"), _stub("***"), _stub("DrugX 10mg")]
    items = _ocr_items_to_drug_items(raw, source_type="packaging")
    assert len(items) == 1
    assert items[0].brand_name == "DrugX 10mg"
    assert items[0].dosage_instruction is None


def test_ocr_empty_and_short_text_filtered():
    """Dòng rỗng/rtrim quá ngắn (< 2 ký tự) phải được bỏ qua."""
    raw = [_stub(""), _stub(" "), _stub("x")]
    items = _ocr_items_to_drug_items(raw, source_type="packaging")
    assert items == []
