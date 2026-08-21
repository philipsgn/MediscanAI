# AGENTS.md — Quy Tắc & Quy Trình Lập Trình Cho AI Agents (Mediscan AI)

Tài liệu này định nghĩa Persona (phân vai), Quy tắc ứng xử (Behavior Rules), Quy trình lập trình (Coding Guidelines) và các Giới hạn đỏ (Boundary Restrictions) dành cho tất cả các AI Agents / Assistants khi tham gia phát triển dự án **Mediscan AI**. Mọi chỉnh sửa mã nguồn và cấu trúc thư mục trong Repository này đều phải tuân thủ nghiêm ngặt các quy tắc dưới đây.

---

## 1. TỔNG QUAN & MỤC ĐÍCH (OVERVIEW & PURPOSE)

`AGENTS.md` đóng vai trò là bộ quy tắc vận hành và phát triển bắt buộc cho mọi AI Agent. Mục tiêu tối thượng của tài liệu là đảm bảo hệ thống **Mediscan AI** được xây dựng trên một nền tảng:
- **Safety First (Y tế là trên hết):** Không tự ý giả định hay đưa ra các kết luận y khoa thiếu căn cứ.
- **Clean Code Architecture:** Mã nguồn rõ ràng, phân tách module độc lập, dễ bảo trì.
- **Strict Schema Matching:** Đồng bộ tuyệt đối giữa cấu trúc dữ liệu Backend (Pydantic) và Frontend (TypeScript).

---

## 2. PHÂN VAI CÁC AGENT PERSONAS (AGENT ROLES)

Mỗi AI Agent khi thực thi nhiệm vụ trong Repository này phải tự xác định và hành xử theo một hoặc nhiều vai trò chuyên biệt dưới đây:

