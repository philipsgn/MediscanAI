# OCR MODEL TRAINING, FINE-TUNING & DEPLOYMENT GUIDE

**MediScanAI — Local On-Premise OCR Model Lifecycle Management**
**Author:** AI/MLOps Architecture Team
**Document Status:** Production Operational Standard
**Applies To:** All Engineers & AI Agents training, exporting, or deploying OCR models in MediScanAI.

---

## 1. TỔNG QUAN KIẾN TRÚC & NGUYÊN TẮC BẤT BIẾN (ARCHITECTURE INVARIANTS)

1. **Zero External VLM Dependency:**
   Toàn bộ quá trình nhận diện quang học (OCR) chạy 100% On-Premise trên CPU qua engine `onnxruntime` của PaddleOCR 3.7+ (PaddleX). Tuyệt đối không gọi API thị giác thương mại (Gemini Vision / GPT-4V).
2. **Zero Image Persistence:**
   Không lưu ảnh gốc, Base64, nhị phân, BLOB hay đường dẫn tệp vào database/disk trong quá trình suy luận.
3. **Training Artifacts ≠ Production Inference Artifacts:**
   Các tệp checkpoint huấn luyện (`.pdparams`, `.pth`, optimizer state) **KHÔNG** thể nạp trực tiếp vào Backend. Bắt buộc phải qua bước Export sang định dạng ONNX Runtime (`inference.onnx` + `inference.yml`).
4. **Deterministic Resolution & No Silent Fallback:**
   Nếu cấu hình sử dụng một phiên bản mô hình tùy biến nhưng tệp artifact bị thiếu hoặc hỏng, hệ thống kích hoạt cơ chế **Fail-Fast** (ném lỗi dừng lại), tuyệt đối không tự ý fallback ngầm về baseline.

---

## 2. QUY TRÌNH TOÀN BỘ VÒNG ĐỜI MÔ HÌNH (END-TO-END MODEL LIFECYCLE)

```text
┌─────────────────────────┐
│     1. DATASET PREP     │  - Phân tách riêng: Prescriptions (Toa thuốc) & Packaging (Bao bì)
│                         │  - Gán nhãn Bounding Box + Text Label (Unicode tiếng Việt)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   2. TRAINING / TUNING  │  - Huấn luyện trên GPU (Kaggle Notebook / Local GPU)
│      (Kaggle GPU)       │  - Base Model: PP-OCRv6_tiny_det & PP-OCRv6_tiny_rec
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   3. BEST CHECKPOINT    │  - Lựa chọn epoch có Character/Word Accuracy cao nhất
│                         │  - Trọng số thô: model.pdparams + model.pdopt
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 4. EXPORT ONNX ARTIFACT │  - Chuyển đổi sang inference model: inference.onnx + inference.yml
│                         │  - Kiểm tra Dictionary ký tự tiếng Việt
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  5. VALIDATION & BENCH  │  - Chạy benchmark đo SLA (< 15s/ảnh trên CPU)
│                         │  - So sánh Accuracy với Baseline hiện tại
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│    6. MODEL REGISTRY    │  - Đăng ký Manifest vào OCRModelRegistry (backend/app/services/ocr_model_registry.py)
│   & CONFIG ACTIVATION   │  - Thiết lập biến môi trường: OCR_ACTIVE_MODEL_VERSION / OCR_CUSTOM_*
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  7. BACKEND PRODUCTION  │  - OcrEngine nạp xác định qua ONNX Runtime CPU
│                         │  - Sẵn sàng Rollback nếu có Regression
└─────────────────────────┘
```

---

## 3. HƯỚNG DẪN CHI TIẾT DÀNH CHO KỸ SƯ / AGENT KHI HUẤN LUYỆN TRÊN KAGGLE

### Bước 1: Huấn luyện trên Kaggle Notebook
1. **Detection Fine-Tuning (PaddleOCR DBNet):**
   - Sử dụng backbone MobileNetV3 / PP-LCNet.
   - Huấn luyện trên tập ảnh toa thuốc hoặc bao bì thuốc đã được annotate.
2. **Recognition Fine-Tuning (PaddleOCR SVTR-LCNet):**
   - Sử dụng từ điển tiếng Việt đầy đủ dấu thanh (`dict.txt`).
   - Tối ưu hóa đặc thù tên hoạt chất, biệt dược và hàm lượng (mg, ml, mcg, UI).

