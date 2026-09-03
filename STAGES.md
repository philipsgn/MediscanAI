# 🚀 MEDISCAN AI - DỰ ÁN LỘ TRÌNH PHÁT TRIỂN CHI TIẾT (STAGES & VIBE-CODING ROADMAP)

Tài liệu này là **Single Source of Truth** cho tiến độ phát triển dự án **Mediscan AI**. Cấu trúc mỗi Task được chia nhỏ thành các gói công việc cụ thể (Context, Files, Dependencies, Prompt Mẫu) giúp **AI Coding Agent** và Developer triển khai mã nguồn tức thì (*Vibe-Coding Ready*).

---

## 📌 TỔNG QUAN HỆ THỐNG GIAI ĐOẠN (STAGES OVERVIEW)
[Stage 1: Base & Setup] ➔ [Stage 2: Pure Dual OCR Engine] ➔ [Stage 3: Local LLM Clinical & API] ➔ [Stage 4: Web UI & Smart Crop]
│
[Stage 7: Production] ➔ [Stage 7.5: Inference Hardening] ➔ [Stage 8: Auth System] ➔ [Stage 9: Personalized Onboarding] ➔ [Stage 10: History & Reminders] ➔ [Stage 11: OCR Model Lifecycle]

### 🟢 TOÀN BỘ CÁC STAGE 1 ĐẾN 11 ĐÃ HOÀN THÀNH VÀ KIỂM THỬ 100% PASS

| Stage | Tên Giai Đoạn | Trọng Tâm Kiến Trúc | Trạng Thái |
| :--- | :--- | :--- | :--- |
| **Stage 1** | **Base Environment & Data Schemas** | Khởi tạo Monorepo, Setup FastAPI + Next.js, Type Definitions | 🟢 Completed |
| **Stage 2** | **Multi-Format Pure OCR Engine (ONNX)** | Dual-Stream PP-OCRv6 ONNX (Prescription/Receipt & Packaging Stream) — User Pipeline 1 & 2 | 🟢 Completed |
| **Stage 3** | **Drug API, Normalization & LLM Assessment** | OpenFDA/Local Drug DB + RapidFuzz Mapping + Ollama Clinical Reasoning Engine | 🟢 Completed |
| **Stage 4** | **Interactive Web UI & Smart Crop** | Canvas Crop Box, Dynamic Forms, Dashboard & Active Cabinet | 🟢 Completed |
| **Stage 5** | **Centralized Cross-Evaluation Engine** | Multi-Layer Analysis Engine (Drug-Drug, Overdose, Condition) + Layer 4 Dosage Check (Task 5.5) | 🟢 Completed |
| **Stage 6** | **Polish, Medical Safety & Testing** | Medical Disclaimer Interceptor, E2E Flow Testing, UX Polish | 🟢 Completed |
| **Stage 7** | **Production & Docker Deployment** | Docker Compose, Backend Optimization, Web Desktop Launch | 🟢 Completed |
| **Stage 7.5** | **Production Inference Hardening** | Model Warmup, Thread-safety, Privacy Validation, Error Contracts | 🟢 Completed |
| **Stage 8** | **Authentication System** | Đăng ký/Đăng nhập username+password, JWT session, bảo vệ route | 🟢 Completed |
| **Stage 9** | **Personalized Health Onboarding** | Wizard khai hồ sơ y tế (ngày sinh/bệnh nền/dị ứng) gắn với tài khoản thật | 🟢 Completed |
| **Stage 10** | **Medication History & Reminders** | Tủ thuốc cá nhân (Cabinet), Lịch sử scan & Lịch nhắc nhở gắn user_id thật | 🟢 Completed |
| **Stage 11** | **OCR Model Lifecycle & Versioning** | On-Premise ONNX Model Registry, Manifest Contract, Fail-Fast Resolution & Rollback | 🟢 Completed |
| **Stage 12** | **Clinical Dataset Governance & DDI Coverage** | Clinical Safety Invariants (INV-12-01..04), DDInter v2.0 Dataset Governance, Coverage State Machine, Manifest Checksum | 🟢 Completed |

---

## 🛠️ CHI TIẾT TỪNG GIAI ĐOẠN TRIỂN KHAI (DETAILED IMPLEMENTATION)

---

### 🔹 STAGE 1: BASE ENVIRONMENT & DATA SCHEMAS SETUP
> **Mục tiêu:** Dựng khung móng Monorepo, cấu hình biến môi trường, định nghĩa toàn bộ Type Interface & Data Schemas dùng chung.

* **File tác động chính:**
  - `backend/app/main.py`
  - `backend/app/core/config.py`
  - `backend/app/schemas/` (Package schemas chuyển đổi từ `schemas.py`)
  - `frontend/src/types/medication.ts`

- [x] **Task 1.1: Khởi tạo Backend Framework (FastAPI + Pydantic v2)**
  - **Mô tả:** Khởi tạo FastAPI app, cấu hình CORS (cho phép Next.js Dev Server `localhost:3000`), load `.env`.
  - **Agent Action:** Cài đặt `fastapi`, `uvicorn`, `pydantic-settings`, `python-dotenv`.

- [x] **Task 1.2: Xây dựng Schema Dữ liệu Chuẩn (Data Contracts)**
  - **Mô tả:** Khai báo đầy đủ Schemas cho `DrugItem`, `PrescriptionData`, `UserProfile`, `InteractionAlert`, và `EvaluationResponse`.
  - **Agent Action:** 
    - Đảm bảo Match 100% giữa Pydantic models trong `backend/app/schemas/` và TypeScript interfaces trong `frontend/src/types/medication.ts`.

- [x] **Task 1.3: Dựng Cơ sở Dữ liệu Thuốc Việt Nam Mẫu (Local Drug Mock DB)**
  - **Mô tả:** Tạo file JSON/SQLite chứa danh mục 100+ thuốc phổ biến tại Việt Nam (Tên thương mại, Hoạt chất gốc, Hàm lượng chuẩn, Liều tối đa/ngày).
  - **Agent Action:** Tạo file `backend/app/data/vietnam_drugs_db.json`.

---

