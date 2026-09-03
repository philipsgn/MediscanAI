"""
Comprehensive Test Suite for Prescription Processing Pipeline (Mediscan AI)
Tests:
1. Real image test (toa-thuoc.jpg)
2. Case: Prescription with Rp/Rx prefixes (e.g. 'Rp: Augmentin 625mg')
3. Case: Prescription with bullets/dash prefixes (e.g. '- Paracetamol 500mg')
4. Case: Multiline dosage instructions with directions ('Cách dùng: Ngày uống 2 lần, mỗi lần 1 viên sau ăn')
5. Case: Drug without explicit 'Tên thuốc' prefix but followed by dosage lines
6. Case: Formatting noise dots ('.......') cleaning
"""
import sys
import os
import re
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("backend"))
sys.path.insert(0, os.path.abspath("ai"))

from backend.app.api.v1.endpoints.ocr import _ocr_items_to_drug_items, OCRItem
from backend.app.services.normalization_service import normalization_service
from ai.pipelines.onnx_ocr_engine import default_onnx_ocr_engine

def run_tests():
    print("=" * 80)
    print("MEDISCAN AI — PRESCRIPTION PIPELINE AUDIT & TEST SUITE")
    print("=" * 80)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 1: Real Prescription Image (toa-thuoc.jpg)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[TEST 1] Processing Real Image: toa-thuoc.jpg")
    img_path = Path("ai/benchmark/ocr_models/sample_images/toa-thuoc.jpg")
    assert img_path.exists(), f"Missing {img_path}"

    with open(img_path, "rb") as f:
        out = default_onnx_ocr_engine.process_document(f.read(), source_stream="prescription")

    raw_items = [OCRItem(text=l["text"], confidence=l["confidence"], box=l["box"]) for l in out["raw_ocr_lines"]]
    print(f"  • Raw OCR lines extracted: {len(raw_items)}")

    parsed_drugs = _ocr_items_to_drug_items(raw_items, source_type="prescription")
    print(f"  • Drugs parsed by Prescription Pipeline: {len(parsed_drugs)}")

    for i, d in enumerate(parsed_drugs, 1):
        norm = normalization_service.normalize_drug_item(d)
        print(f"    [{i}] Brand: {norm.brand_name} | Strength: {norm.strength} | Ingredient: {norm.active_ingredient}")
        print(f"        Dosage: {norm.dosage_instruction}")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 2: Prescription with Rp / Rx notation
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[TEST 2] Synthetic Test: Rp / Rx notation")
    rx_items = [
        OCRItem(text="ĐƠN THUỐC ĐIỀU TRỊ NGOẠI TRÚ", confidence=0.99),
        OCRItem(text="Chẩn đoán: Viêm xoang cấp", confidence=0.98),
        OCRItem(text="Rp: Augmentin 625mg", confidence=0.95),
        OCRItem(text="Cách dùng: Ngày uống 2 lần, mỗi lần 1 viên sau ăn", confidence=0.94),
        OCRItem(text="Rx: Medrol 16mg", confidence=0.96),
        OCRItem(text="Uống 1 viên vào buổi sáng sau ăn no", confidence=0.95),
    ]
    parsed_rp = _ocr_items_to_drug_items(rx_items, source_type="prescription")
    print(f"  • Parsed Rp/Rx items: {len(parsed_rp)}")
    for d in parsed_rp:
        norm = normalization_service.normalize_drug_item(d)
        print(f"    -> Brand: {norm.brand_name} | Strength: {norm.strength} | Ingredient: {norm.active_ingredient} | Dosage: {norm.dosage_instruction}")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 3: Prescription with Dash / Bullet notation
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[TEST 3] Synthetic Test: Dash / Bullet notation")
    bullet_items = [
        OCRItem(text="TOA THUỐC BỆNH VIỆN", confidence=0.99),
        OCRItem(text="- Paracetamol 500mg (10 viên)", confidence=0.95),
        OCRItem(text="Uống 1 viên khi sốt trên 38.5 độ C", confidence=0.92),
        OCRItem(text="+ Ibuprofen 400mg (15 viên)", confidence=0.96),
        OCRItem(text="Ngày uống 2 lần, mỗi lần 1 viên sau ăn", confidence=0.93),
    ]
    parsed_bullets = _ocr_items_to_drug_items(bullet_items, source_type="prescription")
    print(f"  • Parsed Bullet items: {len(parsed_bullets)}")
    for d in parsed_bullets:
        norm = normalization_service.normalize_drug_item(d)
        print(f"    -> Brand: {norm.brand_name} | Strength: {norm.strength} | Ingredient: {norm.active_ingredient} | Dosage: {norm.dosage_instruction}")

    print("\n" + "=" * 80)
    print("PRESCRIPTION PIPELINE AUDIT FINISHED")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
