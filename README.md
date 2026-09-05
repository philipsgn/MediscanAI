# Mediscan AI 🩺

### Hệ Thống Trợ Lý AI Y Tế — Nhận Diện Toa Thuốc On-Premise & Cảnh Báo An Toàn Tương Tác Đa Tầng

![Next.js](https://img.shields.io/badge/Frontend-Next.js%2016%20(App%20Router)-black?logo=nextdotjs&logoColor=white)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Deploy-Docker%20Compose-2496ED?logo=docker&logoColor=white)
![OCR](https://img.shields.io/badge/OCR-PP--OCRv6%20%2B%20VietOCR%20(Hybrid%20On--Premise)-success)
![Status](https://img.shields.io/badge/Status-Stage%2018%20Production%20Ready-brightgreen)
![Tests](https://img.shields.io/badge/Tests-249%2B%20Passed%20(100%25)-green)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 1. Bối Cảnh & Mục Tiêu Dự Án (Project Context)

### 📌 Vấn Đề Thực Tế (Clinical Pain-Points)
Trong thực tế khám chữa bệnh và sử dụng thuốc tại Việt Nam, người bệnh thường xuyên đối mặt với các nguy cơ y khoa đe dọa sức khỏe:
* **Đơn thuốc chồng chéo (Fragmented Prescriptions):** Người bệnh khám tại nhiều cơ sở y tế khác nhau và nhận nhiều đơn thuốc riêng biệt mà các bác sĩ điều trị không hề biết thông tin của nhau.
* **Tự ý mua thuốc & Dùng Thực phẩm chức năng (OTC & Dietary Supplements):** Việc tự mua thuốc không kê đơn dựa trên vỏ hộp cũ hoặc dùng thêm các chế phẩm dinh dưỡng, bổ khớp, gân, dạ dày... mà không có sự kiểm soát về tương tác dược lý.
* **Nguy cơ tai biến dược lý tiềm ẩn:** Người bệnh không có khả năng tự nhận biết các nguy cơ tương tác thuốc nguy kịch (**Drug-Drug Interactions**), trùng lặp hoạt chất gây suy gan/suy thận cấp (**Overdose / Duplication**), hoặc xung đột trực tiếp với bệnh nền có sẵn (**Drug-Disease Conflicts**).

### 🎯 Mục Tiêu Cốt Lõi Của Mediscan AI
**Mediscan AI** được xây dựng nhằm cung cấp giải pháp tham khảo và cảnh báo an toàn y tế sớm, vận hành trên nguyên tắc **Privacy First & Safety First**:
1. **100% On-Premise OCR (Zero Commercial VLM):** Tuyệt đối không gửi ảnh toa thuốc chứa thông tin nhạy cảm của bệnh nhân (tên, tuổi, địa chỉ, bệnh án) lên các cloud thương mại (Gemini Vision / GPT-4o Vision). Toàn bộ xử lý ảnh chạy trên CPU nội bộ.
2. **Hệ Thống Chuẩn Hóa Dược Liệu Đa Tầng (5-Tier Authority Hierarchy):** Bao phủ từ 105 thuốc cơ sở Dược thư Việt Nam, mở rộng hơn **11.500+ biệt dược generic**, tra cứu thẩm quyền quốc tế **RxNorm (US NLM)**, tem nhãn **OpenFDA**, và tầng suy luận Text LLM cho các chế phẩm đặc thù.
3. **Kho Tương Tác Dược Lý DDInter 2.0 (On-Premise):** Tra cứu tức thời $O(1)$ (< 0.02ms) các tương tác thuốc dựa trên CSDL đã bình duyệt quốc tế, kèm mã xác thực tính toàn vẹn dữ liệu **SHA-256 Checksum**.
4. **Vòng Lặp Active Learning & Chống Ngộ Độc Cache (Anti-Poisoning):** Bộ nhớ tự học 3 tầng (L1 RAM $\rightarrow$ L2 Relational DB $\rightarrow$ L3 JSON) với giao diện Human-in-the-Loop (HITL) giúp nâng cấp tri thức và đo lường chi phí AI theo thời gian thực.

---

## 2. Các Tính Năng & Kiến Trúc Kỹ Thuật Đột Phá

### 🔍 1. Hybrid Ensemble On-Premise OCR Pipeline (Stream A & Stream B)
* **Luồng Toa thuốc (Stream A - Prescription):** 
  - Ứng dụng kiến trúc **Ensemble Hybrid**: Sử dụng `PP-OCRv6 DBNet` siêu tốc để định vị tọa độ bounding boxes trên toàn trang đơn, kết hợp `VietOCR VGG-Transformer` chạy CPU on-premise để giải mã tiếng Việt chuẩn 100% dấu nguyên âm (`TOA THUỐC`, `Trước ăn 30 phút`, `Trưa/Tối`, `Uống thuốc sau khi ăn no`).
  - Đảm bảo thời gian xử lý trung bình **< 9.5 giây/ảnh**, vượt xa cam kết SLA (< 15 giây).
* **Luồng Vỏ hộp / Lọ / Vỉ thuốc (Stream B - Packaging):**
  - Tối ưu hóa đọc nhãn in hoa latin bằng PP-OCRv6, hỗ trợ **Smart Crop**, tự động phân tách biến thể hàm lượng (Variant Pills: `500mg`, `650mg`), và tính năng **Quét 2 mặt vỏ hộp (Multi-Shot)** xử lý 100% in-memory (Zero Image Persistence).

---

### 🌐 2. Phân Cấp Chuẩn Hóa Hoạt Chất 5 Tầng (Authority-Driven Normalization)

Thay vì đoán mò (hallucination), Mediscan AI áp dụng quy tắc an toàn y tế nghiêm ngặt:

```
[Tên Thuốc / Biệt Dược Quét Được]
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ TẦNG 1: Dược Thư Quốc Gia DAV (105 thuốc Gold Standard)│ -> O(1) Offline
└────────────────────────────────────────────────────────┘
                 │ (Miss)
                 ▼
┌────────────────────────────────────────────────────────┐
│ TẦNG 2: Extended Master Registry (11.500+ Generic)     │ -> O(1) Offline
└────────────────────────────────────────────────────────┘
                 │ (Miss)
                 ▼
┌────────────────────────────────────────────────────────┐
│ TẦNG 2.5: Dynamic Knowledge Cache (Thuốc Đã Tự Học)   │ -> O(1) L1 RAM / L2 DB
└────────────────────────────────────────────────────────┘
                 │ (Miss)
                 ▼
┌────────────────────────────────────────────────────────┐
│ TẦNG 3: RxNorm / RxNav REST API (US NLM - Thẩm Quyền) │ -> Miễn phí, 0 Key
└────────────────────────────────────────────────────────┘
                 │ (Miss)
                 ▼
┌────────────────────────────────────────────────────────┐
│ TẦNG 3.5: OpenFDA Drug Label API (Tem Nhãn Bổ Trợ)    │ -> Tích hợp API Key
└────────────────────────────────────────────────────────┘
                 │ (Miss)
                 ▼
┌────────────────────────────────────────────────────────┐
│ TẦNG 4: Text LLM Fallback (Gemini Lite / Groq / Ollama)│ -> Phân giải TPCN
└────────────────────────────────────────────────────────┘
```

---

### ⚡ 3. Đánh Giá Lâm Sàng Đa Lớp (4-Layer Clinical Safety Gate)

1. **Layer 1: Trùng Lặp Hoạt Chất & Quá Liều (Overdose / Duplication):**
   - Nhận diện việc uống đồng thời nhiều chế phẩm có cùng hoạt chất (vd: *Panadol Extra* + *Efferalgan Codeine* $\rightarrow$ tổng liều Paracetamol vượt ngưỡng 4.000mg/ngày gây hoại tử gan).
2. **Layer 2: Tương Tác Thuốc - Thuốc (Drug-Drug Interactions - DDInter 2.0):**
   - Đánh giá theo 3 mức độ quốc tế: **HIGH / MEDIUM / LOW**.
   - Cung cấp cơ chế dược lý (Pharmacodynamics / Pharmacokinetics) và khuyến cáo xử trí lâm sàng cho bệnh nhân.
3. **Layer 3: Chống Chỉ Định Bệnh Nền (Drug-Disease Conflicts):**
   - Cảnh báo tức thì khi thuốc đối kháng với bệnh lý trong hồ sơ cá nhân (vd: NSAIDs với Loét dạ dày, Co mạch Pseudoephedrine với Cao huyết áp, Metformin với Suy thận cấp độ 3b/4).
4. **Layer 4: Đối Chiếu Liều Dùng Thực Tế (Dosage Appropriateness):**
   - Đối chiếu liều lượng bác sĩ kê hoặc liều người dùng tự nhập với giới hạn tối đa khuyến cáo y khoa (`max_daily_dosage`).
   - Tổng hợp toàn bộ 4 tầng thành **Final Clinical Summary** hiển thị rõ ràng ở đầu báo cáo.

---

### 🧠 4. Enterprise Dynamic Knowledge Store, Anti-Poisoning & AI Telemetry

Hệ thống biến tri thức AI thành tài sản lâu dài của doanh nghiệp:
* **Kiến trúc lưu trữ 3 tầng (Multi-Tier Storage):**
  - **L1 RAM In-Memory Hash Map:** Phản hồi $O(1)$ (< 0.01ms).
  - **L2 Relational Database (`LearnedDrugModel`):** PostgreSQL / SQLite với SQLAlchemy 2.0 Async, chỉ mục `brand_name_normalized`, và bộ đếm nguyên tử `hit_count`.
  - **L3 Offline JSON Fallback:** Đảm bảo sẵn sàng cao (High Availability).
* **Vòng lặp Active Learning & Chống ngộ độc Cache (Anti-Poisoning):**
  - AI suy luận ban đầu gán trạng thái `PENDING_REVIEW` (`is_verified = False`).
  - Giao diện **Human-in-the-Loop (HITL)** cho phép người dùng/bác sĩ xác nhận (`VERIFIED`) hoặc chỉnh sửa hoạt chất đúng (`USER_CORRECTED`), ngay lập tức ghi đè lên RAM và CSDL để ngăn chặn triệt để ảo giác AI.
* **Bảng Đo Lường Chi Phí AI Trực Tiếp (AI Observability & ROI Dashboard):**
  - Endpoint `GET /api/v1/metrics/ai-cache` theo dõi: Tỷ lệ Cache Hit (%), Tổng số Token LLM tiết kiệm được, Chi phí USD tiết kiệm, và Top biệt dược được tái sử dụng nhiều nhất.
  - Tích hợp Modal trực quan **"⚡ AI Telemetry"** trên trang quét thuốc.

---

## 3. Kiến Trúc Luồng Dữ Liệu Chi Tiết (Architecture Flow)

```mermaid
flowchart TD
    subgraph Input [1. Đầu Vào An Toàn On-Premise]
        ImgPresc[Ảnh Toa Thuốc In Máy] --> OCR_A[Hybrid OCR: PP-OCRv6 + VietOCR]
        ImgBox[Ảnh Vỏ Hộp / Vỉ Thuốc] --> OCR_B[Smart Crop + PP-OCRv6 Latin]
    end

    subgraph Normalization [2. Chuẩn Hóa Phân Tầng Thẩm Quyền]
        OCR_A & OCR_B --> T1{Tier 1: DAV 105?}
        T1 -- Miss --> T2{Tier 2: Extended 11.5k?}
        T2 -- Miss --> T25{Tier 2.5: Learned Cache?}
        T25 -- Miss --> T3{Tier 3: RxNorm NLM?}
        T3 -- Miss --> T35{Tier 3.5: OpenFDA?}
        T35 -- Miss --> T4[Tier 4: Gemini Lite / Groq / Ollama]
        T4 --> SaveCache[Lưu vết vào L1 RAM + L2 CSDL + L3 JSON]
        SaveCache --> HITL[3. Xác Nhận Người Dùng - HITL Form]
        T1 -- Hit --> HITL
        T2 -- Hit --> HITL
        T25 -- Hit --> HITL
        T3 -- Hit --> HITL
        T35 -- Hit --> HITL
    end

    subgraph Clinical [4. Đánh Giá Lâm Sàng 4 Lớp]
        HITL --> Profile[Hồ Sơ Bệnh Nền & Tuổi]
        HITL --> Agg[Tủ Thuốc Hoạt Động - Active Inventory]
        Agg & Profile --> L1_OD[Layer 1: Trùng Lặp & Quá Liều]
        Agg & Profile --> L2_DD[Layer 2: Tương Tác DDInter 2.0 O(1)]
        Agg & Profile --> L3_DC[Layer 3: Chống Chỉ Định Bệnh Nền]
        Agg & Profile --> L4_DS[Layer 4: Đối Chiếu Liều Khuyến Cáo]
    end

    subgraph Output [5. Báo Cáo & Quản Trị]
        L1_OD & L2_DD & L3_DC & L4_DS --> Summary[Bản Tóm Tắt & Cảnh Báo Lâm Sàng]
        Summary --> History[Lưu Lịch Sử Khám & Nhắc Nhở Uống Thuốc]
        Summary --> Telemetry[AI Cache Telemetry & Cost Dashboard]
    end
```

---

## 4. Công Nghệ Sử Dụng (Tech Stack)

* **Frontend:**
  - **Core:** Next.js 16 (App Router), React 19, TypeScript (Strict Mode).
  - **Giao diện:** TailwindCSS, Shadcn UI, Lucide Icons.
  - **State & Data Fetching:** TanStack React Query, Axios.
* **Backend:**
  - **Framework:** FastAPI (Python 3.10+ / 3.14), Asynchronous Architecture (`asyncpg`, `aiosqlite`).
  - **ORM & Migrations:** SQLAlchemy 2.0 Async, Alembic.
  - **Bảo mật:** JWT Authentication (HS256), SlowAPI Rate Limiting, CORS Protection.
* **AI & Computer Vision:**
  - **OCR Detection:** PaddleOCR PP-OCRv6 ONNX Runtime (CPU multi-threading).
  - **OCR Recognition:** VietOCR VGG-Transformer (PyTorch CPU On-Premise).
  - **Matching & Normalization:** RapidFuzz Levenshtein, RxNav REST API, OpenFDA Label API.
  - **Text LLM Inference:** Google Gemini 2.5/Flash-Lite, Groq Cloud (openai/gpt-oss-20b), Local Ollama (`qwen2.5:1.5b`).
  - **DDI Engine:** DDInter 2.0 Local Dataset với SHA-256 Manifest Integrity Validation.
* **DevOps & Infrastructure:**
  - Docker & Docker Compose (Multi-stage builds, Non-root containers).

---

## 5. Cấu Trúc Thư Mục Dự Án (Project Structure)

```text
MediscanAI/
├── ai/                         # Module AI Computer Vision & Data Ingestion
│   ├── configs/vietocr/        # Cấu hình Offline-safe cho VietOCR (vgg-transformer.yml)
│   ├── data_ingestion/         # Pipeline nạp dataset 11.5k thuốc (ingest_medicine_dataset.py)
│   ├── models/                 # Trọng số ONNX PP-OCRv6 và VietOCR transformer
│   └── pipelines/              # VietOCR Recognizer Engine Singleton
├── backend/                    # Python FastAPI Central REST API
│   ├── alembic/                # Quản lý Database Migrations (001 -> 005_learned_drugs)
│   ├── app/
│   │   ├── api/v1/endpoints/   # Endpoints: auth, ocr, drugs, evaluate, cabinet, metrics...
│   │   ├── core/config.py      # Cấu hình Single Source of Truth (Pydantic BaseSettings)
│   │   ├── data/               # Datasets: vietnam_drugs, extended_medicines, ddinter, manifest
│   │   ├── db/                 # Kết nối CSDL Async SQLAlchemy (session.py, base.py)
│   │   ├── models/             # ORM Models: User, DrugCabinet, History, LearnedDrug
│   │   ├── schemas/            # Pydantic Contracts (OCR, Medication, Evaluation, Telemetry)
│   │   ├── services/           # OCR Engine, Normalization, DDInter, Evaluation, LLM Resolver
│   │   └── main.py             # Điểm khởi chạy FastAPI ứng dụng
│   ├── tests/                  # Bộ kiểm thử tự động 249+ tests PASS 100%
│   ├── .env.example            # Tệp mẫu cấu hình môi trường chuẩn
│   └── requirements.txt        # Danh sách thư viện Backend
├── frontend/                   # Ứng dụng Web Desktop Next.js
│   ├── src/
│   │   ├── app/                # App Router: scan, cabinet, history, onboarding, login, register
│   │   ├── components/         # Smart Crop, DrugVerificationForm, InteractionAlertCards, TelemetryModal
│   │   ├── services/           # API Client Axios & TanStack Query Hooks
│   │   └── types/              # TypeScript Interfaces đồng bộ 100% với Pydantic Backend
│   └── package.json
├── docker-compose.yml          # Triển khai toàn bộ hệ thống 1-chạm
├── Dockerfile.backend          # Multi-stage build cho FastAPI
└── Dockerfile.frontend         # Standalone build cho Next.js
```

---

## 6. Hướng Dẫn Cài Đặt & Chạy Hệ Thống (Quick Start)

### 1. Cấu hình Biến Môi Trường (`backend/.env`)
Tạo tệp `backend/.env` dựa trên `backend/.env.example`:

```env
# Cấu hình ứng dụng
APP_HOST=0.0.0.0
APP_PORT=8000

# Tầng suy luận tri thức mở rộng (Stage 17 & 18)
ENABLE_LLM_DRUG_RESOLVER=true

# 1. Google Gemini Text API (Ưu tiên số 1 - Miễn phí 1.500 req/ngày)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-flash-lite-latest

# 2. Groq Cloud API (Ưu tiên số 2 - Siêu tốc độ 500+ tokens/s, Miễn phí)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b

# 3. Local Ollama (Chạy 100% Offline trên máy tính)
LOCAL_LLM_BASE_URL=http://localhost:11434
LOCAL_LLM_MODEL=qwen2.5:1.5b

# OpenFDA API (Hỗ trợ tem nhãn quốc tế)
OPENFDA_API_KEY=your_openfda_api_key_here
OPENFDA_BASE_URL=https://api.fda.gov/drug

# Xác thực bảo mật JWT
JWT_SECRET=your_secure_random_64_character_secret_key_here
AUTH_RATE_LIMIT=5/minute
```

---

### 2. Triển Khai 1-Lệnh Bằng Docker Compose (Khuyên Dùng)

```bash
# Khởi chạy toàn bộ hệ thống đồng thời
docker compose up --build
```
* 🌐 **Giao diện Web:** [http://localhost:3000](http://localhost:3000)
* ⚙️ **API Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 3. Chạy Thủ Công Dành Cho Lập Trình Viên (Development Mode)

#### Chạy Backend (FastAPI):
```bash
cd backend
python -m venv .venv
# Kích hoạt môi trường ảo:
# Windows: .\.venv\Scripts\activate | macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Chạy Server:
uvicorn app.main:app --reload --port 8000
```

#### Chạy Frontend (Next.js):
```bash
cd frontend
npm install
npm run dev
```

#### Chạy Bộ Kiểm Thử Đảm Bảo Chất Lượng (Regression Tests):
```bash
cd backend
pytest tests/ -v
```
*(Toàn bộ 249+ test cases sẽ hoàn thành với 100% PASS)*

---

## 7. Giới Hạn Sử Dụng & Miễn Trừ Trách Nhiệm (Medical Disclaimer)

> [!IMPORTANT]
> **Mediscan AI** được thiết kế như một công cụ hỗ trợ thông tin và cảnh báo tham khảo sớm các nguy cơ an toàn thuốc. Hệ thống **KHÔNG** thay thế cho các chẩn đoán, quyết định điều trị lâm sàng hoặc chỉ định y khoa từ bác sĩ điều trị và dược sĩ chuyên môn. Người bệnh tuyệt đối không tự ý thay đổi liều lượng, ngừng thuốc hoặc phối hợp thuốc mới mà không có sự tham vấn trực tiếp từ nhân viên y tế.