### Bước 2: Xuất mô hình Inference sang ONNX
Sau khi hoàn tất training và có `best_accuracy.pdparams`:
1. Xuất mô hình sang Paddle Inference Model (`inference.pdmodel`, `inference.pdiparams`):
   ```bash
   paddlex --export_model --model_dir ./output/best_accuracy/ --save_dir ./exported_det/
   ```
2. Chuyển đổi sang ONNX Model (`inference.onnx` + `inference.yml`):
   ```bash
   paddle2onnx --model_dir ./exported_det/ --model_filename inference.pdmodel --params_filename inference.pdiparams --save_file ./production_det/inference.onnx --opset_version 14
   ```
3. Đảm bảo thư mục artifact thu được chứa đầy đủ:
   - `inference.onnx`: Trọng số và đồ thị tính toán ONNX.
   - `inference.yml`: Cấu hình transform ops (DecodeImage, NormalizeImage, ToCHWImage, DBPostProcess).

### Bước 3: Đặt Artifacts vào Repository
Tạo thư mục theo chuẩn versioning:
```text
ai/models/
├── prescription_v1/
│   ├── det/
│   │   ├── inference.onnx
│   │   └── inference.yml
│   └── rec/
│       ├── inference.onnx
│       ├── inference.yml
│       └── inference.json (hoặc dict.txt)
```

### Bước 4: Đăng Ký Mô Hình Vào Backend
Mở [`backend/app/services/ocr_model_registry.py`](file:///c:/Users/TanPhat/Documents/AI_E/MediscanAI/backend/app/services/ocr_model_registry.py) và khai báo:
```python
prescription_v1_manifest = ModelArtifactManifest(
    version="prescription_v1",
    model_type="fine_tuned",
    base_model="PP-OCRv6_tiny",
    domain="prescription",
    training_framework="PaddleOCR 3.7.0 / PaddleX 3.7.2",
    inference_runtime="onnxruntime",
    text_detection_model_dir="ai/models/prescription_v1/det",
    text_recognition_model_dir="ai/models/prescription_v1/rec",
    metrics={
        "character_accuracy": 0.965,
        "drug_name_exact_match": 0.942,
        "avg_cpu_latency_ms": 4850,
    },
    status="candidate",
)
ocr_model_registry.register_manifest(prescription_v1_manifest)
```

### Bước 5: Kích hoạt Mô hình Qua Biến Môi Trường
Trong file `backend/.env` hoặc Docker Compose:
```env
OCR_ACTIVE_MODEL_VERSION=prescription_v1
OCR_CUSTOM_DET_MODEL_DIR=ai/models/prescription_v1/det
OCR_CUSTOM_REC_MODEL_DIR=ai/models/prescription_v1/rec
```

---

## 4. QUY TRÌNH KIỂM CHỨNG & BENCHMARK GATE (PROMOTION CHECKLIST)

Trước khi chuyển trạng thái từ `candidate` sang `production`, mô hình bắt buộc phải vượt qua:

```bash
# 1. Chạy Unit Tests kiểm tra phân giải mô hình
pytest backend/tests/test_ocr_model_lifecycle.py -v

# 2. Chạy Integration Tests luồng OCR
pytest backend/tests/test_ocr_production_integration.py -v

# 3. Chạy Benchmark so sánh với Baseline PP-OCRv6
python test-benchmark/benchmark_ppocr.py
```

**Tiêu chí Chấp Thuận (Acceptance Criteria):**
- [x] Không có lỗi nạp mô hình trên CPU (`onnxruntime`).
- [x] Độ trễ trung bình trên CPU < 15.000 ms (SLA).
- [x] Độ chính xác nhận diện tên thuốc và hàm lượng cao hơn Baseline (> 90%).
- [x] Không phát sinh bất kỳ lỗi ghi đĩa hoặc vi phạm Zero Image Persistence.

---

## 5. QUY TRÌNH ROLLBACK AN TOÀN (ROLLBACK PROCEDURE)

Nếu phát hiện hiện tượng suy giảm độ chính xác (Regression) hoặc crash runtime trên Production:
1. Đặt biến môi trường về Baseline mặc định:
   ```env
   OCR_ACTIVE_MODEL_VERSION=ppocrv6_tiny_baseline
   OCR_CUSTOM_DET_MODEL_DIR=
   OCR_CUSTOM_REC_MODEL_DIR=
   ```
2. Khởi động lại dịch vụ:
   ```bash
   docker compose restart backend
   ```
3. Hệ thống ngay lập tức trở lại sử dụng mô hình Baseline PP-OCRv6 Tiny chuẩn mà không cần biên dịch lại mã nguồn hay huấn luyện lại.