### 🔹 STAGE 2: DUAL-STREAM PURE OCR ENGINE (ONNX RUNTIME)
> **Mục tiêu:** Xây dựng Engine OCR cục bộ (On-Premise) trích xuất văn bản từ **Toa thuốc/Hóa đơn in nhiệt** và **Vỏ hộp/Lọ thuốc**, hoàn toàn loại bỏ phụ thuộc vào VLM bên thứ 3 (Gemini Vision) để bảo mật và tối ưu chi phí.

* **File tác động chính:**
  - `backend/app/services/ocr_engine.py`
  - `backend/app/api/v1/endpoints/ocr.py`
  - `test-benchmark/benchmark_ppocr.py`

- [x] **Task 2.1: Triển khai Stream OCR Toa Thuốc & Hóa Đơn In Nhiệt (Prescription / Receipt Stream)**
  - **Mô tả:** Nhận ảnh toa thuốc hoặc hóa đơn in nhiệt mờ/nhăn/font dot-matrix, xử lý preprocessing downscale max cạnh 1600px và chạy qua PP-OCRv6 ONNX Engine.
  - **Agent Action:** Viết handler `extract_prescription_receipt(image_bytes)` trong `ocr_engine.py` tối ưu cho các dòng chữ in phẳng.

- [x] **Task 2.2: Triển khai Stream OCR Vỏ Hộp / Lọ Thuốc (Packaging Label Stream)**
  - **Mô tả:** Nhận ảnh vỏ hộp/lọ thuốc (chữ 3D, bóng sáng, cong vồng), xử lý CLAHE tăng tương phản, điều hướng khung hình và unwarping.
  - **Agent Action:** Viết handler `extract_packaging_label(cropped_image_bytes)` trong `ocr_engine.py`.

- [x] **Task 2.3: Benchmark Tối Ưu Tốc Độ Preprocessing & Latency Engine**
  - **Mô tả:** Tối ưu hóa thời gian xử lý OCR đạt SLA (< 15s) bằng cách tắt các bước xoay hướng/unwarp không cần thiết trên CPU và downscale ảnh.
  - **Agent Action & Kết quả:**
    - Cập nhật `test-benchmark/benchmark_ppocr.py`: downscale ảnh (`MAX_IMAGE_DIM=1600`) + mặc định tắt `doc-orientation classifier` và `UVDoc unwarping`.
    - **Kết quả:** Giảm **Avg Latency từ 29s xuống 5.59s/ảnh** (6 ảnh × 3 rounds, 100% PASS SLA). Steady-state API đạt ~3.4s/request.

- [x] **Task 2.4: Khởi tạo Endpoint Production OCR API & Cấu trúc Backend Service**
  - **Mô tả:** Tái cấu trúc Backend FastAPI theo chuẩn Production, tách biệt endpoint OCR và khai báo lifespan event giải phóng tài nguyên CPU/ONNX.
  - **Agent Action:**
    - Tạo `backend/app/api/v1/endpoints/ocr.py` cung cấp endpoint `POST /api/v1/ocr/scan`.
    - Thêm cấu hình feature toggle trong `backend/app/core/config.py` (`OCR_DOC_ORIENTATION`, `OCR_DOC_UNWARPING`).
    - Loại bỏ hoàn toàn `vision_service.py` cũ và cập nhật `main.py` dùng bộ router chuẩn v1.

---

### 🔹 STAGE 3: DRUG DATABASE API, NORMALIZATION & LOCAL CLINICAL LLM
> **Mục tiêu:** Chuẩn hóa chuỗi ký tự OCR thô sang ID Dược phẩm chuẩn (Vietnamese DB / OpenFDA API) và sử dụng **Local LLM (Ollama)** để thực hiện đánh giá lâm sàng (Clinical Assessment).

* **File tác động chính:**
  - `backend/app/services/drug_database.py`
  - `backend/app/services/normalization_service.py`
  - `backend/app/services/clinical_service.py`
  - `backend/app/schemas/ocr_schema.py`

- [x] **Task 3.1: Tích hợp CSDL Dược Mở (OpenFDA & Local Drug Database API)**
  - **Mô tả:** Dựng service kết nối CSDL 100+ thuốc Việt Nam và tích hợp API OpenFDA tra cứu thông tin hoạt chất, brand name, hàm lượng và cảnh báo.
  - **Agent Action:** Viết `backend/app/services/drug_database.py` hỗ trợ tìm kiếm đa tầng theo Brand Name và Active Ingredient.

- [x] **Task 3.2: Engine Chuẩn Hóa Dữ Liệu Dược (Fuzzy Matching Normalization)**
  - **Mô tả:** Áp dụng thuật toán Fuzzy Matching (`rapidfuzz`) để map văn bản OCR bị lỗi typo/thiếu nét sang danh mục thuốc chuẩn trong Database.
  - **Agent Action:** Viết `backend/app/services/normalization_service.py` thực hiện mapping 3 tầng (Exact Match ➔ Fuzzy Match Brand ➔ Active Ingredient Fallback).

- [x] **Task 3.3: Tích hợp Engine Phân Tích Lâm Sàng Bằng Local LLM (Clinical Reasoning Engine)**
  - **Mô tả:** Truyền danh sách thuốc đã normalize + Hồ sơ bệnh nền vào LLM chạy cục bộ qua Ollama (`phi3:mini`, `qwen2.5:0.5b` hoặc `qwen2.5vl:3b`) để tự động phát hiện Tương tác thuốc, Chống chỉ định và Quá liều.
  - **Agent Action:** 
    - Tạo `backend/app/services/clinical_service.py` với cấu trúc JSON Prompt nghiêm ngặt, có cơ chế Fallback sang OpenAI API nếu thiếu Local LLM.
    - Kết hợp kết quả OCR + Normalization + Clinical Assessment trả về trong response duy nhất tại `POST /api/v1/ocr/scan`.

> 📌 **Backlog có điều kiện:** Pipeline train YOLO 3-class (brand_name/active_ingredient/strength detection) đã được build thử nghiệm và archive tại nhánh `experimental/yolo-packaging-detection` (ngày 29/08/2026). Quyết định Architect: **KHÔNG kích hoạt** trừ khi đo được tỷ lệ `is_verified=False` sau Local DB + OpenFDA tier-4 (F3.4) vượt ngưỡng đáng kể trong vận hành thật. Lý do tạm dừng: kiến trúc layout-based không phù hợp với bố cục vỏ hộp đa dạng theo hãng; hệ thống hiện tại dùng OCR + Fuzzy Match content-based đã đủ dùng.

