"""Validate YOLO image/label pairs and emit a JSON report."""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from ai.training.packaging.data_scrapers.utils import validate_image

def validate(root: Path, classes: int = 3) -> dict[str, object]:
    report: dict[str, object] = {"images": 0, "valid": 0, "invalid": 0, "missing_labels": 0, "bad_labels": 0, "splits": {}}
    for split in ("train", "val", "test"):
        image_dir, label_dir = root / "images" / split, root / "labels" / split
        split_count = 0
        for image in sorted(image_dir.glob("*")) if image_dir.exists() else []:
            if image.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
                continue
            report["images"] = int(report["images"]) + 1; split_count += 1
            try: validate_image(image)
            except ValueError: report["invalid"] = int(report["invalid"]) + 1; continue
            label = label_dir / f"{image.stem}.txt"
            if not label.exists(): report["missing_labels"] = int(report["missing_labels"]) + 1; continue
            try:
                for line in label.read_text(encoding="ascii").splitlines():
                    fields = line.split(); values = [float(v) for v in fields[1:]]
                    if len(fields) != 5 or int(fields[0]) not in range(classes) or len(values) != 4 or any(v < 0 or v > 1 for v in values): raise ValueError
                report["valid"] = int(report["valid"]) + 1
            except (OSError, ValueError): report["bad_labels"] = int(report["bad_labels"]) + 1
        report["splits"][split] = split_count  # type: ignore[index]
    report["invalid"] = int(report["invalid"]) + int(report["missing_labels"]) + int(report["bad_labels"])
    return report

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("root", type=Path); parser.add_argument("--report", type=Path); args = parser.parse_args()
    result = validate(args.root); text = json.dumps(result, indent=2, sort_keys=True); print(text)
    if args.report: args.report.write_text(text + "\n", encoding="utf-8")
    if result["invalid"]: raise SystemExit(1)
if __name__ == "__main__": main()
