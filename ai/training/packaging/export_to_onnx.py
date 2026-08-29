"""Export packaging YOLO weights to CPU-oriented ONNX and smoke-test inference."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np


def export(weights: Path, output: Path, half: bool = False, int8: bool = False) -> Path:
    """Export fixed 640x640 ONNX weights and verify CPU loading/inference."""
    if half and int8:
        raise ValueError("Choose at most one of --half and --int8")
    try:
        from ultralytics import YOLO
        import onnxruntime as ort
        model = YOLO(str(weights))
        exported = Path(model.export(format="onnx", imgsz=640, dynamic=False, half=half, int8=int8, device="cpu"))
        output.parent.mkdir(parents=True, exist_ok=True)
        if exported.resolve() != output.resolve():
            output.write_bytes(exported.read_bytes())
        session = ort.InferenceSession(str(output), providers=["CPUExecutionProvider"])
        input_meta = session.get_inputs()[0]
        shape = [int(value) if isinstance(value, (int, np.integer)) else 1 for value in input_meta.shape]
        sample = np.zeros(shape, dtype=np.float16 if half else np.float32)
        start = time.perf_counter()
        session.run(None, {input_meta.name: sample})
        latency_ms = (time.perf_counter() - start) * 1000
        print(f"ONNX CPU inference: {latency_ms:.2f} ms")
        if latency_ms >= 100:
            print("WARNING: CPU latency is >= 100 ms on this machine")
        return output
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError(f"ONNX export or smoke test failed: {exc}") from exc


def main() -> None:
    """Parse export options and produce ``ai/models/packaging_detector.onnx``."""
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, default=root / "training" / "packaging" / "weights" / "best.pt")
    parser.add_argument("--output", type=Path, default=root / "models" / "packaging_detector.onnx")
    parser.add_argument("--half", action="store_true", help="Export FP16 (when supported by the exporter)")
    parser.add_argument("--int8", action="store_true", help="Export INT8 (requires Ultralytics calibration data)")
    args = parser.parse_args()
    export(args.weights, args.output, args.half, args.int8)


if __name__ == "__main__":
    main()
