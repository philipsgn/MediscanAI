"""Medical OCR Product Name Extraction QA Audit (Senior Test Engineer).

Evaluates exact and fuzzy extraction of DRUG PRODUCT NAMES across 4 image formats:
1. hop-thuoc.jpg (Box)
2. lo-thuoc.png (Bottle)
3. vi-thuoc.jpg (Blister)
4. toa-thuoc.jpg (Prescription - 6 drugs)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from ground_truth import _levenshtein_distance

# Ground truth definition for Drug Product Names
PRODUCT_NAME_GROUND_TRUTH = {
    "hop-thuoc.jpg": {
        "format": "Hộp thuốc (Box packaging)",
        "products": [
            {
                "brand_name": "ACRETIN",
                "full_product_name": "ACRETIN 0.05%",
                "strength": "0.05%",
                "active_ingredient": "Tretinoin",
                "notes": "Hộp kem bôi Acretin 0.05% (Jamjoom Pharma)"
            }
        ]
    },
    "lo-thuoc.png": {
        "format": "Lọ thuốc (Bottle packaging)",
        "products": [
            {
                "brand_name": "ALA-Bio",
                "full_product_name": "ALA-Bio",
                "strength": "",
                "active_ingredient": "5-ALA (5-Amino Levulinic Acid)",
                "notes": "Lọ thực phẩm bảo vệ sức khỏe ALA-Bio"
            }
        ]
    },
    "vi-thuoc.jpg": {
        "format": "Vỉ thuốc (Blister packaging)",
        "products": [
            {
                "brand_name": "tendoactive",
                "full_product_name": "tendoactive",
                "strength": "",
                "active_ingredient": "Mucopolysaccharides + Collagen type I",
                "notes": "Vỉ viên nang Tendoactive (Bioiberica)"
            }
        ]
    },
    "toa-thuoc.jpg": {
        "format": "Toa thuốc (Prescription)",
        "products": [
            {
                "brand_name": "Augmentin",
                "full_product_name": "Augmentin 625mg",
                "strength": "625mg",
                "active_ingredient": "Amoxicillin + Clavulanic acid",
                "notes": "Thuốc 1 trên toa"
            },
            {
                "brand_name": "Medrol",
                "full_product_name": "Medrol 16mg",
                "strength": "16mg",
                "active_ingredient": "Methylprednisolone",
                "notes": "Thuốc 2 trên toa"
            },
            {
                "brand_name": "Ibuprofen",
                "full_product_name": "Ibuprofen 400mg",
                "strength": "400mg",
                "active_ingredient": "Ibuprofen",
                "notes": "Thuốc 3 trên toa"
            },
            {
                "brand_name": "Alphachymotrysin",
                "full_product_name": "Alphachymotrysin 4,2mg",
                "strength": "4,2mg",
                "active_ingredient": "Chymotrypsin",
                "notes": "Thuốc 4 trên toa (Chính tả trên ảnh là Alphachymotrysin 4,2mg)"
            },
            {
                "brand_name": "Paracetamol",
                "full_product_name": "Paracetamol 500mg",
                "strength": "500mg",
                "active_ingredient": "Paracetamol",
                "notes": "Thuốc 5 trên toa"
            },
            {
                "brand_name": "Omeprazol",
                "full_product_name": "Omeprazol 20mg",
                "strength": "20mg",
                "active_ingredient": "Omeprazol",
                "notes": "Thuốc 6 trên toa"
            }
        ]
    }
}


def fuzzy_similarity(s1: str, s2: str) -> float:
    """Compute normalized Levenshtein similarity between 0.0 and 1.0 (alphanumeric clean)."""
    s1_clean = "".join(c.lower() for c in s1 if c.isalnum())
    s2_clean = "".join(c.lower() for c in s2 if c.isalnum())
    if not s1_clean and not s2_clean:
        return 1.0
    if not s1_clean or not s2_clean:
        return 0.0
    dist = _levenshtein_distance(s1_clean, s2_clean)
    max_len = max(len(s1_clean), len(s2_clean))
    return 1.0 - (dist / max_len)


def evaluate_extracted_text(extracted_lines: list[str], expected_products: list[dict[str, str]]):
    """Evaluate product name matches in extracted lines."""
    full_text = " ".join(extracted_lines)
    full_text_lower = full_text.lower()
    
    results = []
    for prod in expected_products:
        brand = prod["brand_name"]
        full_name = prod["full_product_name"]
        
        # 1. Exact match check
        exact_brand = brand.lower() in full_text_lower
        exact_full = full_name.lower() in full_text_lower
        
        # 2. Best fuzzy similarity across extracted lines
        best_sim_brand = 0.0
        best_match_line = ""
        for line in extracted_lines:
            # Check substrings of line of similar length
            words = line.split()
            for w in words:
                sim = fuzzy_similarity(w, brand)
                if sim > best_sim_brand:
                    best_sim_brand = sim
                    best_match_line = line
            # Also check whole line
            sim_line = fuzzy_similarity(line, brand)
            if sim_line > best_sim_brand:
                best_sim_brand = sim_line
                best_match_line = line
                
        # Classify
        if exact_full:
            status = "EXACT_FULL_MATCH"
        elif exact_brand:
            status = "EXACT_BRAND_MATCH"
        elif best_sim_brand >= 0.80:
            status = f"FUZZY_MATCH ({best_sim_brand*100:.1f}%)"
        else:
            status = "MISSED_OR_MISIDENTIFIED"
            
        results.append({
            "brand": brand,
            "full_name": full_name,
            "exact_brand": exact_brand,
            "exact_full": exact_full,
            "best_sim": round(best_sim_brand, 3),
            "best_match_line": best_match_line,
            "status": status
        })
    return results


def run_audit():
    results_dir = Path(__file__).resolve().parent.parent / "results"
    with open(results_dir / "pretrained_baseline_report.json", encoding="utf-8") as f:
        baseline = json.load(f)
        
    print("=" * 85)
    print("🔬 SENIOR MEDICAL OCR QA AUDIT: DRUG PRODUCT NAME EXTRACTION (4 FORMATS)")
    print("=" * 85)
    
    audit_summary = []
    
    for img_name, meta in PRODUCT_NAME_GROUND_TRUTH.items():
        format_name = meta["format"]
        expected_products = meta["products"]
        total_drugs = len(expected_products)
        
        print(f"\n─────────────────────────────────────────────────────────────────────────────")
        print(f"📁 [{format_name.upper()}] - {img_name} ({total_drugs} thuốc mục tiêu)")
        print(f"─────────────────────────────────────────────────────────────────────────────")
        
        # PP-OCR (Packaging Stream / P1)
        base_p1 = next((r for r in baseline["results"] if r["image"] == img_name and r["pipeline"] == "packaging"), None)
        p1_lines = base_p1["text_extracted"].split("\n") if base_p1 else []
        p1_res = evaluate_extracted_text(p1_lines, expected_products)
        
        # VietOCR (Prescription Stream / P2)
        base_p2 = next((r for r in baseline["results"] if r["image"] == img_name and r["pipeline"] == "prescription"), None)
        p2_lines = base_p2["text_extracted"].split("\n") if base_p2 else []
        p2_res = evaluate_extracted_text(p2_lines, expected_products)
        
        p1_exact_count = sum(1 for r in p1_res if r["exact_brand"])
        p1_fuzzy_count = sum(1 for r in p1_res if r["exact_brand"] or r["best_sim"] >= 0.80)
        
        p2_exact_count = sum(1 for r in p2_res if r["exact_brand"])
        p2_fuzzy_count = sum(1 for r in p2_res if r["exact_brand"] or r["best_sim"] >= 0.80)
        
        print(f"  [PP-OCR Pipeline]: Exact Matches: {p1_exact_count}/{total_drugs} ({p1_exact_count/total_drugs*100:.1f}%), Fuzzy (>=80%): {p1_fuzzy_count}/{total_drugs} ({p1_fuzzy_count/total_drugs*100:.1f}%)")
        for r in p1_res:
            print(f"    • {r['full_name']} -> Status: [{r['status']}] (Line: '{r['best_match_line']}')")
            
        print(f"\n  [VietOCR Pipeline]: Exact Matches: {p2_exact_count}/{total_drugs} ({p2_exact_count/total_drugs*100:.1f}%), Fuzzy (>=80%): {p2_fuzzy_count}/{total_drugs} ({p2_fuzzy_count/total_drugs*100:.1f}%)")
        for r in p2_res:
            print(f"    • {r['full_name']} -> Status: [{r['status']}] (Line: '{r['best_match_line']}')")
            
        audit_summary.append({
            "format": format_name,
            "image": img_name,
            "total_drugs": total_drugs,
            "p1_exact": p1_exact_count,
            "p1_fuzzy": p1_fuzzy_count,
            "p2_exact": p2_exact_count,
            "p2_fuzzy": p2_fuzzy_count,
        })
        
    return audit_summary


if __name__ == "__main__":
    run_audit()
