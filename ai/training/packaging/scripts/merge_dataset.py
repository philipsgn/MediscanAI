"""Merge annotated real and synthetic roots with target source ratios."""
from __future__ import annotations
import argparse, hashlib, json, shutil, sys
from pathlib import Path
if __package__ in (None, ""): sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

def merge(real: Path, synthetic: Path, output: Path, real_ratio: float = .3, synthetic_ratio: float = .7) -> dict[str, object]:
    if not 0 <= real_ratio <= 1 or not 0 <= synthetic_ratio <= 1: raise ValueError("ratios must be between zero and one")
    output_images, output_labels = output / "images" / "all", output / "labels" / "all"; output_images.mkdir(parents=True, exist_ok=True); output_labels.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set(); result: dict[str, object] = {"real_images": 0, "synthetic_images": 0, "total_images": 0, "duplicates": 0, "real_ratio": 0.0, "synthetic_ratio": 0.0, "manifest": []}
    pools: dict[str, list[Path]] = {"real": sorted(path for path in (real / "images").glob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}), "synthetic": sorted(path for path in (synthetic / "images").glob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"})}
    available = {name: len(paths) for name, paths in pools.items()}; capacity = min(available["real"] / real_ratio if real_ratio else float("inf"), available["synthetic"] / synthetic_ratio if synthetic_ratio else float("inf")); target_total = round(capacity) if capacity != float("inf") else max(available.values())
    if not available["real"] or not available["synthetic"]:
        wanted = {"real": available["real"], "synthetic": available["synthetic"]}
    else:
        wanted = {"real": min(available["real"], round(target_total * real_ratio)), "synthetic": min(available["synthetic"], round(target_total * synthetic_ratio))}
    # If a source is too small, retain all of it and use the other source rather than truncating it.
    if available["real"] < wanted["real"]: wanted["real"] = available["real"]
    if available["synthetic"] < wanted["synthetic"]: wanted["synthetic"] = available["synthetic"]
    for name, root in (("real", real), ("synthetic", synthetic)):
        for image in pools[name][: wanted[name]]:
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            if digest in seen: result["duplicates"] = int(result["duplicates"]) + 1; continue
            seen.add(digest); destination_name = f"{name}_{image.name}"; shutil.copy2(image, output_images / destination_name); label = root / "labels" / f"{image.stem}.txt"
            if label.exists(): shutil.copy2(label, output_labels / f"{Path(destination_name).stem}.txt")
            result[f"{name}_images"] = int(result[f"{name}_images"]) + 1; result["manifest"].append({"filename": destination_name, "source": name, "sha256": digest})  # type: ignore[union-attr]
    result["total_images"] = int(result["real_images"]) + int(result["synthetic_images"])
    if result["total_images"]:
        result["real_ratio"] = round(int(result["real_images"]) / int(result["total_images"]), 4); result["synthetic_ratio"] = round(int(result["synthetic_images"]) / int(result["total_images"]), 4)
    (output / "merge_manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8"); return result

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--real", required=True, type=Path); parser.add_argument("--synthetic", required=True, type=Path); parser.add_argument("--output", default=Path("ai/training/packaging/datasets/final"), type=Path); parser.add_argument("--real-ratio", type=float, default=.3); parser.add_argument("--synthetic-ratio", type=float, default=.7); parser.add_argument("--report", type=Path); args = parser.parse_args(); result = merge(args.real, args.synthetic, args.output, args.real_ratio, args.synthetic_ratio); report = args.report or args.output / "merge_report.json"; report.parent.mkdir(parents=True, exist_ok=True); report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8"); print(json.dumps({key: value for key, value in result.items() if key != "manifest"}, sort_keys=True))
if __name__ == "__main__": main()
