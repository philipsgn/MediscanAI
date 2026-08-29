"""Evaluate a trained packaging YOLO model and print standard detection metrics."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


def evaluate(weights: Path, data: Path, imgsz: int = 640, split: str = "val") -> Any:
    """Validate weights and return Ultralytics' metrics object."""
    try:
        from ultralytics import YOLO
        model = YOLO(str(weights))
        return model.val(data=str(data), imgsz=imgsz, split=split, device="cpu")
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError(f"Evaluation failed: {exc}") from exc


def main() -> None:
    """Run validation and report mAP, precision, and recall."""
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, default=root / "weights" / "packaging" / "weights" / "best.pt")
    parser.add_argument("--data", type=Path, default=root / "configs" / "packaging_data.yaml")
    args = parser.parse_args()
    metrics = evaluate(args.weights, args.data)
    box = metrics.box
    print(f"mAP@50: {box.map50:.4f}\nmAP@50-95: {box.map:.4f}\nPrecision: {box.mp:.4f}\nRecall: {box.mr:.4f}")


if __name__ == "__main__":
    main()
