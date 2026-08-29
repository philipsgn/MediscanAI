"""Train a YOLO11-nano detector on the synthetic/real packaging dataset."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


def train(model_name: str, data: Path, hyperparams: Path, project: Path) -> Any:
    """Run Ultralytics training and return its result object."""
    try:
        from ultralytics import YOLO
        import yaml
    except ImportError as exc:
        raise RuntimeError("Install ultralytics and PyYAML to train the detector") from exc
    try:
        params = yaml.safe_load(hyperparams.read_text(encoding="utf-8"))
        params.pop("model", None)
        model = YOLO(model_name)
        return model.train(data=str(data), project=str(project), name="packaging", **params)
    except (OSError, TypeError, ValueError, RuntimeError) as exc:
        raise RuntimeError(f"YOLO training failed: {exc}") from exc


def main() -> None:
    """Parse training paths and start a CPU-safe YOLO11 training run."""
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--data", type=Path, default=root / "configs" / "packaging_data.yaml")
    parser.add_argument("--hyperparams", type=Path, default=root / "configs" / "train_hyperparams.yaml")
    parser.add_argument("--project", type=Path, default=root / "weights")
    args = parser.parse_args()
    train(args.model, args.data, args.hyperparams, args.project)


if __name__ == "__main__":
    main()