---

### 🔹 STAGE 4: INTERACTIVE WEB UI & SMART CROP COMPONENT
> **Mục tiêu:** Xây dựng giao diện Web Desktop trực quan, cho phép Upload, Cropping ảnh vỏ hộp, chỉnh sửa Human-in-the-Loop và Quản lý Tủ thuốc.

* **File tác động chính:**
  - `frontend/src/app/scan/page.tsx`
  - `frontend/src/components/scan/SmartCropModal.tsx`
  - `frontend/src/components/scan/DrugVerificationForm.tsx`
  - `frontend/src/components/cabinet/ActiveCabinet.tsx`

- [x] **Task 4.1: Dựng Component Smart Crop Ảnh Vỏ Hộp Thuốc**
  - **Mô tả:** Cho phép người dùng kéo thả khoanh vùng Tên & Hàm lượng trên ảnh vỏ hộp thuốc trước khi gửi Backend.
  - **Agent Action:** Tích hợp `react-image-crop` hoặc HTML5 Canvas Custom Component trong `SmartCropModal.tsx`.

- [x] **Task 4.2: Dựng Dynamic Verification Form (Human-in-the-Loop Step)**
  - **Mô tả:** Hiển thị kết quả AI đọc được. Đánh dấu màu đỏ/vàng vùng nghi ngờ. Bổ sung **One-Tap Dosage Selector** cho vỏ hộp thuốc (Sáng - Trưa - Chiều - Tối) + Auto-complete Search từ điển.
  - **Agent Action:** Xây dựng Component `DrugVerificationForm.tsx` bằng React Hook Form + Tailwind CSS (hand-rolled components qua helper `cn()`, không dùng thư viện Shadcn/Radix — quyết định Architect tại Stage 4 Audit F4.5: giữ nguyên stack hiện có vì đã ổn định, tuân thủ Strict Mode, không `any`; tránh rework không cần thiết).

- [x] **Task 4.3: Dựng Màn hình Tủ Thuốc Cá Nhân (Active Medication Cabinet)**
  - **Mô tả:** Nơi tập hợp tất cả các thuốc đã quét từ Toa 1, Toa 2, Vỏ hộp và Nhập tay thành 1 danh sách duy nhất.
  - **Agent Action:** Tạo UI hiển thị Card danh sách thuốc, cho phép Xóa/Sửa/Bật-Tắt hoạt động của từng viên thuốc.

---

### 🔹 STAGE 5: CENTRALIZED CROSS-EVALUATION ENGINE
> **Mục tiêu:** Xây dựng "Trái tim" thuật toán phân tích tương tác chéo y tế 3 lớp (Thuốc-Thuốc, Quá liều, Thuốc-Bệnh nền).

* **File tác động chính:**
  - `backend/app/services/evaluation_service.py`
  - `backend/app/api/v1/evaluate.py`
  - `frontend/src/components/report/InteractionAlertCards.tsx`

- [x] **Task 5.1: Thuật Toán Cảnh Báo Quá Liều Hoạt Chất (Overdose Layer)**
  - **Mô tả:** Cộng dồn hàm lượng hoạt chất gốc từ TẤT CẢ các thuốc trong Tủ Thuốc theo ngày. So sánh với Liều Tối Đa An Toàn.
  - **Ví dụ Logic:** `Panadol (500mg)` + `Efferalgan Codeine (500mg)` ➔ Tổng `Paracetamol = 1000mg/lần`. Cảnh báo nếu tổng ngày > 4000mg.

- [x] **Task 5.2: Thuật Toán Cảnh Báo Tương Tác Thuốc - Thuốc (Drug-Drug Layer)**
  - **Mô tả:** Tra cứu ma trận tương tác giữa các cặp Hoạt chất gốc có trong Tủ thuốc.
  - **Agent Action:** Tạo bộ Rule-engine tra cứu cặp xung đột (vd: *Aspirin + Ibuprofen*, *Kháng sinh Ciprofloxacin + Canxi*).

- [x] **Task 5.3: Thuật Toán Cảnh Báo Thuốc - Bệnh Nền (Drug-Condition Layer)**
  - **Mô tả:** Đối chiếu danh sách Hoạt chất gốc với `UserProfile` của bệnh nhân (vd: Tiền sử Cao huyết áp, Viêm loét dạ dày, Bệnh gan/thận).

- [x] **Task 5.4: Render Giao Diện Báo Cáo Phân Cấp Cảnh Báo (Severity UI)**
  - **Mô tả:** Hiển thị kết quả phân tích theo 3 cấp độ màu: 🔴 **HIGH (Đỏ)**, 🟡 **MEDIUM (Vàng)**, 🟢 **LOW (Xanh)**.
  - **Agent Action:** Dựng Component `InteractionAlertCards.tsx` có bộ lọc theo Severity level.

- [x] **Task 5.5: Thuật Toán Layer 4 — Đối Chiếu Liều Dùng Thực Tế vs. Liều Khuyến Cáo (Dosage Appropriateness Layer)**
  - **Mô tả:** Bổ sung layer thứ 4 vào `evaluation_service.py`:
    - Với **User Pipeline 2** (toa thuốc): so sánh `dosage_instruction` đã trích xuất từ toa với liều khuyến cáo chuẩn theo hoạt chất, tuổi và bệnh nền (`UserProfile`). Không kết luận toa "sai" — chỉ cảnh báo tham khảo, khuyến nghị xác nhận lại với bác sĩ.
    - Với **User Pipeline 1** (vỏ hộp): so sánh liều + buổi uống User tự nhập ở Smart Form với liều khuyến cáo chuẩn.
    - Trả về danh sách `DosageCheckResult` (theo schema đã định nghĩa tại `ARCHITECTURE.md` mục 5.1) và tổng hợp toàn bộ 4 layer thành `final_summary`.
  - **Agent Action:** 
    - Mở rộng `backend/app/services/evaluation_service.py` thêm hàm `check_dosage_appropriateness()`.
    - Mở rộng `backend/app/schemas/` thêm `DosageCheckResult`, cập nhật `EvaluationResponse` thêm trường `dosage_checks` và `final_summary`.
    - Đồng bộ `frontend/src/types/medication.ts` (`IDosageCheckResult`, cập nhật `IEvaluationResponse`).
    - Cập nhật `InteractionAlertCards.tsx` (hoặc component mới `DosageCheckCard.tsx`) để hiển thị kết quả Layer 4 và banner Summary/lời khuyên cuối cùng ở đầu báo cáo.
  - **File tác động:** `backend/app/services/evaluation_service.py`, `backend/app/schemas/evaluation_schema.py`, `frontend/src/types/medication.ts`, `frontend/src/components/report/DosageCheckCard.tsx`.
  - **Kết quả:** Đã triển khai `dosage_guidelines.json` (15 hoạt chất, có nguồn), `check_dosage_appropriateness()` phân biệt chống chỉ định (`contraindication_tag`) vs thiếu dữ liệu, `DosageCheckResult` + `final_summary` wire-through đầy đủ tại `/evaluate`. Kèm F3.7 (`strength_mismatch_warning`) đóng cùng đợt. 106/106 tests pass, E2E HTTP thật xác nhận.

