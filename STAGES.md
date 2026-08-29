# 🚀 MEDISCAN AI - DỰ ÁN LỘ TRÌNH PHÁT TRIỂN CHI TIẾT (STAGES & VIBE-CODING ROADMAP)

Tài liệu này là **Single Source of Truth** cho tiến độ phát triển dự án **Mediscan AI**. Cấu trúc mỗi Task được chia nhỏ thành các gói công việc cụ thể (Context, Files, Dependencies, Prompt Mẫu) giúp **AI Coding Agent** và Developer triển khai mã nguồn tức thì (*Vibe-Coding Ready*).
# 🚀 MEDISCAN AI - DỰ ÁN LỘ TRÌNH PHÁT TRIỂN CHI TIẾT (STAGES & VIBE-CODING ROADMAP)

Tài liệu này là **Single Source of Truth** cho tiến độ phát triển dự án **Mediscan AI**. Cấu trúc mỗi Task được chia nhỏ thành các gói công việc cụ thể (Context, Files, Dependencies, Prompt Mẫu) giúp **AI Coding Agent** và Developer triển khai mã nguồn tức thì (*Vibe-Coding Ready*).

---

## 📌 TỔNG QUAN HỆ THỐNG GIAI ĐOẠN (STAGES OVERVIEW)
[Stage 1: Base & Setup] ➔ [Stage 2: Pure Dual OCR Engine] ➔ [Stage 3: Local LLM Clinical & API] ➔ [Stage 4: Web UI & Smart Crop]
│
[Stage 7: Production]  ➔ [Stage 8: Auth System] ➔ [Stage 9: Personalized Onboarding] ➔ [Stage 10: History & Reminders]

### 🟡 STAGE 8, 9, 10 MỚI BỔ SUNG — CÁC STAGE 1-7 ĐÃ HOÀN THÀNH

| Stage | Tên Giai Đoạn | Trọng Tâm Kiến Trúc | Trạng Thái |
| :--- | :--- | :--- | :--- |
| **Stage 1** | **Base Environment & Data Schemas** | Khởi tạo Monorepo, Setup FastAPI + Next.js, Type Definitions | 🟢 Completed |
| **Stage 2** | **Multi-Format Pure OCR Engine (ONNX)** | Dual-Stream PP-OCRv6 ONNX (Prescription/Receipt & Packaging Stream) — User Pipeline 1 & 2 | 🟢 Completed |
| **Stage 3** | **Drug API, Normalization & LLM Assessment** | OpenFDA/Local Drug DB + RapidFuzz Mapping + Ollama Clinical Reasoning Engine | 🟢 Completed |
| **Stage 4** | **Interactive Web UI & Smart Crop** | Canvas Crop Box, Dynamic Forms, Dashboard & Active Cabinet | 🟢 Completed |
| **Stage 5** | **Centralized Cross-Evaluation Engine** | Multi-Layer Analysis Engine (Drug-Drug, Overdose, Condition) + Layer 4 Dosage Check (Task 5.5) | 🟢 Completed |
| **Stage 6** | **Polish, Medical Safety & Testing** | Medical Disclaimer Interceptor, E2E Flow Testing, UX Polish | 🟢 Completed |
| **Stage 7** | **Production & Docker Deployment** | Docker Compose, Backend Optimization, Web Desktop Launch | 🟢 Completed |
| **Stage 8** | **Authentication System** | Đăng ký/Đăng nhập username+password, JWT session, bảo vệ route | 🔴 Not Started |
| **Stage 9** | **Personalized Health Onboarding** | Wizard khai hồ sơ y tế (ngày sinh/bệnh nền/dị ứng) gắn với tài khoản thật | 🔴 Not Started |
| **Stage 10** | **Medication History & Reminders** | Giữ nguyên nội dung cũ, chuyển từ "ẩn danh" sang "gắn với user_id thật" | 🔴 Not Started |

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

### 🔹 STAGE 8: AUTHENTICATION SYSTEM
> **Mục tiêu:** Xây dựng hệ thống Đăng ký/Đăng nhập bằng tài khoản thật (Username + Password). Sử dụng JWT session, mã hóa mật khẩu, và bảo vệ các route người dùng (như Hồ sơ, Lịch sử, Nhắc nhở).

* **File tác động chính:**
  - Backend: `auth_service.py`, `user_schema.py`, `auth_router.py`
  - Frontend: `authStore.ts`, `LoginPage.tsx`, `RegisterPage.tsx`, Middleware bảo vệ route

- [ ] **Task 8.1: Backend — JWT Authentication & User Model**
- [ ] **Task 8.2: Frontend — Auth Pages & Zustand Store**

---

### 🔹 STAGE 9: PERSONALIZED HEALTH ONBOARDING
> **Mục tiêu:** Di chuyển và cá nhân hóa Wizard khai báo hồ sơ y tế (Ngày sinh, Cân nặng, Bệnh nền, Dị ứng) để nó gắn liền với tài khoản thật vừa đăng ký.

* **File tác động chính:**
  - Backend: Liên kết UserProfile với tài khoản người dùng (`user_id`).
  - Frontend: Chỉnh sửa lại `userProfileStore.ts` để đọc/ghi từ Backend API thay vì chỉ lưu `localStorage`. Cập nhật `OnboardingWizard`.

