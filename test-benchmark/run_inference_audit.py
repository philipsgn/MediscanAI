"""
Inference Test & Clinical OCR Audit Script for Sample Images
Target directory: ai/benchmark/ocr_models/sample_images
"""
import sys
import os
import time
import json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project roots
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("backend"))
sys.path.insert(0, os.path.abspath("ai"))

import cv2
import numpy as np
from PIL import Image

from ai.pipelines.onnx_ocr_engine import default_onnx_ocr_engine
from ai.normalization.drug_mapper import default_drug_mapper
from ai.pipelines.clinical_ner_parser import default_ner_parser
from backend.app.services.drug_database import drug_database
from backend.app.services.normalization_service import normalization_service
from backend.app.schemas import DrugItem

SAMPLE_DIR = Path("ai/benchmark/ocr_models/sample_images")

def run_test():
    image_files = sorted([f for f in SAMPLE_DIR.iterdir() if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]])
    print(f"================================================================================")
    print(f"MEDISCAN AI — SENIOR TESTER INFERENCE AUDIT ({len(image_files)} sample images)")
    print(f"================================================================================")

    results = []

    for idx, img_path in enumerate(image_files, 1):
        print(f"\n[{idx}/{len(image_files)}] TESTING IMAGE: {img_path.name}")
        file_size_kb = round(img_path.stat().st_size / 1024, 1)

        # Read image to get dims
        with Image.open(img_path) as img:
            w, h = img.size

        print(f"  • File: {img_path.name} | Size: {file_size_kb} KB | Dimensions: {w}x{h}")

        # Choose stream type based on filename
        stream_type = "prescription" if "toa" in img_path.name.lower() else "packaging"
        print(f"  • Pipeline Stream: {stream_type.upper()}")

        # Read bytes
        with open(img_path, "rb") as f:
            image_bytes = f.read()

        t0 = time.perf_counter()
        try:
            doc_out = default_onnx_ocr_engine.process_document(image_bytes, source_stream=stream_type)
            latency_ms = int(round((time.perf_counter() - t0) * 1000))

            raw_lines = doc_out.get("raw_ocr_lines", [])
            extracted_drugs = doc_out.get("extracted_drugs", [])
            metrics = doc_out.get("metrics", {})

            print(f"  • Latency: {latency_ms} ms (Preproc: {metrics.get('preprocessor_ms', 0)}ms, OCR: {metrics.get('ocr_inference_ms', 0)}ms)")
            print(f"  • Raw Text Lines Count: {len(raw_lines)}")

            # Display raw text lines
            print("  • Sample Raw OCR Lines (top 8):")
            for line in raw_lines[:8]:
                txt = line.get("text", "")
                conf = line.get("confidence", 0.0)
                print(f"      - \"{txt}\" (conf: {conf:.2f})")
            if len(raw_lines) > 8:
                print(f"      ... and {len(raw_lines) - 8} more lines")

            # Map to Drug Database / Normalization
            mapped_candidates = []
            for line in raw_lines:
                txt = line.get("text", "")
                if len(txt) >= 3:
                    # Test against backend NormalizationService
                    raw_drug = DrugItem(brand_name=txt, strength="")
                    norm_drug = normalization_service.normalize_drug_item(raw_drug)
                    if norm_drug.active_ingredient:
                        mapped_candidates.append({
                            "raw_text": txt,
                            "matched_brand": norm_drug.brand_name,
                            "active_ingredient": norm_drug.active_ingredient,
                            "strength": norm_drug.strength,
                            "variants": norm_drug.variants,
                            "confidence": norm_drug.confidence_score,
                            "match_method": norm_drug.match_method,
                        })

            print(f"  • Verified Drug Matches in Local DB: {len(mapped_candidates)}")
            for m in mapped_candidates:
                print(f"      ★ RAW: \"{m['raw_text']}\" -> BRAND: \"{m['matched_brand']}\" | INGREDIENT: {m['active_ingredient']} | STRENGTH: {m['strength']} | METHOD: {m['match_method']} (conf: {m['confidence']})")

            results.append({
                "image": img_path.name,
                "size_kb": file_size_kb,
                "dimensions": f"{w}x{h}",
                "stream": stream_type,
                "latency_ms": latency_ms,
                "raw_lines_count": len(raw_lines),
                "raw_lines": [l.get("text", "") for l in raw_lines],
                "matches": mapped_candidates
            })

        except Exception as e:
            print(f"  [ERROR] Failed to process {img_path.name}: {e}")
            import traceback
            traceback.print_exc()

    # Save summary json
    out_json = Path("test-benchmark/inference_audit_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "="*80)
    print(f"Audit completed! Output saved to: {out_json}")
    print("="*80)

if __name__ == "__main__":
    run_test()