---

### 🔹 STAGE 6: POLISH, MEDICAL SAFETY & E2E TESTING
> **Mục tiêu:** Hoàn thiện trải nghiệm người dùng, đảm bảo tính pháp lý y tế và kiểm thử toàn bộ hệ thống.

* **File tác động chính:**
  - `frontend/src/components/common/MedicalDisclaimerModal.tsx`
  - `backend/tests/test_evaluation_engine.py`

- [x] **Task 6.1: Tích hợp Interceptor Disclaimer Y tế Bắt Buộc**
  - **Mô tả:** Bắt buộc người dùng tích chọn *"Tôi đã hiểu Mediscan AI chỉ mang tính tham khảo và không thay thế chỉ định Bác sĩ"* trước khi bấm nút **"Đánh Giá Tương Tác"**.
  - **Agent Action:** Dựng Modal Interceptor lưu trạng thái vào `localStorage` hoặc Session State.
  - **Kết quả:** Đã dựng `frontend/src/components/common/MedicalDisclaimerModal.tsx` — Modal bắt buộc đồng ý checkbox trước khi phân tích, lưu trạng thái vào `localStorage` (`mediscan_disclaimer_accepted`), hỗ trợ mở lại từ Header/Báo cáo qua `openMedicalDisclaimerModal()`, và gate chặn trong `ActiveCabinet.handleAnalyze`.

- [x] **Task 6.2: Viết Unit Test & Integration Test Cho Core Logic**
  - **Mô tả:** Kiểm thử độ chính xác của Engine phân tích với 40+ kịch bản đơn thuốc thực tế phức tạp.
  - **Agent Action:** Dùng `pytest` cho Backend FastAPI.
  - **Kết quả:** Xóa bỏ `test_vision.py` đã cũ, cập nhật `test_evaluation_engine.py` và các test suite API. Tổng cộng **42 backend tests pass 100%** (`python -m pytest`). Bao phủ cả Dual OCR, Normalization, Rule-based Assessment và Edge Cases.

- [x] **Task 6.3: UX Polish & Responsive Adjustments**
  - **Mô tả:** Tối ưu hóa hiệu ứng loading skeleton khi AI đang đọc ảnh, xử lý lỗi mất mạng (Network Failures), hiển thị Tooltip giải thích từ ngữ y khoa.
  - **Kết quả:** Loading Skeleton 3-bước (tiếp nhận ảnh ➔ OCR trích xuất ➔ LLM/Normalization) trên màn hình Scan; Toast Notification cho lỗi mất kết nối Backend, timeout, định dạng ảnh sai & quá dung lượng 15MB; Form Hồ sơ Bệnh nhân trong Tủ thuốc; Nút mở lại Điều khoản Miễn trừ Y tế trên mọi màn hình.

---

### 🔹 STAGE 7: PRODUCTION DOCKERIZATION & DEPLOYMENT
> **Mục tiêu:** Đóng gói ứng dụng thành Container sẵn sàng triển khai Beta Production.

* **File tác động chính:**
  - `Dockerfile.backend`
  - `Dockerfile.frontend`
  - `docker-compose.yml`

- [x] **Task 7.1: Viết File Dockerfile Cho Backend & Frontend**
  - **Agent Action:** Tối ưu Multi-stage build cho Next.js và Python FastAPI để giảm dung lượng Image.
  - **Kết quả:** Tạo `Dockerfile.backend` (builder compile wheels ➔ runtime python:3.12-slim, non-root user, healthcheck) và `Dockerfile.frontend` (deps ➔ builder ➔ runner node:20-alpine, Next.js **Standalone mode** `output: "standalone"`, non-root user, healthcheck). Bổ sung `pydantic-settings`, `rapidfuzz`, `onnxruntime`, `opencv-python-headless` vào `backend/requirements.txt`.

- [x] **Task 7.2: Cấu hình Docker Compose Local Production**
  - **Mô tả:** Khởi chạy Backend, Frontend và Local Database chỉ với 1 lệnh `docker compose up --build`.
  - **Kết quả:** Tạo `docker-compose.yml` khởi chạy 2 services `backend` (Port 8000) & `frontend` (Port 3000) trên network bridge `mediscan-network`, truyền env vars an toàn (API Keys & Ollama URL đọc từ host `.env`), `restart: unless-stopped`. Xác thực thành công bằng `docker compose config`.

---

### 🔹 STAGE 7.5: PRODUCTION INFERENCE HARDENING & PRIVACY VALIDATION
> **Mục tiêu:** Đảm bảo Pipeline PP-OCRv6 chạy ổn định, thread-safe, không lưu ảnh xuống đĩa (Privacy RAM-Only) và xử lý lỗi đồng nhất trước khi chuyển sang các hệ thống phân quyền (Auth).

* **File tác động chính:**
  - `backend/app/services/ocr_engine.py`
  - `backend/app/api/v1/endpoints/ocr.py`
  - `backend/app/main.py`
  - `ARCHITECTURE.md`