- [ ] **Task 9.1: Backend — UserProfile CRUD APIs**
- [ ] **Task 9.2: Frontend — Sync Onboarding Flow with Auth**

---

### 🔹 STAGE 10: MEDICATION HISTORY & REMINDERS (TRANG 3 — QUẢN LÝ USER)
> **Mục tiêu:** Bổ sung Trang 3 hoàn chỉnh cho việc quản lý User: Lịch sử các lần quét/đánh giá và Nhắc nhở uống thuốc. Thay vì lưu trữ cho "User ẩn danh", mọi dữ liệu nay phải gắn với `user_id` thật từ JWT session.

* **File tác động chính:**
  - `backend/app/schemas/history_schema.py`, `backend/app/schemas/reminder_schema.py`
  - `backend/app/api/v1/endpoints/history.py`, `backend/app/api/v1/endpoints/reminders.py`
  - `backend/app/services/history_service.py`, `backend/app/services/reminder_service.py`
  - `frontend/src/app/account/history/page.tsx`, `frontend/src/app/account/reminders/page.tsx`
  - `frontend/src/components/history/HistoryTimeline.tsx`, `frontend/src/components/reminders/ReminderScheduler.tsx`

- [ ] **Task 10.1: Backend — Lưu & Truy Vấn Lịch Sử Quét Thuốc Gắn Với User ID**
  - **Mô tả:** Mỗi lần gọi thành công `POST /api/v1/evaluate` phải ghi lại một `MedicationHistoryEntry` gắn với `user_id` hiện tại.
  - **Agent Action:** Viết `history_service.py` với endpoint GET hỗ trợ phân trang.

- [ ] **Task 10.2: Backend — Quản Lý Nhắc Nhở Uống Thuốc Cho Tài Khoản**
  - **Mô tả:** CRUD cho `MedicationReminder`, gắn với thuốc đang có trong Tủ thuốc và `user_id`.
  - **Agent Action:** Viết `reminder_service.py` + endpoint `POST/GET/PATCH/DELETE /api/v1/reminders`.

- [ ] **Task 10.3: Frontend — Trang 3 Quản Lý User Hoàn Chỉnh**
  - **Mô tả:** Dựng `frontend/src/app/account/` gồm 3 tab: Tủ thuốc (đã có ở Stage 4), Lịch sử, Nhắc nhở (nay yêu cầu đăng nhập).
  - **Agent Action:**
    - `HistoryTimeline.tsx`: hiển thị timeline các lần quét, click vào để xem lại báo cáo chi tiết đã lưu.
    - `ReminderScheduler.tsx`: UI chọn buổi uống (Sáng/Trưa/Chiều/Tối) theo từng thuốc, toggle bật/tắt.
    - Tích hợp TanStack Query cho cả 2 màn hình, đồng bộ với Axios client tại `src/services/`.

- [ ] **Task 10.4: Thông Báo Nhắc Nhở (Notification Delivery)**
  - **Mô tả:** Quyết định cơ chế nhắc nhở khả thi cho Web Desktop (Browser Notification API / in-app toast).
  - **Agent Action:** Ghi rõ giới hạn kỹ thuật trong tài liệu, đề xuất giải pháp nâng cấp khi có Mobile App (Flutter/React Native) ở giai đoạn mở rộng.

---

## 🎯 DEFINITION OF DONE (TIÊU CHÍ NGHỆM THU CHUNG)
1. **Zero External VLM Dependency:** Không phụ thuộc vào bất kỳ API đọc ảnh thương mại nào (Gemini Vision/GPT-4V) cho cả User Pipeline 1 và Pipeline 2. Hệ thống OCR vận hành 100% On-Premise trên CPU với model tự huấn luyện (baseline ONNX Runtime).
2. **Zero Compile & Test Errors:** Không có lỗi TypeScript (`tsc`), không có lỗi Python Syntax/Linting, 42/42 backend tests hiện có pass, bổ sung test mới cho Task 5.5 và Stage 8.
3. **Schema Adherence:** Mọi API Endpoint trả về đúng cấu trúc JSON quy định (bao gồm Raw OCR, Mapped Drugs, Clinical Assessment, Dosage Check, và Final Summary).
4. **Latency Benchmark SLA:** Phân tích OCR đạt thời gian xử lý trung bình < 15 giây/ảnh trên phần cứng CPU thông thường.
5. **4-Layer Evaluation Completeness:** Mọi lần gọi `/api/v1/evaluate` phải trả về đủ 4 layer (Trùng lặp/Quá liều, Thuốc-Thuốc, Thuốc-Bệnh nền, Đối chiếu Liều Dùng) kèm `final_summary`.
6. **History & Reminder Persistence:** Mọi lần đánh giá thành công phải được lưu vào Lịch sử; Nhắc nhở uống thuốc hoạt động độc lập, không làm chậm luồng đánh giá chính.
7. **Traceability:** Mọi commit/PR đều đánh dấu chính xác mã Task trong file này (Ví dụ: `feat: [Task 2.1] Dual Stream ONNX OCR Engine Implementation`, `feat: [Task 5.5] Dosage Appropriateness Layer`, `feat: [Task 8.1] Medication History Service`).
