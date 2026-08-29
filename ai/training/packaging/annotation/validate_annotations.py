"""Enforce annotation schema, score/status rules, and image-label pairing."""
from __future__ import annotations
import argparse, json, math
from pathlib import Path

def validate(annotation_file: Path, output_root: Path | None = None) -> dict[str, int]:
    result = {"records": 0, "invalid": 0, "accepted": 0, "review": 0, "rejected": 0}
    with annotation_file.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip(): continue
            result["records"] += 1
            try:
                record = json.loads(line); status = record["status"]; scores = [float(record[key]) for key in ("ocr_score", "match_score", "annotation_score")]
                if status not in {"accepted", "review", "rejected"} or any(not math.isfinite(score) or score < 0 or score > 1 for score in scores): raise ValueError
                if status == "accepted" and record["annotation_score"] < .85: raise ValueError
                if status == "review" and not .65 <= record["annotation_score"] < .85: raise ValueError
                if status == "rejected" and record["annotation_score"] >= .65: raise ValueError
                if not isinstance(record.get("ocr"), list): raise ValueError
                for item in record["ocr"]:
                    box = item["bbox"]
                    if len(box) != 4 or any(not math.isfinite(float(value)) for value in box) or not item.get("text"): raise ValueError
                if output_root is not None:
                    image = output_root / "images" / record["filename"]; label = output_root / "labels" / f"{record['image_id']}.txt"
                    if status == "accepted" and (not image.is_file() or not label.is_file() or label.stem != Path(record["filename"]).stem): raise ValueError
                    if image.is_file():
                        from PIL import Image
                        with Image.open(image) as opened: image_width, image_height = opened.size
                        for item in record["ocr"]:
                            x1, y1, x2, y2 = [float(value) for value in item["bbox"]]
                            if not (0 <= x1 <= x2 <= image_width and 0 <= y1 <= y2 <= image_height): raise ValueError
                    if not label.is_file(): continue
                    for label_line in label.read_text(encoding="ascii").splitlines():
                        values = label_line.split()
                        if len(values) != 5 or int(values[0]) not in range(3) or any(not 0 <= float(value) <= 1 for value in values[1:]): raise ValueError
                result[status] += 1
            except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError): result["invalid"] += 1
    return result

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("annotations", type=Path); parser.add_argument("--output-root", type=Path); args = parser.parse_args(); result = validate(args.annotations, args.output_root); print(json.dumps(result, sort_keys=True)); raise SystemExit(1 if result["invalid"] else 0)
if __name__ == "__main__": main()
