# Changelog — MediscanAI

All notable changes to the MediscanAI codebase are documented in this file.

---

## [Unreleased] - 2026-08-30

### 🚀 Integration: PP-OCRv6_tiny ONNX Engine & Clinical OCR Pipeline (Stage 2)

#### Added
- **PP-OCRv6_tiny ONNX Runtime (`ocr_engine.py`):**
  - Integrated `PP-OCRv6_tiny_det` and `PP-OCRv6_tiny_rec` with native ONNX CPU runtime, reducing inference latency from ~5.59s to **500–750ms** per image.
  - Added concurrency control via `asyncio.Semaphore(2)` in `OcrEngine`.
- **Structured Prescription Parsing (`backend/app/api/v1/endpoints/ocr.py`):**
  - Implemented regex pattern matching for structured prescriptions (`1. Tên thuốc (Drug): ...`).
  - Automatically isolates drug names and strengths, cleans punctuation, and aggregates subsequent dosage instruction lines (`Sáng... Trưa... Tối...`, `Số lượng...`, `Trước/sau ăn...`).
  - Added noise filter for header/metadata fields (`Họ và tên`, `Tuổi`, `Địa chỉ`, `Chẩn đoán`, `Bác sĩ`, `Ký tên`).
  - Maintained fallback support for unstructured receipts/snippets.
- **Packaging Stream Filter (`backend/app/api/v1/endpoints/ocr.py`):**
  - Added filter for manufacturer names (`Jamjoom Pharma`, `Bioiberica`), marketing slogans (`FOR ACNE TREATMENT`, `COMPLEMENTO ALIMENTICID`), and packaging specs (`30 GM`, `60 CAPSULAS`, `CN:...`).
- **Generic / Active Ingredient Normalization (`backend/app/services/normalization_service.py`):**
  - Added support for matching prescription lines written by active ingredient name (`Paracetamol 500mg`, `Ibuprofen 400mg`, `Omeprazol 20mg`).
  - **Medical Safety Rule:** When matched by ingredient (`match_method="ingredient"`), the original brand name from the prescription is strictly preserved and never overwritten by database brand names.
- **OpenFDA Exact Phrase Querying (`backend/app/services/drug_database.py`):**
  - Quoted search terms (`openfda.brand_name:"..."`) to eliminate false-positive OR-search matching on unrelated drugs.
- **Backlog Tracking (`ai/benchmark/ocr_models/BACKLOG.md`):**
  - Documented follow-up tasks for test set expansion ($N=10\text{--}15$), OpenFDA monitoring, DB expansion, and advanced packaging parsing.

#### Changed / Fixed
- **Image Preprocessing:** Removed destructive enhancement filters (`_enhance_receipt` and CLAHE distortion) from `_load_array()`, ensuring clean text inputs matching baseline benchmarks.
- **Documentation:** Updated `AGENTS.md` §B.1 to reflect the on-premise local OCR architecture pivot.

#### Verification & Benchmarks
- Benchmark & Audit reports:
  - [`ai/benchmark/ocr_models/MODEL_SOURCES.md`](file:///c:/Users/TanPhat/Documents/AI_E/MediscanAI/ai/benchmark/ocr_models/MODEL_SOURCES.md)
  - [`ai/benchmark/ocr_models/BACKLOG.md`](file:///c:/Users/TanPhat/Documents/AI_E/MediscanAI/ai/benchmark/ocr_models/BACKLOG.md)
- Unit tests: 109/109 tests passing (`109 passed in 2.93s`).