- [x] **Task 7.5.1: Thread-Safety & True Model Warmup**
  - **Mô tả:** Thêm `threading.Lock` bảo vệ khởi tạo lazy của PaddleOCR. Chạy ảnh dummy qua `predict()` trong hàm `warmup` để nạp kernels ONNX vào RAM ở lần đầu khởi động server.
- [x] **Task 7.5.2: Inference Error Isolation**
  - **Mô tả:** Bắt lỗi OCR Inference (exception từ `predict()`) để tránh lỗi 500 chung chung. Trả về Error Contract chuẩn có chứa `OCR_INFERENCE_FAILED`.
- [x] **Task 7.5.3: Zero Image Persistence Verification**
  - **Mô tả:** Audit và test đảm bảo tuyệt đối không có bytes ảnh nào rò rỉ ra ổ cứng ở bất kỳ bước nào trong quy trình.

---

### 🔹 STAGE 8: AUTHENTICATION SYSTEM
> **Mục tiêu:** Xây dựng hệ thống Đăng ký/Đăng nhập bằng tài khoản thật (Username + Password). Sử dụng JWT session, mã hóa mật khẩu bằng Bcrypt, Rate Limiting chống brute-force, và chuẩn hóa Error Contract 6-key cho toàn bộ Auth layer.

* **File tác động chính:**
  - Backend: `app/core/config.py`, `app/services/auth_service.py`, `app/schemas/user_schema.py`, `app/api/v1/endpoints/auth.py`, `app/models/user.py`
  - Frontend: `src/types/auth.ts`, `src/services/authApi.ts`, `src/stores/authStore.ts`, `src/app/login/page.tsx`, `src/app/register/page.tsx`

* **Entry Criteria:**
  - Stage 7.5 Production Inference Hardening & Privacy Validation: PASS (155/155 tests passed).
  - Database schema migration cho bảng `users` đã tồn tại và sẵn sàng.

* **Security Acceptance Criteria:**
  - Mật khẩu bắt buộc băm bằng `bcrypt` trước khi lưu vào DB; không bao giờ log hoặc trả về plaintext password / hash.
  - JWT Access Token (HS256) ký bằng `JWT_SECRET` bắt buộc từ môi trường (validator chặn hardcoded/empty secret).
  - Refresh Token hỗ trợ cấp mới Access Token mà không yêu cầu user login lại.
  - Rate limiting (5 req/min) bảo vệ các endpoint nhạy cảm (`/auth/login`, `/auth/register`).
  - Error Response tuân thủ 100% unified contract 6-key (`error_code`, `message`, `service`, `stage`, `request_id`, `retryable=False`).
  - Privacy Invariant: Tuyệt đối không log credentials, raw tokens hoặc Authorization header.

* **Detailed Tasks:**
  - [x] **Task 8.1: Backend Auth Core & Unified Error Contract**
    - **Mô tả:** Chuẩn hóa `AuthService` và `auth.py` router tích hợp 6-key error contract, `X-Request-ID` propagation, validate password strength (min 6 chars), sanitize inputs. Đã hoàn tất và đạt 157/157 tests PASS.
  - [x] **Task 8.2: Backend Token Lifecycle & Security Hardening**
    - [x] **Task 8.2.1 — Access Token Validation Hardening:** Bắt buộc `algorithms=["HS256"]` explicit, kiểm tra đầy đủ claims (`sub`, `exp`, `iat`, `type="access"`), đối soát `user.is_active == True`, trả lỗi `UNAUTHORIZED` / `INVALID_TOKEN` chuẩn 6-key.
    - [x] **Task 8.2.2 — Refresh Token Lifecycle & Replay Hardening:** Enforce strict `type == "refresh"`, chặn triệt để access token lọt vào `/auth/refresh`, kiểm tra expiration, và giữ semantic cấp mới access token ổn định.
    - [x] **Task 8.2.3 — Protected Route Security & State Isolation:** Kiểm tra `get_current_user` và `get_optional_current_user` trên toàn bộ protected routes (OCR, Profile, History, Reminders); chặn tài khoản bị vô hiệu hóa (`is_active=False`).
    - [x] **Task 8.2.4 — Logout & Revocation Boundary Definition:** Xác định kiến trúc Stateless Client-Side Token Discard cho Stage 8 (xóa token ở client state, không lưu state session server-side), ghi nhận ranh giới bảo mật và khả năng mở rộng denylist trong tương lai.
    - [x] **Task 8.2.5 — Comprehensive Token Security Test Suite:** Bổ sung các bài test chuyên biệt: chữ ký bị sửa đổi, thuật toán giả mạo (`alg:none`), token hết hạn, user bị khóa (`is_active=False`), token type confusion, và request tracing. Đã đạt 164/164 tests PASS.
  - [x] **Task 8.3: Frontend Auth State & UI Integration**
    - [x] **Task 8.3.1 — Token Storage Architecture & Session Lifecycle:** Quản lý an toàn Access Token và Refresh Token trong Web Storage & Session Cookie đồng bộ với Next.js Middleware.
    - [x] **Task 8.3.2 — Axios Auto-Refresh Interceptor & Request Queue Hardening:** Khóa `isRefreshing` và hàng đợi `failedQueue` ngăn chặn race condition khi nhiều request 401 đồng thời; xử lý triệt để loop refresh.
    - [x] **Task 8.3.3 — Zustand Auth State Machine & Hydration Protection:** State machine quản lý `APP_BOOT ➔ AUTH_LOADING ➔ AUTHENTICATED / UNAUTHENTICATED`, đồng bộ trạng thái khi logout hoặc hết hạn session.
    - [x] **Task 8.3.4 — Next.js Route Protection & Anti-Flash Guard:** Middleware & AuthGuard ngăn ngừa flash dữ liệu trước khi hydrate; điều hướng theo `isProfileCompleted` (`/onboarding` vs `/cabinet`).
    - [x] **Task 8.3.5 — Unified Error Contract UI Normalization:** Chuẩn hóa parser bóc tách 6-key error (`detail.error_code`, `detail.message`) hiển thị Toast và Form Alert thân thiện. Đã verify Next.js build PASS và Full Backend Regression 164/164 PASS.

* **Definition of Done (DoD):**
  - 100% Unit & Integration test cho Auth pass xanh (Register, Duplicate Check, Login, Wrong Password, Refresh Token, Rate Limit, Protected Route Rejection).
  - Full backend regression suite không bị ảnh hưởng (155+ tests pass).