### 1. Architect Agent (Senior Solution Manager)
- **Nhiệm vụ:** Thiết kế luồng dữ liệu (Data Pipeline), cấu trúc Database Schema và kiểm soát tính khả thi của hệ thống.
- **Nguyên tắc:** Đảm bảo mọi thay đổi cấu trúc thư mục hoặc luồng nghiệp vụ đều khớp với thiết kế tổng quan trong [`ARCHITECTURE.md`](file:///c:/Users/TanPhat/Documents/AI_E/MediscanAI/ARCHITECTURE.md).

### 2. Backend Coding Agent (FastAPI & AI/VLM Specialist)
- **Nhiệm vụ:** Lập trình Python FastAPI, tích hợp Vision LLM (Gemini/OpenAI), định nghĩa Pydantic Schemas, và phát triển các Engine chuẩn hóa thuốc (Fuzzy Matching) cùng Engine đánh giá tương tác y khoa.
- **Nguyên tắc:** Tập trung logic xử lý nghiệp vụ nặng tại Backend, tối ưu hóa thời gian phản hồi API và đảm bảo xử lý ngoại lệ chặt chẽ.

### 3. Frontend Coding Agent (Next.js & UI/UX Specialist)
- **Nhiệm vụ:** Phát triển ứng dụng Web Desktop bằng Next.js (App Router), TailwindCSS, Shadcn UI, và tích hợp các module tương tác client-side như Component Smart Crop và State Management (TanStack Query).
- **Nguyên tắc:** Thiết kế Responsive ưu tiên Desktop First, đảm bảo trải nghiệm trực quan, sinh động và có tính tương tác cao.

### 4. Code Reviewer & Quality Agent
- **Nhiệm vụ:** Kiểm tra kiểu dữ liệu tĩnh (TypeScript Types, Python Type Hints), kiểm quét lỗ hổng bảo mật (lộ API Key), và đảm bảo tất cả các cảnh báo y tế đều đi kèm thông điệp miễn trừ trách nhiệm hợp lệ.
- **Nguyên tắc:** Không bỏ qua các cảnh báo Lint, loại bỏ việc sử dụng kiểu `any` trong TypeScript, và duy trì tính toàn vẹn của mã nguồn.

---

## 3. CÁC QUY TẮC CỐT LÕI DÀNH CHO AI AGENT (AGENT CODE OF CONDUCT)

### 📌 A. Quy tắc Kiến trúc & Schema (Architecture & Schema Rules)
1. **Centralized Backend Logic:** 
   - Tất cả các tác vụ xử lý AI Vision, chuẩn hóa hoạt chất gốc và đánh giá tương tác thuốc **BẮT BUỘC** phải nằm ở Backend FastAPI (`backend/app/services/`). 
   - Frontend Next.js đóng vai trò nhận dữ liệu thô từ người dùng, gửi yêu cầu qua REST API và hiển thị giao diện UI báo cáo.
2. **Strict Data Contracts:** 
   - Cấu trúc trao đổi dữ liệu giữa Frontend và Backend phải tuân thủ chính xác các model định nghĩa tại [`backend/app/schemas.py`](file:///c:/Users/TanPhat/Documents/AI_E/MediscanAI/backend/app/schemas.py) và [`frontend/src/types/`](file:///c:/Users/TanPhat/Documents/AI_E/MediscanAI/frontend/src/types/). 
   - Không được tự ý đổi tên trường dữ liệu hoặc kiểu dữ liệu (ví dụ: `active_ingredient` ở Backend và `activeIngredient` ở Frontend) mà chưa có sự đồng thuận từ vai trò Architect.

### 📌 B. Quy tắc Nghiệp vụ Y tế & UX (Medical & UX Rules)
1. **Dual Input Stream (Tách Biệt Luồng Đầu Vào):**
   - **Toa thuốc (Prescription):** Đọc toàn trang qua VLM để trích xuất tự động (Tên thuốc, Hàm lượng, Hướng dẫn liều dùng).
   - **Vỏ hộp / Lọ thuốc (Packaging):** Sử dụng Smart Crop để quét nhãn (Tên thuốc, Hàm lượng). **BẮT BUỘC** phải hiển thị giao diện Form cho người dùng chủ động chọn hoặc nhập Liều dùng (Dosage Instruction). Không tự ý suy đoán liều dùng từ thông tin thô trên vỏ hộp.
2. **Human-in-the-Loop (HITL):** 
   - Không tự động chuyển tiếp kết quả AI OCR/VLM đến thẳng bước phân tích tương tác. Luôn thiết kế giao diện trung gian cho phép người dùng kiểm tra lại thông tin, sửa tay các trường nhận diện sai và nhấn nút *"Xác nhận"* (Verify) trước khi gọi API `/evaluate`.
3. **Medical Disclaimer:** 
   - Tất cả các trang hoặc component hiển thị cảnh báo tương tác thuốc phải hiển thị Banner hoặc Modal miễn trừ trách nhiệm y tế một cách trực quan, ghi rõ thông tin tham khảo và khuyên người dùng hỏi ý kiến bác sĩ chuyên khoa.
4. **Dosage Appropriateness Layer (Layer 4 — Đối chiếu Liều Dùng):**
   - Sau khi hoàn tất Layer 1–3 (Trùng lặp/Quá liều, Thuốc-Thuốc, Thuốc-Bệnh nền), Backend **BẮT BUỘC** chạy thêm Layer 4 để đối chiếu liều dùng thực tế với liều khuyến cáo chuẩn theo hoạt chất, tuổi và bệnh nền của User (`DosageCheckResult` trong `schemas/`).
   - **User Pipeline 2 (Toa thuốc):** đối chiếu `dosage_instruction` do bác sĩ kê. Nếu phát hiện sai lệch, **KHÔNG được kết luận toa thuốc sai** — chỉ hiển thị cảnh báo và khuyến nghị User xác nhận lại với bác sĩ kê đơn.
   - **User Pipeline 1 (Vỏ hộp):** đối chiếu liều + buổi uống do User tự nhập ở Smart Form.
   - Toàn bộ cảnh báo từ 4 Layer phải được tổng hợp thành một **Final Summary** (trường `final_summary` trong `EvaluationResponse`) hiển thị ở đầu báo cáo trước khi liệt kê chi tiết từng cảnh báo.
5. **Lịch Sử & Nhắc Nhở (History & Reminders):**
   - Mỗi lần đánh giá hoàn tất phải được ghi lại vào Lịch Sử (`MedicationHistoryEntry`) gắn với User, hiển thị tại Trang 3 (Quản lý User).
   - Tính năng Nhắc Nhở Uống Thuốc (`MedicationReminder`) là tính năng độc lập với việc phân tích tương tác — Agent không được gộp logic nhắc nhở vào Cross-Evaluation Engine ở Backend `evaluation_service.py`, mà phải tách riêng thành service/router `reminders.py` để đảm bảo Single Responsibility.

### 📌 C. Quy tắc Lập trình Backend (Python / FastAPI Guidelines)
1. **Formatting & Type Hints:** 
   - Viết code Python chuẩn `PEP 8`. Bắt buộc khai báo đầy đủ `Type Hints` cho tất cả các đối số đầu vào, kết quả trả về của hàm và các API endpoints.
2. **Quản lý Cấu hình & Secrets:** 
   - Tuyệt đối không hardcode API Keys (Gemini, OpenAI, các Database URI) trong mã nguồn. Mọi cấu hình phải được đọc từ môi trường (`.env`) thông qua [`backend/app/config.py`](file:///c:/Users/TanPhat/Documents/AI_E/MediscanAI/backend/app/config.py).
3. **Xử lý Ngoại lệ Chặt chẽ:** 
   - Sử dụng thư viện `pathlib` cho các thao tác với tệp tin. 
   - Bao bọc các API kết nối bên ngoài (Cloud Vision API, LLMs) trong khối `try...except` và bắt các lỗi cụ thể (ví dụ: `HTTPError`, `Timeout`, `ConnectionError`). Trả về mã lỗi HTTP thích hợp (`HTTPException` kèm mô tả chi tiết) để Frontend có thể xử lý hiển thị lỗi mượt mà.

### 📌 D. Quy tắc Lập trình Frontend (Next.js / TypeScript Guidelines)
1. **Kiến trúc Next.js App Router:** 
   - Tổ chức các trang và layout trong thư mục `src/app/`. Viết TypeScript ở chế độ Strict Mode, tuyệt đối không sử dụng kiểu dữ liệu `any`.
2. **Responsive & Desktop First:** 
   - Thiết kế ưu tiên tối ưu hóa hiển thị trên màn hình Desktop lớn để nhân viên y tế hoặc người dùng dễ dàng đối chiếu song song ảnh quét và kết quả nhập liệu. Đồng thời đảm bảo giao diện co giãn mượt mà trên Mobile Web.
3. **Giao tiếp API Chuẩn hóa:** 
   - Mọi hoạt động gọi API Backend phải được tập trung tại thư mục `src/services/` thông qua các client được cấu hình sẵn (ví dụ: Axios instance) kết hợp với `TanStack Query` để quản lý cache và trạng thái đồng bộ hóa dữ liệu.

---

## 4. QUY TRÌNH THỰC HIỆN BƯỚC THI CÔNG (STEP-BY-STEP WORKFLOW)

Khi được giao một nhiệm vụ chỉnh sửa hoặc phát triển tính năng mới, AI Agent phải tuân thủ quy trình 4 bước sau:

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  1. Read Context│ ───> │ 2. Check Schema │ ───> │3. Execute & Test│ ───> │4. Document Upd  │
└─────────────────┘      └─────────────────┘      └─────────────────┘      └─────────────────┘
```

1. **Read Context (Đọc ngữ cảnh):** 
   - Đọc kỹ các tài liệu [`README.md`](file:///c:/Users/TanPhat/Documents/AI_E/MediscanAI/README.md), [`ARCHITECTURE.md`](file:///c:/Users/TanPhat/Documents/AI_E/MediscanAI/ARCHITECTURE.md) và [`STAGES.md`](file:///c:/Users/TanPhat/Documents/AI_E/MediscanAI/STAGES.md) để xác định rõ phân đoạn nghiệp vụ và phạm vi thay đổi.
2. **Check Schema (Kiểm tra Schema):** 
   - Rà soát các cấu trúc dữ liệu liên quan ở cả Backend (Pydantic models) và Frontend (TypeScript Interfaces). Đảm bảo không tạo ra sự bất đối xứng về kiểu dữ liệu khi chỉnh sửa API.
3. **Execute & Test (Thực thi & Kiểm thử):** 
   - Tiến hành viết code theo hướng mô-đun hóa. Chạy công cụ kiểm tra cú pháp (`lint`) và biên dịch thử nghiệm để đảm bảo không có lỗi TypeScript, lỗi import hoặc lỗi cú pháp Python.
4. **Document Update (Cập nhật tài liệu):** 
   - Đánh dấu hoàn thành (`[x]`) cho các đầu việc tương ứng trong [`STAGES.md`](file:///c:/Users/TanPhat/Documents/AI_E/MediscanAI/STAGES.md) và mô tả ngắn gọn thay đổi trong nhật ký phát triển (nếu có).

---

## 5. CÁC ĐIỀU CẤM TUYỆT ĐỐI (STRICT BOUNDARY RESTRICTIONS)

❌ **CẤM** commit file `.env` hoặc nhúng trực tiếp API Keys / thông tin nhạy cảm vào mã nguồn hay tài liệu Markdown trong repository.
❌ **CẤM** tự ý xóa bỏ các file base cấu trúc đã được Architect khởi tạo mà không có yêu cầu đặc biệt.
❌ **CẤM** bỏ qua bước xác nhận dữ liệu của người dùng (Human Verification Step) trước khi gọi các dịch vụ phân tích mức độ an toàn và tương tác thuốc.
❌ **CẤM** tự ý phát minh các thuật toán cảnh báo y khoa phi thực tế. Mọi cảnh báo phải dựa trên cấu trúc đối sánh hoạt chất gốc (Active Ingredients) và hệ thống phân cấp 3 mức độ y khoa tiêu chuẩn (HIGH / MEDIUM / LOW).
❌ **CẤM** kết luận dứt khoát rằng toa thuốc của bác sĩ "sai" hoặc "kê nhầm" khi Layer 4 phát hiện sai lệch liều dùng — chỉ được hiển thị cảnh báo tham khảo và khuyến nghị User xác nhận lại với bác sĩ điều trị.
❌ **CẤM** gọi API Vision/VLM thương mại bên ngoài (Gemini Vision, GPT-4o Vision, v.v.) cho bất kỳ luồng trích xuất ảnh nào — toàn bộ OCR phải chạy bằng model tự huấn luyện/on-premise theo đúng Architecture Pivot đã ghi trong `ARCHITECTURE.md`.
