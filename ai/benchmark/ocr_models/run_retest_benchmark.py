"""Retest 2-Pipeline OCR Benchmark — 4 Methodological Fixes (Mediscan AI).

Fixes applied:
1. Model swap: PP-OCRv6_tiny + PP-OCRv5_mobile (replacing PP-OCRv6_medium)
2. VietOCR quantization: PyTorch Dynamic INT8 + ONNX CNN+Encoder INT8
3. Measurement control: 5 rounds, min/max/std, CPU monitoring, consistency test
4. CER + field accuracy on toa-thuoc.jpg (replaces confidence-only comparison)

Usage:
    python run_retest_benchmark.py [--rounds 5]

Output: ai/benchmark/results/retest_benchmark_report.json
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import cv2
import numpy as np
import psutil
import torch
import torch.nn as nn
from PIL import Image

# Local modules
from ground_truth import (
    DRUG_FIELD_TARGETS,
    GROUND_TRUTH_TOA_THUOC_KEY_LINES,
    compute_cer,
    compute_field_accuracy,
)

try:
    import cpuinfo
except ImportError:
    cpuinfo = None

from paddleocr import PaddleOCR

from vietocr.tool.config import Cfg
from vietocr.tool.predictor import Predictor as VietOCRPredictor

SCRIPT_DIR = Path(__file__).resolve().parent
BENCHMARK_DIR = SCRIPT_DIR.parent
SAMPLE_DIR = SCRIPT_DIR / "sample_images"
RESULTS_DIR = BENCHMARK_DIR / "results"
CONFIGS_DIR = SCRIPT_DIR / "configs"
WEIGHTS_DIR = SCRIPT_DIR / "weights"

MAX_IMAGE_DIM = 1600
SLA_TARGET_MS = 15000

# Previous benchmark results (PP-OCRv6_medium) for comparison
PREV_RESULTS_FILE = RESULTS_DIR / "pretrained_baseline_report.json"


# ── CPU Monitoring ───────────────────────────────────────────────────────────


class CPUMonitor:
    """Background CPU usage monitor using psutil."""

    def __init__(self, interval_sec: float = 0.5) -> None:
        self.interval = interval_sec
        self.readings: list[float] = []
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, float]:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if not self.readings:
            return {"avg_cpu_pct": 0.0, "max_cpu_pct": 0.0, "samples": 0}
        return {
            "avg_cpu_pct": round(statistics.mean(self.readings), 1),
            "max_cpu_pct": round(max(self.readings), 1),
            "min_cpu_pct": round(min(self.readings), 1),
            "samples": len(self.readings),
        }

    def _monitor(self) -> None:
        while self._running:
            self.readings.append(psutil.cpu_percent(interval=self.interval))


# ── Helpers ──────────────────────────────────────────────────────────────────


def get_cpu_brand() -> str:
    if cpuinfo:
        try:
            info = cpuinfo.get_cpu_info()
            return info.get("brand_raw", platform.processor())
        except Exception:
            pass
    return platform.processor() or "x86_64 CPU"


def load_image(image_path: Path, max_dim: int = MAX_IMAGE_DIM) -> np.ndarray:
    """Load image as BGR numpy array, downscale if needed."""
    arr = cv2.imread(str(image_path))
    if arr is None:
        with Image.open(image_path) as img:
            rgb = np.array(img.convert("RGB"))
        arr = rgb[:, :, ::-1]
    h, w = arr.shape[:2]
    longest = max(h, w)
    if longest > max_dim:
        scale = max_dim / longest
        new_w = max(1, round(w * scale))
        new_h = max(1, round(h * scale))
        arr = cv2.resize(arr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return arr


def crop_polygon(image_bgr: np.ndarray, polygon: list[list[float]] | np.ndarray) -> Image.Image:
    """Crop text bounding box polygon to a PIL RGB image."""
    poly = np.array(polygon, dtype=np.float32)
    x_min = max(0, int(np.floor(np.min(poly[:, 0]))))
    x_max = min(image_bgr.shape[1], int(np.ceil(np.max(poly[:, 0]))))
    y_min = max(0, int(np.floor(np.min(poly[:, 1]))))
    y_max = min(image_bgr.shape[0], int(np.ceil(np.max(poly[:, 1]))))
    crop_bgr = image_bgr[y_min:y_max, x_min:x_max]
    if crop_bgr.size == 0 or crop_bgr.shape[0] < 2 or crop_bgr.shape[1] < 2:
        return Image.new("RGB", (32, 32), color="white")
    crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(crop_rgb)


def latency_stats(times: list[float]) -> dict[str, float]:
    """Compute mean/min/max/std from a list of latency values."""
    return {
        "mean_ms": round(statistics.mean(times), 2),
        "min_ms": round(min(times), 2),
        "max_ms": round(max(times), 2),
        "std_ms": round(statistics.stdev(times), 2) if len(times) > 1 else 0.0,
    }


# ── Model Initializers ──────────────────────────────────────────────────────


def init_ppocr(det_model: str, rec_model: str) -> Any:
    """Initialize PaddleOCR with specified detection/recognition models."""
    return PaddleOCR(
        text_detection_model_name=det_model,
        text_recognition_model_name=rec_model,
        use_textline_orientation=False,
        device="cpu",
        engine="onnxruntime",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
    )


def init_vietocr_fp32() -> VietOCRPredictor:
    """Initialize VietOCR predictor (FP32 baseline)."""
    cfg_file = CONFIGS_DIR / "vgg_seq2seq.yml"
    config = Cfg.load_config_from_file(str(cfg_file))
    config["device"] = "cpu"
    config["predictor"]["beamsearch"] = False
    config["weights"] = str(WEIGHTS_DIR / "vgg_seq2seq.pth")
    return VietOCRPredictor(config)


def init_vietocr_pytorch_int8() -> tuple[Any, Any]:
    """Initialize VietOCR with PyTorch Dynamic INT8 quantization.

    Returns (quantized_model, predictor) — predictor for vocab/config access,
    model is replaced with quantized version.
    """
    predictor = init_vietocr_fp32()
    original_model = predictor.model
    original_model.eval()

    quantized_model = torch.quantization.quantize_dynamic(
        original_model,
        {nn.Linear, nn.LSTM, nn.GRU},
        dtype=torch.qint8,
    )
    # Replace model in predictor
    predictor.model = quantized_model
    return predictor


def init_vietocr_onnx_int8() -> tuple[Any, Any, Any]:
    """Initialize VietOCR with ONNX CNN+Encoder INT8 + PyTorch Decoder.

    Returns (onnx_session, predictor, config) for hybrid inference.
    """
    import onnxruntime as ort

    onnx_int8_path = WEIGHTS_DIR / "vietocr_cnn_encoder_int8.onnx"
    if not onnx_int8_path.exists():
        raise FileNotFoundError(
            f"ONNX INT8 model not found: {onnx_int8_path}\n"
            "Run export_vietocr_quantized.py first."
        )

    session = ort.InferenceSession(
        str(onnx_int8_path),
        providers=["CPUExecutionProvider"],
    )
    predictor = init_vietocr_fp32()
    return session, predictor, predictor.config


# ── Pipeline Runners ─────────────────────────────────────────────────────────


def run_pipeline1(ppocr_engine: Any, img_bgr: np.ndarray) -> tuple[float, float, list[str]]:
    """Pipeline 1: PP-OCR full (det + rec). Returns (total_ms, avg_conf, texts)."""
    t0 = time.perf_counter()
    results = ppocr_engine.predict(img_bgr)
    t1 = time.perf_counter()
    total_ms = (t1 - t0) * 1000

    texts: list[str] = []
    confs: list[float] = []
    for res in results:
        data = res if isinstance(res, dict) else (res.json if hasattr(res, "json") else {})
        if isinstance(data, dict):
            texts.extend(data.get("rec_texts", []) or [])
            confs.extend(data.get("rec_scores", []) or [])

    avg_conf = float(np.mean(confs)) if confs else 0.0
    return total_ms, avg_conf, texts


def _extract_det_polys(ppocr_engine: Any, img_bgr: np.ndarray) -> tuple[list[Any], float]:
    """Run PP-OCR detection only, return polygons and detection time."""
    t0 = time.perf_counter()
    results = ppocr_engine.predict(img_bgr)
    t1 = time.perf_counter()
    det_ms = (t1 - t0) * 1000

    dt_polys: list[Any] = []
    for res in results:
        data = res if isinstance(res, dict) else (res.json if hasattr(res, "json") else {})
        if isinstance(data, dict) and "dt_polys" in data:
            dt_polys.extend(data.get("dt_polys", []) or [])
    return dt_polys, det_ms


def run_pipeline2_fp32(
    ppocr_engine: Any, vietocr_predictor: Any, img_bgr: np.ndarray
) -> tuple[float, float, float, list[str]]:
    """Pipeline 2 (FP32): PP-OCR det + VietOCR FP32 rec.
    Returns (det_ms, rec_ms, avg_conf, texts).
    """
    dt_polys, det_ms = _extract_det_polys(ppocr_engine, img_bgr)

    t_rec_start = time.perf_counter()
    texts: list[str] = []
    probs: list[float] = []
    for poly in dt_polys:
        crop_pil = crop_polygon(img_bgr, poly)
        try:
            pred_text, prob = vietocr_predictor.predict(crop_pil, return_prob=True)
            if pred_text and pred_text.strip():
                texts.append(pred_text.strip())
                probs.append(float(prob))
        except Exception:
            continue
    t_rec_end = time.perf_counter()
    rec_ms = (t_rec_end - t_rec_start) * 1000
    avg_conf = float(np.mean(probs)) if probs else 0.0
    return det_ms, rec_ms, avg_conf, texts


def run_pipeline2_pytorch_int8(
    ppocr_engine: Any, vietocr_int8_predictor: Any, img_bgr: np.ndarray
) -> tuple[float, float, float, list[str]]:
    """Pipeline 2 (PyTorch INT8): PP-OCR det + VietOCR quantized rec."""
    return run_pipeline2_fp32(ppocr_engine, vietocr_int8_predictor, img_bgr)


def run_pipeline2_onnx_int8(
    ppocr_engine: Any, onnx_session: Any, vietocr_predictor: Any,
    img_bgr: np.ndarray,
) -> tuple[float, float, float, list[str]]:
    """Pipeline 2 (ONNX INT8): PP-OCR det + ONNX CNN+Encoder + PyTorch Decoder.

    Uses ONNX INT8 session for CNN+Encoder, then PyTorch decoder for autoregressive generation.
    """
    from vietocr.tool.translate import translate
    from vietocr.tool.utils import process_input

    dt_polys, det_ms = _extract_det_polys(ppocr_engine, img_bgr)
    config = vietocr_predictor.config

    t_rec_start = time.perf_counter()
    texts: list[str] = []
    probs: list[float] = []

    for poly in dt_polys:
        crop_pil = crop_polygon(img_bgr, poly)
        try:
            # Preprocess image the same way VietOCR does
            img_tensor = process_input(
                crop_pil,
                config["dataset"]["image_height"],
                config["dataset"]["image_min_width"],
                config["dataset"]["image_max_width"],
            )

            # Run CNN+Encoder through ONNX
            img_np = img_tensor.numpy()
            onnx_result = onnx_session.run(None, {"image": img_np})
            memory_np = onnx_result[0]  # encoder memory

            # Convert back to torch for decoder
            memory = torch.from_numpy(memory_np)

            # Run decoder using VietOCR's translate logic (adapted)
            model = vietocr_predictor.model
            model.eval()
            device = torch.device("cpu")

            sos_token = 1
            eos_token = 2
            max_seq_length = 128

            translated_sentence = [[sos_token]]
            char_probs_list = [[1.0]]
            max_length = 0

            while max_length <= max_seq_length:
                tgt_inp = torch.LongTensor(translated_sentence).to(device)
                output, memory = model.transformer.forward_decoder(tgt_inp, memory)
                output = torch.softmax(output, dim=-1).cpu()

                values, indices = torch.topk(output, 5)
                idx = indices[:, -1, 0].tolist()
                val = values[:, -1, 0].tolist()

                char_probs_list.append(val)
                translated_sentence.append(idx)
                max_length += 1

                if all(np.any(np.asarray(translated_sentence).T == eos_token, axis=1)):
                    break

            sent = np.asarray(translated_sentence).T
            cprobs = np.asarray(char_probs_list).T
            cprobs = np.multiply(cprobs, sent > 3)
            prob_val = float(np.sum(cprobs, axis=-1)[0] / max(1, (cprobs > 0).sum(-1)[0]))

            decoded = vietocr_predictor.vocab.decode(sent[0].tolist())
            if decoded and decoded.strip():
                texts.append(decoded.strip())
                probs.append(prob_val)
        except Exception:
            continue

    t_rec_end = time.perf_counter()
    rec_ms = (t_rec_end - t_rec_start) * 1000
    avg_conf = float(np.mean(probs)) if probs else 0.0
    return det_ms, rec_ms, avg_conf, texts


# ── Consistency Test ─────────────────────────────────────────────────────────


def run_consistency_test(ppocr_engine: Any, img_bgr: np.ndarray) -> dict[str, Any]:
    """Run detection 2x on same image in same session, verify <15% deviation."""
    print("\n[CONSISTENCY] Running detection 2x on toa-thuoc.jpg...")

    t0 = time.perf_counter()
    ppocr_engine.predict(img_bgr)
    t1 = time.perf_counter()
    run1_ms = (t1 - t0) * 1000

    t2 = time.perf_counter()
    ppocr_engine.predict(img_bgr)
    t3 = time.perf_counter()
    run2_ms = (t3 - t2) * 1000

    max_val = max(run1_ms, run2_ms)
    deviation_pct = abs(run1_ms - run2_ms) / max_val * 100 if max_val > 0 else 0.0
    passed = deviation_pct < 15.0

    print(f"  Run 1: {run1_ms:.1f}ms")
    print(f"  Run 2: {run2_ms:.1f}ms")
    print(f"  Deviation: {deviation_pct:.1f}% {'✓ PASS (<15%)' if passed else '✗ FAIL (>=15%)'}")

    return {
        "run1_ms": round(run1_ms, 2),
        "run2_ms": round(run2_ms, 2),
        "deviation_pct": round(deviation_pct, 2),
        "pass": passed,
    }


# ── Main Benchmark ───────────────────────────────────────────────────────────


def load_prev_results() -> dict[str, Any] | None:
    """Load previous benchmark results for comparison."""
    if PREV_RESULTS_FILE.exists():
        with open(PREV_RESULTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return None


def run_retest_benchmark(rounds: int = 5) -> dict[str, Any]:
    """Execute the full retest benchmark with all 4 fixes."""
    print("=" * 70)
    print("🚀 MEDISCAN AI — RETEST BENCHMARK (4 Methodological Fixes)")
    print("=" * 70)

    # Start CPU monitoring
    cpu_monitor = CPUMonitor(interval_sec=0.5)
    cpu_monitor.start()

    # ── Load Models ──────────────────────────────────────────────────────
    print("\n[1/7] Loading models...")

    # PP-OCR configs to test
    ppocr_configs = [
        ("PP-OCRv6_tiny", "PP-OCRv6_tiny_det", "PP-OCRv6_tiny_rec"),
        ("PP-OCRv5_mobile", "PP-OCRv5_mobile_det", "PP-OCRv5_mobile_rec"),
    ]

    ppocr_engines: dict[str, Any] = {}
    for label, det, rec in ppocr_configs:
        t0 = time.perf_counter()
        ppocr_engines[label] = init_ppocr(det, rec)
        t1 = time.perf_counter()
        print(f"  ✓ {label} (ONNX CPU) loaded in {(t1 - t0)*1000:.1f}ms")

    # VietOCR variants
    t0 = time.perf_counter()
    vietocr_fp32 = init_vietocr_fp32()
    t1 = time.perf_counter()
    print(f"  ✓ VietOCR FP32 loaded in {(t1 - t0)*1000:.1f}ms")

    t0 = time.perf_counter()
    vietocr_int8 = init_vietocr_pytorch_int8()
    t1 = time.perf_counter()
    print(f"  ✓ VietOCR PyTorch INT8 loaded in {(t1 - t0)*1000:.1f}ms")

    onnx_session = None
    onnx_int8_path = WEIGHTS_DIR / "vietocr_cnn_encoder_int8.onnx"
    if onnx_int8_path.exists():
        t0 = time.perf_counter()
        onnx_session, onnx_predictor, _ = init_vietocr_onnx_int8()
        t1 = time.perf_counter()
        print(f"  ✓ VietOCR ONNX INT8 loaded in {(t1 - t0)*1000:.1f}ms")
    else:
        print("  ⚠ VietOCR ONNX INT8 not found — skipping (run export_vietocr_quantized.py first)")

    # ── Collect Images ───────────────────────────────────────────────────
    images = sorted([p for p in SAMPLE_DIR.iterdir() if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]])
    print(f"\n[2/7] Found {len(images)} test images")

    # ── Warm-up ──────────────────────────────────────────────────────────
    print("\n[3/7] Warming up all engines (1 round each)...")
    if images:
        dummy_img = load_image(images[0])
        for label, engine in ppocr_engines.items():
            run_pipeline1(engine, dummy_img)
        run_pipeline2_fp32(list(ppocr_engines.values())[0], vietocr_fp32, dummy_img)
        run_pipeline2_pytorch_int8(list(ppocr_engines.values())[0], vietocr_int8, dummy_img)
        if onnx_session:
            run_pipeline2_onnx_int8(list(ppocr_engines.values())[0], onnx_session, onnx_predictor, dummy_img)
    print("  ✓ Warm-up complete")

    # ── Benchmark Pipeline 1 (all PP-OCR configs × all images) ───────────
    print(f"\n[4/7] Pipeline 1 benchmark ({rounds} rounds per image per config)...")
    p1_results: list[dict[str, Any]] = []

    for config_label, engine in ppocr_engines.items():
        for img_path in images:
            img_name = img_path.name
            img_bgr = load_image(img_path)
            times: list[float] = []
            confs: list[float] = []
            last_texts: list[str] = []

            for r in range(rounds):
                tot_ms, conf, texts = run_pipeline1(engine, img_bgr)
                times.append(tot_ms)
                confs.append(conf)
                if r == rounds - 1:
                    last_texts = texts

            stats = latency_stats(times)
            avg_conf = round(statistics.mean(confs), 4)
            sla_pass = stats["mean_ms"] < SLA_TARGET_MS

            # CER/field accuracy for toa-thuoc only
            cer_val = None
            field_acc = None
            if "toa-thuoc" in img_name:
                full_text = "\n".join(last_texts)
                gt_text = "\n".join(GROUND_TRUTH_TOA_THUOC_KEY_LINES)
                cer_val = round(compute_cer(full_text, gt_text), 4)
                field_acc = compute_field_accuracy(full_text, DRUG_FIELD_TARGETS)

            result = {
                "config": config_label,
                "pipeline": "P1_PPOCR_FullRec",
                "image": img_name,
                "latency": stats,
                "avg_confidence": avg_conf,
                "sla_pass": sla_pass,
                "num_lines": len(last_texts),
                "text_preview": " | ".join(last_texts[:4]),
            }
            if cer_val is not None:
                result["cer"] = cer_val
                result["field_accuracy"] = field_acc

            p1_results.append(result)
            status = "PASS" if sla_pass else "FAIL"
            print(f"  {config_label} | {img_name}: {stats['mean_ms']:.0f}ms (±{stats['std_ms']:.0f}) | conf={avg_conf:.3f} | {status}")

    # ── Benchmark Pipeline 2 (VietOCR variants × all images) ─────────────
    print(f"\n[5/7] Pipeline 2 benchmark ({rounds} rounds)...")

    # Use first PP-OCR config as detector for Pipeline 2
    det_config_label = list(ppocr_engines.keys())[0]
    det_engine = ppocr_engines[det_config_label]

    vietocr_variants: list[tuple[str, Any]] = [
        ("VietOCR_FP32", lambda eng, img: run_pipeline2_fp32(eng, vietocr_fp32, img)),
        ("VietOCR_PyTorch_INT8", lambda eng, img: run_pipeline2_pytorch_int8(eng, vietocr_int8, img)),
    ]
    if onnx_session:
        vietocr_variants.append(
            ("VietOCR_ONNX_INT8", lambda eng, img: run_pipeline2_onnx_int8(eng, onnx_session, onnx_predictor, img)),
        )

    p2_results: list[dict[str, Any]] = []

    for variant_label, run_fn in vietocr_variants:
        for img_path in images:
            img_name = img_path.name
            img_bgr = load_image(img_path)
            det_times: list[float] = []
            rec_times: list[float] = []
            total_times: list[float] = []
            confs: list[float] = []
            last_texts: list[str] = []

            for r in range(rounds):
                det_ms, rec_ms, conf, texts = run_fn(det_engine, img_bgr)
                det_times.append(det_ms)
                rec_times.append(rec_ms)
                total_times.append(det_ms + rec_ms)
                confs.append(conf)
                if r == rounds - 1:
                    last_texts = texts

            total_stats = latency_stats(total_times)
            rec_stats = latency_stats(rec_times)
            avg_conf = round(statistics.mean(confs), 4)
            sla_pass = total_stats["mean_ms"] < SLA_TARGET_MS

            cer_val = None
            field_acc = None
            if "toa-thuoc" in img_name:
                full_text = "\n".join(last_texts)
                gt_text = "\n".join(GROUND_TRUTH_TOA_THUOC_KEY_LINES)
                cer_val = round(compute_cer(full_text, gt_text), 4)
                field_acc = compute_field_accuracy(full_text, DRUG_FIELD_TARGETS)

            result = {
                "config": f"{det_config_label}+{variant_label}",
                "pipeline": "P2_PPOCR_Det+VietOCR_Rec",
                "vietocr_variant": variant_label,
                "image": img_name,
                "latency_total": total_stats,
                "latency_recognition": rec_stats,
                "avg_confidence": avg_conf,
                "sla_pass": sla_pass,
                "num_lines": len(last_texts),
                "text_preview": " | ".join(last_texts[:4]),
            }
            if cer_val is not None:
                result["cer"] = cer_val
                result["field_accuracy"] = field_acc

            p2_results.append(result)
            status = "PASS" if sla_pass else "FAIL"
            print(f"  {det_config_label}+{variant_label} | {img_name}: {total_stats['mean_ms']:.0f}ms (±{total_stats['std_ms']:.0f}) | conf={avg_conf:.3f} | {status}")

    # ── Quantization Comparison (toa-thuoc specific) ─────────────────────
    print("\n[6/7] Quantization latency comparison (toa-thuoc.jpg)...")
    quant_comparison: dict[str, Any] = {}

    # Extract toa-thuoc results for each VietOCR variant
    for variant_label, _ in vietocr_variants:
        toa_results = [r for r in p2_results if r.get("vietocr_variant") == variant_label and "toa-thuoc" in r["image"]]
        if toa_results:
            quant_comparison[variant_label] = {
                "total_latency_ms": toa_results[0]["latency_total"]["mean_ms"],
                "rec_latency_ms": toa_results[0]["latency_recognition"]["mean_ms"],
            }

    # Compute % reduction
    if "VietOCR_FP32" in quant_comparison:
        fp32_rec = quant_comparison["VietOCR_FP32"]["rec_latency_ms"]
        for key in ["VietOCR_PyTorch_INT8", "VietOCR_ONNX_INT8"]:
            if key in quant_comparison:
                opt_rec = quant_comparison[key]["rec_latency_ms"]
                reduction = (1 - opt_rec / fp32_rec) * 100 if fp32_rec > 0 else 0
                quant_comparison[key]["latency_reduction_pct"] = round(reduction, 1)
                print(f"  {key}: rec={opt_rec:.0f}ms (Δ {reduction:+.1f}% vs FP32)")
        print(f"  VietOCR_FP32: rec={fp32_rec:.0f}ms (baseline)")

    # ── Consistency Test ─────────────────────────────────────────────────
    print("\n[7/7] Consistency test...")
    toa_path = SAMPLE_DIR / "toa-thuoc.jpg"
    consistency_result: dict[str, Any] = {"skipped": True}
    if toa_path.exists():
        toa_img = load_image(toa_path)
        consistency_result = run_consistency_test(det_engine, toa_img)

    # ── Stop CPU monitor ─────────────────────────────────────────────────
    cpu_stats = cpu_monitor.stop()

    # ── Assemble Report ──────────────────────────────────────────────────
    prev_data = load_prev_results()

    final_report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "cpu_info": get_cpu_brand(),
            "python_version": sys.version.split()[0],
            "os": f"{platform.system()} {platform.release()}",
            "benchmark_rounds": rounds,
            "cpu_during_benchmark": cpu_stats,
            "model_configs_tested": {
                "ppocr": [c[0] for c in ppocr_configs],
                "vietocr_variants": [v[0] for v in vietocr_variants],
            },
        },
        "pipeline1_results": p1_results,
        "pipeline2_results": p2_results,
        "quantization_comparison": quant_comparison,
        "consistency_test": consistency_result,
        "sla_check": {
            "target_ms": SLA_TARGET_MS,
            "all_p1_pass": all(r["sla_pass"] for r in p1_results),
            "all_p2_pass": all(r["sla_pass"] for r in p2_results),
        },
        "previous_baseline_summary": (
            {
                "model": "PP-OCRv6_medium",
                "toa_thuoc_p1_ms": None,
                "toa_thuoc_p2_ms": None,
            }
            if prev_data is None
            else _extract_prev_summary(prev_data)
        ),
    }

    # Save
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = RESULTS_DIR / "retest_benchmark_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print(f"✅ RETEST COMPLETE! Report: {report_file}")
    all_pass = final_report["sla_check"]["all_p1_pass"] and final_report["sla_check"]["all_p2_pass"]
    print(f"   SLA Status: {'ALL PASS' if all_pass else 'SOME FAIL'} (target <{SLA_TARGET_MS}ms)")
    print("=" * 70)

    return final_report


def _extract_prev_summary(prev_data: dict[str, Any]) -> dict[str, Any]:
    """Extract key numbers from previous baseline report for comparison."""
    summary: dict[str, Any] = {"model": "PP-OCRv6_medium"}
    for r in prev_data.get("results", []):
        if "toa-thuoc" in r.get("image", ""):
            if r.get("pipeline") == "packaging":
                summary["toa_thuoc_p1_ms"] = r.get("total_time_ms")
            elif r.get("pipeline") == "prescription":
                summary["toa_thuoc_p2_ms"] = r.get("total_time_ms")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retest 2-Pipeline OCR Benchmark (4 Fixes)")
    parser.add_argument("--rounds", type=int, default=5, help="Rounds per image (default: 5)")
    args = parser.parse_args()
    run_retest_benchmark(rounds=args.rounds)