---

### 🔹 STAGE 9: PERSONALIZED HEALTH ONBOARDING
> **Mục tiêu:** Di chuyển và cá nhân hóa Wizard khai báo hồ sơ y tế (Ngày sinh, Cân nặng, Bệnh nền, Dị ứng) để nó gắn liền với tài khoản thật vừa đăng ký.

* **File tác động chính:**
  - Backend: Liên kết UserProfile với tài khoản người dùng (`user_id`).
  - Frontend: Chỉnh sửa lại `userProfileStore.ts` để đọc/ghi từ Backend API thay vì chỉ lưu `localStorage`. Cập nhật `OnboardingWizard`.

- [x] **Task 9.1: Backend — UserProfile CRUD APIs & Error Contract Hardening**
  - Chuẩn hóa endpoints: `GET/POST/PUT /profile/me` và giữ tương thích `POST/PUT /profile`.
  - Enforce `current_user.id` từ JWT, loại bỏ hoàn toàn nguy cơ IDOR.
  - Chuẩn hóa phản hồi 404 sang Unified 6-Key Error Contract (`PROFILE_NOT_FOUND`).
  - Thắt chặt validation schemas (`age >= 1`, `height_cm > 0`, `weight_kg > 0`).
  - Tự động tính BMI an toàn và kích hoạt transaction cập nhật `is_profile_completed = True`.
- [x] **Task 9.2: Frontend — Sync Onboarding Flow with Auth**
  - Chuyển `userProfileStore.ts` sang Zustand memory, Backend REST API là Single Source of Truth duy nhất (loại bỏ localStorage fallback).
  - Đồng bộ `logout()` và 401 session expiration xóa sạch Profile state và legacy cache.
  - Loại bỏ hoàn toàn bypass client-side fake completion trong `ClinicalOnboardingWizard.tsx`.
  - Đã verify Next.js build PASS và Full Backend Regression đạt 169/169 PASS.

---

### 🔹 STAGE 10: MEDICATION HISTORY & REMINDERS (TRANG 3 — QUẢN LÝ USER) `🟢 Completed`
> **Mục tiêu:** Bổ sung Trang 3 hoàn chỉnh cho việc quản lý User: Lịch sử các lần quét/đánh giá, Tủ thuốc cá nhân (Cabinet) và Nhắc nhở uống thuốc. Dữ liệu gắn trực tiếp với `user_id` thật từ JWT session với phân trang, bảo vệ IDOR và Zero Image Persistence.

* **File tác động chính:**
  - `backend/app/models/medication.py`, `backend/app/models/reminder.py`, `backend/app/models/history.py`
  - `backend/alembic/versions/b2c3d4e5f6g7_003_user_medications_and_reminder_link.py`
  - `backend/app/schemas/history_reminder_schema.py`
  - `backend/app/api/v1/endpoints/history.py`, `backend/app/api/v1/endpoints/reminders.py`, `backend/app/api/v1/endpoints/medications.py`
  - `backend/app/services/history_service.py`, `backend/app/services/reminder_service.py`, `backend/app/services/medication_service.py`
  - `frontend/src/app/history/page.tsx`, `frontend/src/components/management/HistoryTimeline.tsx`, `frontend/src/components/management/ReminderSchedule.tsx`
  - `frontend/src/store/historyReminderStore.ts`, `frontend/src/store/authStore.ts`

- [x] **Task 10.1: Backend — Lưu & Truy Vấn Lịch Sử Quét Thuốc Gắn Với User ID (Internal Write Only)**
  - Tự động ghi Lịch sử phiên quét (Zero Image) nội bộ sau khi `POST /evaluate` thành công; loại bỏ hoàn toàn Public Write API.
  - Phân trang `PaginatedScanHistoryResponse` (`items`, `total`, `limit`, `offset`, `has_more`), lọc severity (`HIGH`, `MEDIUM`, `LOW`, `ALL`).
  - Hỗ trợ `GET /history/{id}` tái dựng báo cáo chi tiết và `DELETE /history/{id}` bảo vệ IDOR tuyệt đối.

- [x] **Task 10.2: Backend — Tủ Thuốc (Cabinet) & Quản Lý Nhắc Nhở Uống Thuốc Cho Tài Khoản**
  - Khởi tạo bảng `user_medications` trong PostgreSQL; liên kết FK `reminders.medication_id` với cascade delete.
  - Chống IDOR/Cross-user linking: Kiểm tra đồng thời `reminder.user_id == current_user.id` và `medication.user_id == current_user.id`.
  - Validate định dạng giờ `reminder_time` chuẩn `HH:MM` 24h; tính toán chính xác Adherence Stats (`taken` / `skipped`).
  - Toàn bộ lỗi 404 tuân thủ Unified 6-Key Error Contract (`HISTORY_NOT_FOUND`, `REMINDER_NOT_FOUND`, `MEDICATION_NOT_FOUND`).

- [x] **Task 10.3: Frontend — Trang Quản Lý User Hoàn Chỉnh (Tủ Thuốc, Lịch Sử & Nhắc Nhở)**
  - `HistoryTimeline.tsx`: Phân trang, lọc mức độ cảnh báo, tái dựng báo cáo lâm sàng chi tiết không cần ảnh gốc, hỗ trợ khôi phục vào Tủ thuốc.
  - `ReminderSchedule.tsx`: Quản lý thời gian biểu uống thuốc theo 4 khung giờ, toggle active/inactive, ghi nhật ký tuân thủ điều trị.
  - Đồng bộ `authStore.logout()` dọn sạch 100% dữ liệu lịch sử, nhắc nhở và tủ thuốc trên client memory.

- [x] **Task 10.4: Thông Báo Nhắc Nhở (Notification Delivery)**
  - Cơ chế Web Desktop: In-app background timer (polling định kỳ) + Browser Notification API (khi được cấp quyền).
  - Ranh giới kỹ thuật đã công bố: Không cam kết gửi notification khi tắt hoàn toàn trình duyệt hoặc OS deep sleep (sẽ hỗ trợ Push Notifications APNs/FCM trên Mobile App).
  - Toàn bộ 176/176 Backend Tests PASS và Next.js production build PASS 100%.

