"""Create reviewable YOLO annotations from real-image metadata and local OCR."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from ai.training.packaging.annotation.ocr_engine import OCRResult, OCREngine
from ai.training.packaging.annotation.text_matching import load_dictionary, normalize_text

CLASSES = ("brand_name", "active_ingredient", "strength")


def _similar(left: str, right: str) -> float:
    from difflib import SequenceMatcher
    return SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def _merge_lines(results: list[OCRResult]) -> list[OCRResult]:
    """Join nearby words on the same line without joining vertically separate fields."""
    words = sorted((item for item in results if item.text and item.bbox[2] > item.bbox[0]), key=lambda item: (item.bbox[1], item.bbox[0]))
    lines: list[list[OCRResult]] = []
    for word in words:
        x1, y1, x2, y2 = word.bbox
        target = next((line for line in reversed(lines) if abs(y1 - line[-1].bbox[1]) <= max(y2 - y1, line[-1].bbox[3] - line[-1].bbox[1]) * 0.6 and x1 - line[-1].bbox[2] <= max(80, (x2 - x1) * 2)), None)
        if target is None: lines.append([word])
        else: target.append(word)
    merged: list[OCRResult] = []
    for line in lines:
        line.sort(key=lambda item: item.bbox[0]); x1 = min(item.bbox[0] for item in line); y1 = min(item.bbox[1] for item in line); x2 = max(item.bbox[2] for item in line); y2 = max(item.bbox[3] for item in line)
        merged.append(OCRResult(" ".join(item.text for item in line), sum(item.confidence for item in line) / len(line), (x1, y1, x2, y2)))
    return merged


def _yolo(box: tuple[int, int, int, int], width: int, height: int) -> str:
    x1, y1, x2, y2 = box; box_width, box_height = x2 - x1, y2 - y1
    return f"{{class_id}} {(x1 + x2) / 2 / width:.6f} {(y1 + y2) / 2 / height:.6f} {box_width / width:.6f} {box_height / height:.6f}"


def annotate(metadata: Path, output_root: Path, review_path: Path | None = None, resume: bool = True, include_nonaccepted: bool = False, dictionary: Path | None = None) -> dict[str, int]:
    engine = OCREngine(); output_images = output_root / "images"; output_labels = output_root / "labels"; output_images.mkdir(parents=True, exist_ok=True); output_labels.mkdir(parents=True, exist_ok=True)
    done = {path.stem for path in output_labels.glob("*.txt")} if resume else set(); stats = {"accepted": 0, "review": 0, "rejected": 0}; reviews: list[dict[str, object]] = []
    dictionary_by_id = {str(item.get("id")): item for item in load_dictionary(dictionary)} if dictionary and dictionary.exists() else {}
    rejected: list[dict[str, object]] = []
    with metadata.open(encoding="utf-8") as source:
        for line in source:
            if not line.strip(): continue
            record = json.loads(line); image_id = str(record["image_id"])
            if image_id in done: continue
            image_path = Path(record.get("path", record["filename"])); results = _merge_lines(engine.extract(image_path))
            product = dictionary_by_id.get(str(record.get("drug_id")), {})
            aliases = list(record.get("aliases", [])) + list(product.get("aliases", []))
            fields = {"brand_name": [record.get("brand_name", "")] + aliases, "active_ingredient": record.get("active_ingredient", []) or product.get("active_ingredient", []), "strength": record.get("strength", []) or product.get("strength", [])}; matches: dict[str, tuple[OCRResult, float]] = {}
            for field, expected in fields.items():
                expected_values = expected if isinstance(expected, list) else [expected]
                expected_values = [str(value) for value in expected_values if value]
                if not expected_values: continue
                candidate = max(results, key=lambda item: max((_similar(item.text, value) for value in expected_values), default=0.0), default=None)
                score = max(_similar(candidate.text, value) for value in expected_values) if candidate is not None else 0.0
                if candidate is not None and candidate.confidence >= 0.70 and score >= 0.80: matches[field] = (candidate, score)
            ocr_score = sum(item.confidence for item in results) / len(results) if results else 0.0; match_score = sum(score for _, score in matches.values()) / len(fields) if fields else 0.0; annotation_score = round(ocr_score * .45 + match_score * .55, 4)
            status = "accepted" if annotation_score >= .85 and len(matches) >= 1 else "review" if annotation_score >= .65 else "rejected"; stats[status] += 1
            try:
                from PIL import Image
                with Image.open(image_path) as image: width, height = image.size
            except (ImportError, OSError): width = height = 1
            label_lines = []
            for class_id, field in enumerate(CLASSES):
                if field in matches:
                    label_lines.append(_yolo(matches[field][0].bbox, width, height).format(class_id=class_id))
            if status == "accepted" or include_nonaccepted:
                target_image = output_images / image_path.name; target_image.write_bytes(image_path.read_bytes()); (output_labels / f"{image_id}.txt").write_text("\n".join(label_lines) + ("\n" if label_lines else ""), encoding="ascii")
            else:
                target_image = image_path
            annotation = {"image_id": image_id, "filename": target_image.name, "drug_id": record.get("drug_id"), "group_id": record.get("group_id", record.get("drug_id", image_id)), "ocr_score": round(ocr_score, 4), "match_score": round(match_score, 4), "annotation_score": annotation_score, "status": status, "ocr": [{"text": item.text, "confidence": item.confidence, "bbox": list(item.bbox)} for item in results], "matched_fields": list(matches)}
            if status == "review": reviews.append(annotation)
            if status == "rejected": rejected.append(annotation)
            with (output_root / "annotations.jsonl").open("a", encoding="utf-8") as annotation_file:
                annotation_file.write(json.dumps(annotation, ensure_ascii=False, sort_keys=True) + "\n")
    if review_path: review_path.parent.mkdir(parents=True, exist_ok=True); review_path.write_text(json.dumps(reviews, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); review_path.with_name("rejected.json").write_text(json.dumps(rejected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--metadata", type=Path, required=True); parser.add_argument("--output", type=Path, default=Path("ai/training/packaging/datasets/annotated_real")); parser.add_argument("--review-list", type=Path, default=Path("ai/training/packaging/datasets/metadata/review.json")); parser.add_argument("--dictionary", type=Path, default=Path("ai/training/packaging/drug_dictionary.json")); parser.add_argument("--include-nonaccepted", action="store_true"); parser.add_argument("--no-resume", action="store_true"); args = parser.parse_args(); print(json.dumps(annotate(args.metadata, args.output, args.review_list, not args.no_resume, args.include_nonaccepted, args.dictionary), sort_keys=True))
if __name__ == "__main__": main()
