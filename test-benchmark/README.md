# Test-Benchmark OCR Engines (CPU)

Bộ công cụ đo đạc performance của các OCR Engine trên CPU local cho Mediscan AI.

## Cấu trúc

```
test-benchmark/
├── sample_images/            # Copy ảnh thực tế vào đây
├── results/                  # Kết quả JSON sau khi chạy benchmark
├── benchmark_glm_ocr.py      # Đo GLM-OCR (GGUF) qua Ollama local
├── benchmark_ppocr.py        # Đo PP-OCR (PaddleOCR / OpenVINO) trên CPU
├── requirements-bench.txt    # Dependencies
└── README.md
```

## Hướng dẫn sử dụng

### Bước 1: Copy ảnh thực tế vào `sample_images/`

Copy 3-5 ảnh thực tế (toa thuốc in nhiệt, vỏ hộp thuốc, lọ/chai thuốc) vào
`test-benchmark/sample_images/`. Script quét động toàn bộ ảnh trong thư mục
(không cần khai báo tên), hỗ trợ đa định dạng: `.jpg`, `.jpeg`, `.png`,
`.webp` — kể cả đuôi in hoa `.JPG`/`.PNG`/`.WEBP`. Ảnh `.webp` được chuẩn
hóa bằng Pillow trước khi gửi tới OCR Engine.

### Bước 2: Cài dependencies

```bash
python -m venv .venv-bench        # khuyến nghị dùng venv riêng
pip install -r requirements-bench.txt
```

### Bước 3: Chạy benchmark

```bash
# GLM-OCR qua Ollama local (phải đang chạy: ollama serve)
python benchmark_glm_ocr.py
# hoặc chỉ định model/ảnh
python benchmark_glm_ocr.py --image sample_images/medicine_box.jpg --model qwen2.5vl:3b

# PP-OCR trên CPU
python benchmark_ppocr.py
# hoặc chỉ định ảnh/số lần đo/ngôn ngữ
python benchmark_ppocr.py --image sample_images/medicine_box.jpg --rounds 5 --lang vi
```

### Bước 4: So sánh kết quả trong `results/`

- `results/glm_ocr_result.json` — engine `GLM-OCR-GGUF`
- `results/ppocr_result.json` — engine `PP-OCRv6`

Xem xét `latency_seconds`, `max_ram_mb`, `avg_confidence` để chốt SLA. Mỗi file
JSON chứa mảng `results` (kết quả từng ảnh) kèm khối `summary` tổng hợp
(`total_time_seconds`, `avg_latency_seconds`, `slowest_image`, `max_ram_mb`).

## SLA & trạng thái

- Latency ≤ 15s (hoặc giá trị `--sla` tùy chỉnh) → `PASS_SLA`.
- Latency > 15s → `WARN_SLA_EXCEEDED`, script in
  `[WARNING] Exceeds CPU SLA (15s)!`.
- Ollama không chạy → script bắt `ConnectionError` rõ ràng, không crash;
  kết quả ghi vào JSON với `status: "ERROR"`.

## Lưu ý

- Benchmark chạy trên CPU, kết quả phụ thuộc cấu hình máy.
- PaddleOCR 3.7+ (PaddleX) bị ép chạy bằng **ONNX Runtime** engine trên
  device `cpu`, **không cần cài gói `paddlepaddle`** — tránh lỗi
  `Engine 'paddle_static' is unavailable`. PaddleX tự tải bản ONNX của model.
  *(Lưu ý: PaddleX 3.7 không có backend `openvino`.)*
- PaddleOCR khuyến nghị Python 3.8–3.11; nếu Python quá mới có thể cần cài
  bản `paddlepaddle` phù hợp.