---

### 🔹 STAGE 11: OCR MODEL LIFECYCLE, FINE-TUNING & DEPLOYMENT GATE `🟢 Completed`
> **Mục tiêu:** Chuẩn hóa toàn bộ vòng đời OCR Model từ Training Checkpoint (Kaggle GPU) → Inference ONNX Export → Versioned Registry → Deterministic Loading → Benchmark & Fail-Fast Rollback.

* **File tác động chính:**
  - `backend/app/services/ocr_model_registry.py` (Model Registry & Manifest Schema)
  - `backend/app/services/ocr_engine.py` (Deterministic Model Resolution)
  - `backend/app/core/config.py` (`OCR_ACTIVE_MODEL_VERSION`, `OCR_CUSTOM_*`)
  - `docs/OCR_MODEL_TRAINING_AND_DEPLOYMENT.md` (Hướng dẫn huấn luyện, export và triển khai)
  - `backend/tests/test_ocr_model_lifecycle.py` (Kiểm thử phân giải mô hình và Fail-Fast)

- [x] **Task 11.1: OCR Model Registry & Deterministic Resolution**
  - Định nghĩa Pydantic `ModelArtifactManifest` chứa đầy đủ metadata (version, base_model, runtime, metrics, artifact paths).
  - Khởi tạo `OCRModelRegistry` phân giải trọng số theo release version rõ ràng, loại bỏ hoàn toàn việc nạp ngầm từ cache directory.
- [x] **Task 11.2: Fail-Fast Artifact Validation & Zero Silent Fallback**
  - Tự động kiểm tra tính tồn tại và hợp lệ của `inference.onnx` + `inference.yml` trước khi nạp vào Runtime.
  - Ngăn chặn triệt để Silent Fallback: ném lỗi dừng lại ngay lập tức nếu artifact của custom model được cấu hình bị thiếu hoặc hỏng.
- [x] **Task 11.3: Dual Stream Inference Tuning Isolation**
  - Tách biệt rõ ràng tham số nhạy của Stream A (Prescription: det_thresh=0.3) và Stream B (Packaging: det_thresh=0.4, unclip_ratio=1.8).
  - Cung cấp phương thức `get_active_model_info()` phục vụ giám sát và kiểm tra tình trạng mô hình.
- [x] **Task 11.4: Production Training & Deployment Operational Guide**
  - Hoàn thiện tài liệu `docs/OCR_MODEL_TRAINING_AND_DEPLOYMENT.md` với đầy đủ quy trình từ Kaggle Training, ONNX Export đến Benchmark và Rollback.
  - Toàn bộ 183/183 Backend Tests PASS (bao gồm 7 test suites mới cho Model Lifecycle).

---

### 🔹 STAGE 12: CLINICAL DATASET GOVERNANCE & DDI COVERAGE GATE `🟢 Completed`
> **Mục tiêu:** Thiết lập hệ thống quản trị dữ liệu tri thức lâm sàng, kiểm soát độ bao phủ DDI thực tế, bảo vệ các Bất biến An toàn Y tế (INV-12-01..04), chống ngụy tạo bằng chứng và loại bỏ hoàn toàn lỗi logic "Không tìm thấy tương tác = An toàn".

* **File tác động chính:**
  - `backend/app/schemas/ocr_schema.py` (`DrugCoverageStatus`, `DrugCoverageItem`, `DatasetProvenanceInfo`)
  - `backend/app/services/ddinter_service.py` (Coverage universe & dynamic checksum calculation)
  - `backend/app/data/manifest.json` (Active dataset version 2.0 manifest & rollback status)
  - `backend/app/governance/dataset_validator.py` (Integrity, schema & rollback validator)
  - `backend/app/services/evaluation_service.py` (Coverage evaluation & hardened final summary)
  - `backend/tests/test_clinical_governance_coverage.py` (14 new tests for safety invariants & governance)

- [x] **Task 12.1: Clinical Coverage State Machine & Invariants (INV-12-01..04)**
  - Phân loại rõ 5 trạng thái thuốc (`COVERED`, `NOT_COVERED`, `AMBIGUOUS`, `UNRESOLVED`, `SOURCE_UNAVAILABLE`).
  - Xóa bỏ triệt để kết luận ngầm "An toàn" khi dữ liệu thiếu hoặc thuốc chưa được định danh.
- [x] **Task 12.2: Response Schema Extension & Backward Compatibility**
  - Mở rộng `EvaluationResponse` với `coverage_status`, `drug_coverage_details`, `provenance_metadata` sử dụng default factories, bảo toàn 100% History Raw Payload và Frontend Contract.
- [x] **Task 12.3: Dataset Manifest & Integrity Validator**
  - Xây dựng `DatasetValidator` kiểm tra tính toàn vẹn của dataset, tính duy nhất của ID, không trùng cặp đối xứng và không có self-pairs.
  - Khởi tạo `manifest.json` với mã băm SHA256 động, minh bạch trạng thái rollback `rollback_available: false`.
- [x] **Task 12.4: Comprehensive Verification & Zero-Trust Safety Re-Audit**
  - Thực hiện Zero-Trust Red-Team Audit toàn diện: giải quyết dứt điểm 3 rủi ro release-blocking (main.py API wire contract mapping, ddinter_service fail-closed integrity lockdown khi checksum mismatch / empty, và case-insensitive external match gating ADV-O2).
  - Toàn bộ 216/216 Backend Tests PASS (bao gồm 28 test suites cho Stage 12 Governance & Adversarial Re-Audit), 16/16 AI OCR Tests PASS, và Next.js production build PASS 100% (0 errors).

---

## 🚀 GIAI ĐOẠN 13 (STAGE 13): PACKAGING STRENGTH GOVERNANCE & GRACEFUL CLINICAL EVALUATION

> **Mục tiêu cốt lõi:** Giải quyết triệt để vấn đề thực tế khi bao bì/lọ thuốc tại Việt Nam không ghi hàm lượng (mg) ở mặt trước hoặc là thuốc đa thành phần, phi-mg. Xây dựng cơ chế hạ cấp an toàn (Graceful Degradation) cho phép hệ thống vẫn phân tích trơn tru Layer 1–3 (Trùng lặp hoạt chất, Tương tác Thuốc - Thuốc, Chống chỉ định Bệnh nền) mà không bị crash/block khi khuyết hàm lượng, đồng thời cung cấp UX 1-chạm (Variant Pills) và hỗ trợ quét 2 mặt vỏ hộp.

