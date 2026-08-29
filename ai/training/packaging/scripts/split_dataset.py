"""Split a merged dataset by product group, preserving target ratios."""
from __future__ import annotations
import argparse, hashlib, json, random, shutil, sys
from pathlib import Path
if __package__ in (None, ""): sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

def split(source: Path, output: Path, metadata: Path | None = None, ratios: tuple[float, float, float] = (.8, .2, 0.0), seed: int = 42) -> dict[str, int]:
    if abs(sum(ratios) - 1) > .001: raise ValueError("split ratios must total one")
    records = {}
    if metadata and metadata.exists():
        for line in metadata.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line); records[item.get("filename", item.get("image_id"))] = item
    groups: dict[str, list[Path]] = {}
    for image in sorted((source / "images" / "all").glob("*")):
        if image.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}: continue
        item = records.get(image.name, records.get(image.name.split("_", 1)[-1], {})); group = str(item.get("group_id", item.get("drug_id", image.stem))); groups.setdefault(group, []).append(image)
    groups_list = list(groups.values()); random.Random(seed).shuffle(groups_list); total = sum(map(len, groups_list)); boundaries = (total * ratios[0], total * (ratios[0] + ratios[1])); cursor = 0; result = {"train": 0, "val": 0, "test": 0}; seen: set[str] = set()
    for group in groups_list:
        split_name = "train" if cursor < boundaries[0] else "val" if cursor < boundaries[1] else "test"; cursor += len(group)
        for image in group:
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            if digest in seen: continue
            seen.add(digest); destination = output / "images" / split_name / image.name; destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(image, destination); label = source / "labels" / "all" / f"{image.stem}.txt"
            if label.exists(): destination_label = output / "labels" / split_name / label.name; destination_label.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(label, destination_label)
            result[split_name] += 1
    (output / "split_report.json").write_text(json.dumps({"ratios": ratios, "counts": result, "groups": len(groups_list)}, indent=2) + "\n", encoding="utf-8"); return result
def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--source", required=True, type=Path); parser.add_argument("--output", default=Path("ai/training/packaging/datasets/final"), type=Path); parser.add_argument("--metadata", type=Path); parser.add_argument("--train-ratio", type=float, default=.8); parser.add_argument("--val-ratio", type=float, default=.2); parser.add_argument("--test-ratio", type=float, default=0.0); args = parser.parse_args(); print(json.dumps(split(args.source, args.output, args.metadata, (args.train_ratio, args.val_ratio, args.test_ratio)), sort_keys=True))
if __name__ == "__main__": main()
