"""Export VietOCR vgg_seq2seq to quantized variants for benchmark (Mediscan AI).

Produces two quantized variants from the pretrained vgg_seq2seq.pth:
1. PyTorch Dynamic INT8 — quantizes Linear/LSTM/GRU layers in-memory
2. ONNX CNN+Encoder export + INT8 dynamic quantization via onnxruntime.quantization

Usage:
    python export_vietocr_quantized.py

Output files saved to ai/benchmark/ocr_models/weights/:
    - vietocr_cnn_encoder.onnx          (FP32 ONNX of CNN+Encoder)
    - vietocr_cnn_encoder_int8.onnx     (INT8 quantized ONNX)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import torch
import torch.nn as nn

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIGS_DIR = SCRIPT_DIR / "configs"
WEIGHTS_DIR = SCRIPT_DIR / "weights"


class CNNEncoderWrapper(nn.Module):
    """Wraps VietOCR's CNN + Transformer Encoder for ONNX export.

    The full VietOCR model is: CNN -> Transformer.Encoder -> Transformer.Decoder (loop)
    We export CNN + Encoder as a single ONNX model (no loop, pure feedforward).
    """

    def __init__(self, cnn: nn.Module, transformer_encoder_forward: object) -> None:
        super().__init__()
        self.cnn = cnn
        # Store the full transformer to access forward_encoder
        self._transformer_encoder_forward = transformer_encoder_forward

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward: image -> CNN features -> encoder memory."""
        src = self.cnn(x)
        memory = self._transformer_encoder_forward(src)
        return memory


def load_vietocr_model() -> tuple[object, object]:
    """Load VietOCR predictor and model from local config/weights."""
    from vietocr.tool.config import Cfg
    from vietocr.tool.predictor import Predictor

    cfg_file = CONFIGS_DIR / "vgg_seq2seq.yml"
    cfg = Cfg.load_config_from_file(str(cfg_file))
    cfg["device"] = "cpu"
    cfg["weights"] = str(WEIGHTS_DIR / "vgg_seq2seq.pth")
    cfg["predictor"]["beamsearch"] = False

    predictor = Predictor(cfg)
    return predictor, predictor.model


def export_pytorch_dynamic_int8() -> nn.Module:
    """Apply PyTorch dynamic quantization (INT8) to the full VietOCR model.

    Returns the quantized model (in-memory, not saved to disk).
    """
    print("\n[1/2] PyTorch Dynamic Quantization INT8...")
    _, model = load_vietocr_model()
    model.eval()

    t0 = time.perf_counter()
    quantized_model = torch.quantization.quantize_dynamic(
        model,
        {nn.Linear, nn.LSTM, nn.GRU, nn.Conv2d},
        dtype=torch.qint8,
    )
    t1 = time.perf_counter()

    print(f"  ✓ Quantized in {(t1 - t0)*1000:.1f}ms")

    # Count parameter reduction
    orig_size = sum(p.nelement() * p.element_size() for p in model.parameters())
    # For quantized models, size estimation is approximate
    print(f"  Original model params memory: {orig_size / 1024 / 1024:.1f} MB")
    print(f"  Quantized model ready (INT8 Linear/LSTM/GRU/Conv2d layers)")

    return quantized_model


def export_onnx_cnn_encoder_int8() -> Path:
    """Export CNN+Encoder to ONNX, then apply INT8 dynamic quantization.

    Returns path to the quantized ONNX file.
    """
    print("\n[2/2] ONNX CNN+Encoder Export + INT8 Quantization...")
    _, model = load_vietocr_model()
    model.eval()

    # Build wrapper
    cnn_encoder = CNNEncoderWrapper(model.cnn, model.transformer.forward_encoder)
    cnn_encoder.eval()

    # Create dummy input: batch=1, channels=3 (RGB, VGG19 backbone), height=32, width=128
    dummy_input = torch.randn(1, 3, 32, 128)

    onnx_fp32_path = WEIGHTS_DIR / "vietocr_cnn_encoder.onnx"
    onnx_int8_path = WEIGHTS_DIR / "vietocr_cnn_encoder_int8.onnx"

    # Export to ONNX
    print("  Exporting CNN+Encoder to ONNX (FP32)...")
    t0 = time.perf_counter()
    torch.onnx.export(
        cnn_encoder,
        dummy_input,
        str(onnx_fp32_path),
        input_names=["image"],
        output_names=["memory"],
        dynamic_axes={
            "image": {0: "batch", 3: "width"},
            "memory": {0: "seq_len", 1: "batch"},
        },
        opset_version=17,
        do_constant_folding=True,
        dynamo=False,  # Use legacy TorchScript exporter (torch 2.13+ compat)
    )
    t1 = time.perf_counter()
    fp32_size = onnx_fp32_path.stat().st_size
    print(f"  ✓ FP32 ONNX exported in {(t1 - t0)*1000:.1f}ms ({fp32_size / 1024 / 1024:.1f} MB)")

    # Quantize to INT8
    print("  Applying INT8 dynamic quantization...")
    t2 = time.perf_counter()
    from onnxruntime.quantization import QuantType, quantize_dynamic

    quantize_dynamic(
        str(onnx_fp32_path),
        str(onnx_int8_path),
        weight_type=QuantType.QInt8,
    )
    t3 = time.perf_counter()
    int8_size = onnx_int8_path.stat().st_size
    reduction = (1 - int8_size / fp32_size) * 100
    print(f"  ✓ INT8 ONNX quantized in {(t3 - t2)*1000:.1f}ms ({int8_size / 1024 / 1024:.1f} MB, {reduction:.1f}% smaller)")

    return onnx_int8_path


if __name__ == "__main__":
    print("=" * 70)
    print("🔧 VIETOCR QUANTIZATION EXPORT (Mediscan AI Benchmark)")
    print("=" * 70)

    # Method 1: PyTorch Dynamic INT8
    quantized_pytorch = export_pytorch_dynamic_int8()

    # Method 2: ONNX CNN+Encoder INT8
    onnx_path = export_onnx_cnn_encoder_int8()

    print("\n" + "=" * 70)
    print("✅ All quantized models ready!")
    print(f"   ONNX INT8: {onnx_path}")
    print("=" * 70)