- [x] **Task 13.1: Graceful Degradation in Clinical Evaluation (Backend Layer 4 Safety Gating)**
  - Cho phép `DrugItem.strength` nhận giá trị rỗng/None hoặc `"Không xác định"` mà không gây lỗi validation 422 hay crash logic.
  - Bảo đảm Layer 1 (Trùng lặp), Layer 2 (Thuốc-Thuốc), Layer 3 (Thuốc-Bệnh nền) hoạt động 100% dựa trên hoạt chất gốc đã chuẩn hoá, hoàn toàn độc lập với việc có hay không có `strength`.
  - Layer 4 (Đối chiếu Liều Dùng): Sử dụng chính xác hàm public `check_dosage_appropriateness()` (không có gạch dưới). Khi thiếu thông tin hàm lượng hoặc liều dùng, ghi nhận `DosageCheckResult` với `is_appropriate=None`, đưa khuyến cáo y khoa rõ ràng vào `final_summary` thay vì đưa ra kết luận thiếu căn cứ hoặc crash pipeline.
- [x] **Task 13.2: Drug Catalog Unique-Strength Auto-Default & Variant Catalog Engine**
  - Mở rộng CSDL `vietnam_drugs_db.json` bổ sung trường `common_strengths: list[str]`, `is_unique_strength: bool` và trường bắt buộc `_strength_source: str` trích dẫn Dược thư Quốc gia VN, Cục Quản lý Dược (DAV), hoặc SmPC/HDSD chính hãng. Tuyệt đối KHÔNG tự suy diễn/bịa theo trí nhớ.
  - Cung cấp helper tra cứu danh sách biến thể hàm lượng chuẩn từ CSDL theo tên biệt dược hoặc hoạt chất.
  - Tự động điền hàm lượng mặc định khi thuốc chỉ có 1 quy cách lưu hành duy nhất trên thị trường.
- [x] **Task 13.3: Frontend HITL Quick-Select Variant Pills & Non-Blocking Strength Form**
  - Nâng cấp `DrugVerificationForm`: Khi người dùng nhận diện hoặc gõ tên thuốc có nhiều biến thể trong CSDL, tự động hiển thị hàng nút bấm chọn nhanh (Pills: `[ 500mg ] [ 650mg ] [ Khác ]`) giúp người dùng chọn 1-chạm không cần gõ phím.
  - Cho phép người dùng lưu xác nhận khi bao bì không có hàm lượng mà không bị chặn form (Non-blocking).
  - Cập nhật `InteractionAlertCards`: Chống False Reassurance — trạng thái `isAppropriate === null` (thiếu dữ liệu hàm lượng) hiển thị badge xám/amber trung tính với icon `HelpCircle` hoặc `AlertCircle`, tuyệt đối KHÔNG dùng màu xanh lục `emerald` hay icon tick `CheckCircle2`.
- [x] **Task 13.4: Multi-Shot Packaging Back-Panel Scan (Zero Image Persistence)**
  - Bổ sung tùy chọn trên giao diện quét vỏ hộp (Pipeline 1): *"Chụp thêm mặt sau / bảng thành phần"* khi ảnh mặt trước thiếu thông tin hàm lượng chi tiết.
  - Tuân thủ tuyệt đối nguyên tắc Zero Image Persistence (`ARCHITECTURE.md §7.1`): Cả 2 ảnh (mặt trước + mặt sau) đều xử lý 100% in-memory, tuyệt đối không lưu file xuống đĩa (disk) hay database.
- [x] **Task 13.5: End-to-End Test Suite, Safety Verification & Production Gate**
  - Viết unit tests và integration tests bao phủ 100% các ca: thiếu hàm lượng, thuốc 1 hàm lượng tự động điền, thuốc nhiều hàm lượng chọn pill, đánh giá 4 Layer chạy an toàn không crash khi strength rỗng.
  - Bảo toàn 100% Regression Tests cho Task 5.5 cũ (Metformin + suy thận, Paracetamol quá ngưỡng...).
  - Kiểm tra toàn bộ 223/223 backend tests, 16 AI tests và Next.js production build đạt 100% PASS.

---

## 🎯 DEFINITION OF DONE (TIÊU CHÍ NGHỆM THU CHUNG)
1. **Zero External VLM Dependency:** Không phụ thuộc vào bất kỳ API đọc ảnh thương mại nào (Gemini Vision/GPT-4V) cho cả User Pipeline 1 và Pipeline 2. Hệ thống OCR vận hành 100% On-Premise trên CPU với model tự huấn luyện (baseline ONNX Runtime).
2. **Zero Compile & Test Errors:** Không có lỗi TypeScript (`tsc`), không có lỗi Python Syntax/Linting, 42/42 backend tests hiện có pass, bổ sung test mới cho Task 5.5 và Stage 8.
3. **Schema Adherence:** Mọi API Endpoint trả về đúng cấu trúc JSON quy định (bao gồm Raw OCR, Mapped Drugs, Clinical Assessment, Dosage Check, và Final Summary).
4. **Latency Benchmark SLA:** Phân tích OCR đạt thời gian xử lý trung bình < 15 giây/ảnh trên phần cứng CPU thông thường.
5. **4-Layer Evaluation Completeness:** Mọi lần gọi `/api/v1/evaluate` phải trả về đủ 4 layer (Trùng lặp/Quá liều, Thuốc-Thuốc, Thuốc-Bệnh nền, Đối chiếu Liều Dùng) kèm `final_summary`.
6. **History & Reminder Persistence:** Mọi lần đánh giá thành công phải được lưu vào Lịch sử; Nhắc nhở uống thuốc hoạt động độc lập, không làm chậm luồng đánh giá chính.
7. **Traceability:** Mọi commit/PR đều đánh dấu chính xác mã Task trong file này (Ví dụ: `feat: [Task 2.1] Dual Stream ONNX OCR Engine Implementation`, `feat: [Task 5.5] Dosage Appropriateness Layer`, `feat: [Task 8.1] Medication History Service`).
