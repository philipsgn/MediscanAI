"""Benchmark PP-OCR (PaddleOCR / OpenVINO) tren CPU local.

Quet dong toan bo anh trong sample_images/ (jpg/jpeg/png/webp ke ca duoi
in hoa). Mo mo hinh bang OpenCV (cv2.imread); neu tra ve None (vd file
.webp), fallback dung PIL.Image.open() -> numpy.ndarray.

PaddleOCR 3.7+ (PaddleX) duoc ep chay bang engine 'onnxruntime' (official
CPU backend, khong can paddlepaddle - PaddleX tu dong tai model ONNX).
Ghi chu: PaddleX 3.7 khong ho tro backend 'openvino'.

Quy trinh moi anh: warm-up 1 luot -> do lap 3 luot (default) -> tinh
average latency + avg confidence -> xuat JSON kem summary.

Cach dung:
    python benchmark_ppocr.py
    python benchmark_ppocr.py --rounds 5
    python benchmark_ppocr.py --lang vi
    python benchmark_ppocr.py --no-doc-ori --no-unwarp

Ghi chu: Doc orientation classifier (PP-LCNet_x1_0_doc_ori) va UVDoc
unwarping ton nhieu CPU tren moi anh. Voi anh chup dien thoai thang dung
nen chay voi '--no-doc-ori --no-unwarp' de dat Avg Latency < SLA.

Ghi chu: Script khong crash neu thieu thu vien paddleocr/numpy/cv2/PIL -
se in loi ro rang va ket thuc voi ma exit != 0.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:  # deps chua cai -> RAM tracking vo hieu, khong crash
    psutil = None

try:
    import numpy as np
except ImportError:
    print(
        "[ERROR] Thieu thu vien 'numpy'. Vui long chay: "
        "pip install -r requirements-bench.txt"
    )
    sys.exit(1)

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image
except ImportError:
    Image = None

SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SCRIPT_DIR / "results"
SAMPLE_DIR = SCRIPT_DIR / "sample_images"

# SLA: nguong thoi gian trung binh cho 1 anh tren CPU (configurable qua CLI)
DEFAULT_CPU_SLA_SECONDS = 15.0

# Downscale: canh lon nhat (max(h, w)) toi da 1600px truoc khi OCR.
# Giam khoi luong tinh toan tren CPU -> Avg Latency < SLA.
MAX_IMAGE_DIM = 1600

# Mac dinh tat 2 preprocessing stage ton CPU (doc orientation + unwarp),
# xem docstring init_ocr(). Van co the bat lai bang CLI khi can.
DEFAULT_NO_DOC_ORI = True
DEFAULT_NO_UNWARP = True

# Danh sach dinh dang anh duoc quet dong (bao gom duoi in hoa + .webp)
IMAGE_PATTERNS: tuple[str, ...] = (
    "*.jpg", "*.jpeg", "*.JPG", "*.JPEG",
    "*.png", "*.PNG", "*.webp", "*.WEBP",
)


def scan_images(sample_dir: Path) -> list[Path]:
    """Quet dong toan bo anh (multi-format) trong thu muc, dedup theo path."""
    images: list[Path] = []
    for pattern in IMAGE_PATTERNS:
        images.extend(sample_dir.glob(pattern))

    seen: set[str] = set()
    unique: list[Path] = []
    for image in sorted(images, key=lambda p: p.name):
        key = str(image.resolve()).lower()
        if key not in seen:
            seen.add(key)
            unique.append(image)
    return unique


def downscale_image(arr: "np.ndarray", max_dim: int = MAX_IMAGE_DIM) -> "np.ndarray":
    """Downscale anh giu nguyen aspect ratio, canh lon nhat <= max_dim.

    Chi resize khi can thiet (max(height, width) > max_dim). Dung
    INTER_AREA/LANCZOS de giu chat luong text cho OCR.
    """
    height, width = arr.shape[:2]
    longest = max(height, width)
    if longest <= max_dim:
        return arr

    scale = max_dim / longest
    new_w = max(1, round(width * scale))
    new_h = max(1, round(height * scale))

    if cv2 is not None:
        return cv2.resize(arr, (new_w, new_h), interpolation=cv2.INTER_AREA)

    if Image is None:
        raise ImportError("Thieu thu vien 'pillow' de downscale anh.")
    rgb = Image.fromarray(arr[:, :, ::-1] if arr.ndim == 3 else arr)
    rgb = rgb.resize((new_w, new_h), Image.LANCZOS)
    return np.array(rgb)[:, :, ::-1]  # RGB -> BGR


def load_image_array(image_path: Path, max_dim: int = MAX_IMAGE_DIM) -> "np.ndarray":
    """Nap anh thanh numpy.ndarray (BGR) va downscale toi da max_dim.

    Uu tien cv2.imread(); neu tra ve None (dac biet voi .webp hoac khi
    OpenCV khong ho tro), fallback dung PIL.Image.open() roi convert sang
    numpy.ndarray theo quy uoc BGR cua OpenCV.
    """
    if cv2 is not None:
        arr = cv2.imread(str(image_path))
        if arr is not None:
            return downscale_image(arr, max_dim)

    if Image is None:
        raise ImportError(
            "Thieu thu vien 'pillow' de fallback doc anh. Vui long chay: "
            "pip install -r requirements-bench.txt"
        )

    with Image.open(image_path) as img:
        rgb = np.array(img.convert("RGB"))
    return downscale_image(rgb[:, :, ::-1], max_dim)  # RGB -> BGR


def track_ram_peak() -> float:
    """Tra ve RSS (MB) cua tien trinh hien tai."""
    if psutil is None:
        return 0.0
    try:
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except (psutil.Error, AttributeError):
        return 0.0


def init_ocr(
    lang: str,
    no_doc_ori: bool = False,
    no_unwarp: bool = False,
) -> Any:
    """Khoi tao PaddleOCR 3.7+ tren CPU bang ONNX Runtime engine.

    Thuc te da kiem tra tren bo cai dat (PaddleOCR 3.7.0 + PaddleX 3.7.2):
    - PaddleX 3.7 KHONG co backend 'openvino' (duyet toan bo source: khong
      co tham chieu nao), nen khong the ep 'text_det_engine'/'text_rec_engine'
      = 'openvino' (API 3.7 khong ton tai 2 tham so nay).
    - Engine CPU chay duoc ma KHONG can gói 'paddlepaddle' la 'onnxruntime':
      PaddleX tu dong tai phien ban ONNX cua model chinh thuc (khong can
      convert). 'device' thay the 'use_gpu', 'use_textline_orientation'
      thay the 'use_angle_cls'.
    - Neu cai phien ban cu (< 3.7) se tu dong fallback sang kwargs cu.

    Pipeline preprocessing tac dong thoi gian (co the tat qua flag):
    - PP-LCNet_x1_0_doc_ori: phan loai huong trang (doc orientation), chi
      huu ich voi scan quay vo. Anh chup dien thoai dang thang dung -> 'no_doc_ori'.
    - UVDoc: unwarping (nang cong trang), cost cao tren CPU -> 'no_unwarp'.
    """
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise ImportError(
            "Thieu thu vien 'paddleocr'. Vui long chay: "
            "pip install -r requirements-bench.txt"
        ) from exc

    # API chuan hoa cho PaddleOCR 3.7+ (PaddleX)
    # engine='onnxruntime' + device='cpu': inference tren CPU ma khong can
    # paddlepaddle, tranh loi 'Engine paddle_static is unavailable'.
    init_kwargs: dict[str, Any] = {
        "use_textline_orientation": True,  # thay the use_angle_cls
        "device": "cpu",  # thay the use_gpu
        "lang": lang,
        "engine": "onnxruntime",  # engine CPU khong phu thuoc paddlepaddle
        "use_doc_orientation_classify": not no_doc_ori,
        "use_doc_unwarping": not no_unwarp,
    }

    try:
        return PaddleOCR(**init_kwargs)
    except TypeError:
        # Fallback cho PaddleOCR < 3.7: dung kwargs cu (use_gpu / use_angle_cls ...)
        legacy_kwargs: dict[str, Any] = {
            "lang": lang,
            "use_angle_cls": True,
            "show_log": False,
            "use_gpu": False,
            "enable_mkldnn": True,
        }
        return PaddleOCR(**legacy_kwargs)


def extract_text_and_conf(results: Any) -> tuple[list[str], list[float]]:
    """Tach chuoi OCR va confidence tu ket qua cua PaddleOCR (ho tro 2 API)."""
    texts: list[str] = []
    confs: list[float] = []

    # API moi (paddleocr >= 2.7 / 3.x): ocr.predict() -> list[dict-like]
    try:
        for res in results:
            if isinstance(res, dict) and "rec_texts" in res:
                texts.extend(res["rec_texts"] or [])
                confs.extend(res["rec_scores"] or [])
            else:
                # OCRResult object -> dung __getitem__ / .json
                data = res if isinstance(res, dict) else dict(res.json)
                if isinstance(data, dict) and "rec_texts" in data:
                    texts.extend(data["rec_texts"] or [])
                    confs.extend(data["rec_scores"] or [])
    except (TypeError, KeyError, AttributeError):
        texts, confs = [], []

    # API cu (paddleocr < 2.7): ocr.ocr(img) -> list[list[[box, (text, score)], ...]]
    if not texts:
        for page in results or []:
            for line in page or []:
                if len(line) >= 2 and line[1]:
                    texts.append(str(line[1][0]))
                    confs.append(float(line[1][1]))
    return texts, confs


def run_inference(ocr: Any, image_array: "np.ndarray") -> tuple[list[str], list[float]]:
    """Chay inference tren numpy array, tra ve (texts, confs)."""
    try:
        results = ocr.predict(image_array)
    except AttributeError:
        results = ocr.ocr(image_array, cls=True)
    return extract_text_and_conf(results)


def benchmark_one_image(
    ocr: Any,
    image: Path,
    rounds: int,
    sla_seconds: float,
    max_dim: int = MAX_IMAGE_DIM,
) -> dict[str, Any]:
    """Warm-up 1 luot, do lap 'rounds' lan, tra ve ket qua dict."""
    image_array = load_image_array(image, max_dim)

    # Warm-up: bo qua thoi gian luot dau
    run_inference(ocr, image_array)

    latencies: list[float] = []
    peak_ram_mb = track_ram_peak()
    final_texts: list[str] = []
    final_confs: list[float] = []

    for _ in range(rounds):
        start = time.perf_counter()
        texts, confs = run_inference(ocr, image_array)
        latencies.append(time.perf_counter() - start)
        final_texts, final_confs = texts, confs
        peak_ram_mb = max(peak_ram_mb, track_ram_peak())

    avg_latency = sum(latencies) / len(latencies)
    avg_conf = (sum(final_confs) / len(final_confs)) if final_confs else 0.0

    status = "PASS_SLA" if avg_latency <= sla_seconds else "WARN_SLA_EXCEEDED"
    return {
        "engine": "PP-OCRv6",
        "image_name": image.name,
        "latency_seconds": round(avg_latency, 4),
        "min_latency_seconds": round(min(latencies), 4),
        "max_latency_seconds": round(max(latencies), 4),
        "max_ram_mb": round(peak_ram_mb, 1),
        "avg_confidence": round(avg_conf, 4),
        "num_lines": len(final_texts),
        "status": status,
    }


def print_report(images: list[Path], results: list[dict[str, Any]]) -> None:
    """In bang ket qua va summary ra console."""
    print("=" * 86)
    print("RUNNING BENCHMARK: PP-OCR (PaddleOCR / OpenVINO)")
    print(f"Found {len(images)} images in sample_images/")
    print("-" * 86)

    name_width = max(len(img.name) for img in images)
    for idx, (image, result) in enumerate(zip(images, results), start=1):
        if result.get("latency_seconds") is not None:
            latency = f"{result['latency_seconds']:6.2f}s"
            ram = f"{result['max_ram_mb']:6.0f}MB"
            conf = f"{result.get('avg_confidence', 0.0):.3f}"
            short = "PASS" if result["status"] == "PASS_SLA" else "WARN"
        else:
            latency = "   N/A "
            ram = "   N/A "
            conf = "N/A"
            short = "ERROR"
        print(
            f"[{idx}/{len(images)}] {image.name:<{name_width}} "
            f"| Latency: {latency} | RAM: {ram} | Conf: {conf} | Status: {short}"
        )

    valid = [r for r in results if r.get("latency_seconds") is not None]
    print("-" * 86)
    if valid:
        total = sum(r["latency_seconds"] for r in valid)
        avg = total / len(valid)
        slowest = max(valid, key=lambda r: r["latency_seconds"])
        max_ram = max(r["max_ram_mb"] for r in valid)
        print(
            f"SUMMARY: Avg Latency: {avg:6.2f}s/img | Total Time: {total:6.2f}s "
            f"| Max RAM: {max_ram:5.0f}MB | Slowest: {slowest['image_name']}"
        )
    else:
        print("SUMMARY: Khong co anh nao chay thanh cong.")
    print("=" * 86)


def build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Tinh summary tu cac anh chay thanh cong."""
    valid = [r for r in results if r.get("latency_seconds") is not None]
    if not valid:
        return {
            "total_time_seconds": 0.0,
            "avg_latency_seconds": 0.0,
            "slowest_image": None,
            "max_ram_mb": 0.0,
            "num_images": 0,
        }
    total = sum(r["latency_seconds"] for r in valid)
    slowest = max(valid, key=lambda r: r["latency_seconds"])
    return {
        "total_time_seconds": round(total, 4),
        "avg_latency_seconds": round(total / len(valid), 4),
        "slowest_image": slowest["image_name"],
        "max_ram_mb": round(max(r["max_ram_mb"] for r in valid), 1),
        "num_images": len(valid),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark PP-OCR tren CPU")
    parser.add_argument("--image", type=Path, default=None, help="Anh test (mac dinh: toan bo sample_images/)")
    parser.add_argument("--rounds", type=int, default=3, help="So luot do cho moi anh (mac dinh: 3)")
    parser.add_argument("--lang", default="vi", help="Ngon ngu PaddleOCR (vd: vi, en, ch)")
    parser.add_argument("--sla", type=float, default=DEFAULT_CPU_SLA_SECONDS, help="Nguong SLA (giay)")
    parser.add_argument("--max-dim", type=int, default=MAX_IMAGE_DIM, help=f"Canh lon nhat sau downscale (default: {MAX_IMAGE_DIM}px)")
    parser.add_argument("--doc-ori", action=argparse.BooleanOptionalAction, default=not DEFAULT_NO_DOC_ORI, help="Bat/tat document orientation classifier (mac dinh: tat)")
    parser.add_argument("--doc-unwarp", action=argparse.BooleanOptionalAction, default=not DEFAULT_NO_UNWARP, help="Bat/tat UVDoc unwarping (mac dinh: tat)")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    images: list[Path] = [args.image] if args.image is not None else scan_images(SAMPLE_DIR)
    if not images:
        print("[ERROR] Khong tim thay anh trong sample_images/. Copy anh that roi chay lai.")
        return 1

    try:
        ocr = init_ocr(args.lang, no_doc_ori=not args.doc_ori, no_unwarp=not args.doc_unwarp)
    except Exception as exc:  # noqa: BLE001 - in loi ro rang, khong crash im lang
        print(f"[ERROR] Khoi tao PaddleOCR that bai: {exc}")
        return 1

    results: list[dict[str, Any]] = []
    for image in images:
        try:
            result = benchmark_one_image(ocr, image, args.rounds, args.sla, args.max_dim)
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] {image.name}: {exc}")
            result = {
                "engine": "PP-OCRv6",
                "image_name": image.name,
                "latency_seconds": None,
                "max_ram_mb": None,
                "status": "ERROR",
                "error": str(exc),
            }
        results.append(result)

    print_report(images, results)

    output_payload = {
        "engine": "PP-OCRv6",
        "benchmark_type": "CPU",
        "preprocessing": {
            "max_dim": args.max_dim,
            "doc_orientation": args.doc_ori,
            "doc_unwarping": args.doc_unwarp,
        },
        "summary": build_summary(results),
        "results": results,
    }
    output_json = RESULTS_DIR / "ppocr_result.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)

    print(f"\nKet qua da luu: {output_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())