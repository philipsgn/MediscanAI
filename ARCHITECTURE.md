# Mediscan AI — Tài Liệu Kiến Trúc Hệ Thống (System Architecture)

Tài liệu này mô tả chi tiết kiến trúc hệ thống, luồng xử lý dữ liệu, thiết kế schemas và các nguyên tắc lập trình của dự án **Mediscan AI - Trợ Lý Cảnh Báo Tương Tác & An Toàn Thuốc**.

---

## 1. Tổng Quan Hệ Thống & Nguyên Tắc Thiết Kế (System Overview & Design Principles)

### 📌 Định Hướng Sản Phẩm
**Mediscan AI** cung cấp giải pháp tham khảo và cảnh báo sớm nguy cơ tương tác thuốc kỵ nhau, trùng lặp hoạt chất gây quá liều, hoặc xung đột giữa đơn thuốc với tiền sử bệnh lý của người dùng. Hệ thống được thiết kế theo mô hình **Centralized API-Driven Architecture** nhằm tối ưu hóa khả năng tái sử dụng logic phân tích trên nhiều nền tảng:
1. **Web Desktop Application (Next.js 14+):** Nền tảng cốt lõi giai đoạn đầu phục vụ upload đơn thuốc, quản lý tủ thuốc cá nhân và hiển thị báo cáo chi tiết.
2. **Mobile Application (Flutter / React Native):** Định hướng mở rộng ở giai đoạn tiếp theo để quét nhanh vỏ hộp thuốc tại hiệu thuốc.

> ⚠️ **Cập nhật kiến trúc (Architecture Pivot):** Kể từ Stage 2, hệ thống đã **loại bỏ hoàn toàn phụ thuộc vào VLM thương mại bên thứ ba** (Gemini Vision / GPT-4o Vision). Toàn bộ pipeline trích xuất (Pipeline 1 – Vỏ/lọ/hộp thuốc, Pipeline 2 – Toa thuốc in nhiệt) chạy bằng **model OCR tự huấn luyện/tự host on-premise** (nền tảng ban đầu: PP-OCRv6 ONNX Runtime, sẽ được huấn luyện lại chuyên biệt cho từng luồng sau khi hoàn thiện toàn bộ hệ thống). Mọi mô tả "VLM Full-page Parser" hoặc "VLM Focus API" trong các mục bên dưới cần được hiểu là **Local Trained OCR Model**, không gọi API ảnh ra bên ngoài.

### 📐 Nguyên Tắc Thiết Kế Cốt Lõi

```
┌──────────────────────────────────────────────────────────────────┐
│                    Human-in-the-Loop (HITL)                      │
│   AI trích xuất dữ liệu ──► Xác nhận & sửa đổi từ chuyên gia/user │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Graceful Degradation Fallback                  │
│   Trích xuất VLM thất bại ──► Chuyển sang Smart Form tự động     │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Privacy & Safety First                      │
│   Ảnh xử lý trong RAM ──► Phân cấp cảnh báo đỏ/vàng/xanh ──► Disclaimer│
└──────────────────────────────────────────────────────────────────┘
```

### 🖥️ Cấu Trúc 3 Trang UI/UX Chính

| Trang | Tên | Nội dung |
| :--- | :--- | :--- |
| **Trang 1** | Onboarding | Yêu cầu User cung cấp thông tin chi tiết: tuổi, bệnh nền, dị ứng (đầu vào cho `UserProfile`). |
| **Trang 2** | MediScan AI (Core) | Nơi thực hiện **User Pipeline 1** (upload vỏ/lọ/hộp thuốc) và **User Pipeline 2** (upload toa thuốc in nhiệt): Trích xuất → Tổng hợp → Đánh giá (4 Layer) → hiển thị báo cáo + Summary/lời khuyên cuối cùng. |
| **Trang 3** | Quản lý User | Quản lý Tủ thuốc (Active Cabinet), **Lịch sử** các lần quét (Medication History), và **Nhắc nhở uống thuốc** (Medication Reminders). |

1. **Human-in-the-Loop (HITL - Đặt con người làm trọng tâm):**
   * Do đặc thù y tế yêu cầu độ chính xác tuyệt đối, mọi kết quả trích xuất tự động từ AI (OCR/VLM) đều phải qua bước kiểm tra, xác nhận và cho phép chỉnh sửa bởi người dùng trước khi đưa vào phân tích y khoa.
2. **Graceful Degradation / Hybrid Fallback (Suy thoái có kiểm soát):**
   * Nếu chất lượng hình ảnh đơn thuốc/vỏ hộp kém dẫn đến độ tin cậy trích xuất (Confidence Score) thấp hoặc mô hình VLM gặp lỗi kết nối, hệ thống sẽ tự động chuyển sang chế độ **Smart Form** (Form nhập liệu thông minh tích hợp tìm kiếm gợi ý từ điển) để người dùng tự chọn nhanh biệt dược/hoạt chất.
3. **Privacy & Safety First (Bảo mật & An toàn thông tin):**
   * **Bảo mật:** Dữ liệu hình ảnh y tế nhạy cảm chỉ được xử lý tạm thời trên bộ nhớ đệm (In-memory buffer) của Server, không lưu trữ vĩnh viễn trừ khi có sự đồng ý tường minh (Consent) của người dùng.
   * **An toàn:** Báo cáo tương tác thuốc được phân cấp rõ ràng theo các mức độ nghiêm trọng và luôn đi kèm điều khoản miễn trừ trách nhiệm y tế (Disclaimer).

---

## 2. Kiến Trúc Luồng Dữ Liệu Cốt Lõi (Core Data Pipeline)

Luồng dữ liệu của hệ thống trải qua 5 giai đoạn xử lý từ đầu vào thô cho tới báo cáo tương tác hoàn chỉnh:

```mermaid
flowchart TD
    subgraph G1 [Giai đoạn 1: Onboarding Profile]
        UP[Hồ Sơ Người Dùng<br/>Tuổi, Bệnh nền, Dị ứng]
    end

    subgraph G2 [Giai đoạn 2: Dual Input Stream / User Pipeline 1 & 2]
        direction TB
        subgraph BranchA [User Pipeline 2: Toa Thuốc In Nhiệt]
            Presc[Toa Thuốc In Máy / In Nhiệt] --> OCR_P[Local Trained OCR Model<br/>chuyên biệt Toa/Hóa đơn] --> LookupA[Truy vấn API Thuốc<br/>OpenSource Trong/Ngoài nước]
        end
        subgraph BranchB [User Pipeline 1: Vỏ Hộp / Lọ Thuốc]
            Box[Ảnh Vỏ hộp / Lọ / Vỉ] --> OCR_B[Local Trained OCR Model<br/>chuyên biệt Vỏ hộp/Nhãn] --> LookupB[Truy vấn API Thuốc<br/>OpenSource Trong/Ngoài nước] --> Form[Smart Form Input<br/>User nhập liều dùng + buổi uống]
        end
    end

    subgraph G3 [Giai đoạn 3: Data Normalization Engine]
        LookupA --> Norm[Mapping Thương Hiệu ➔ Hoạt Chất Gốc<br/>Fuzzy Match + Dictionary Lookup]
        Form --> Norm
    end

    subgraph G4 [Giai đoạn 4: Unified Active Inventory Aggregator]
        Norm --> Agg[Tủ Thuốc Cá Nhân Tổng Hợp<br/>Active Medication Inventory]
    end

    subgraph G5 [Giai đoạn 5: Multi-Layer Cross-Evaluation Engine]
        UP --> Eval[Multi-Layer Analysis Engine]
        Agg --> Eval
        
        Eval --> L1[Layer 1: Trùng lặp & Quá liều Hoạt chất]
        Eval --> L2[Layer 2: Tương tác Thuốc - Thuốc]
        Eval --> L3[Layer 3: Tương tác Thuốc - Bệnh nền]
        Eval --> L4[Layer 4: Đối chiếu Liều Kê Toa /<br/>Liều Tự Nhập vs. Liều Khuyến Cáo<br/>theo Tuổi & Bệnh nền]
    end

    subgraph G6 [Báo Cáo UI & Kết Quả]
        L1 --> Report[Báo Cáo Phân Cấp Mức Cảnh Báo<br/>Đỏ / Vàng / Xanh + Summary & Lời khuyên cuối cùng]
        L2 --> Report
        L3 --> Report
        L4 --> Report
        Report --> History[Lưu vào Lịch Sử Quét<br/>+ Lịch Nhắc Nhở Uống Thuốc]
    end
```

> **Ghi chú luồng:** Sơ đồ trên hợp nhất **User Pipeline 1** (Vỏ/lọ/hộp thuốc — Branch B) và **User Pipeline 2** (Toa thuốc in nhiệt — Branch A) như đã định nghĩa ở phần đầu tài liệu. Layer 4 (mới) đảm nhiệm việc: (a) với toa thuốc — kiểm tra liều bác sĩ kê có phù hợp với tuổi/bệnh nền của User; (b) với vỏ hộp — đối chiếu liều/buổi uống User tự nhập với liều khuyến cáo chuẩn.

---

## 3. Thiết Kế Duo-Input Stream & Smart Crop Logic

Để tối ưu hóa độ chính xác cho từng loại định dạng tài liệu, hệ thống phân chia luồng xử lý đầu vào (Dual Input Stream) theo thiết kế sau:

| Tiêu chí so sánh | 📜 User Pipeline 2: Toa Thuốc In Nhiệt (Prescription) | 📦 User Pipeline 1: Vỏ Hộp / Lọ Thuốc (Packaging) |
| :--- | :--- | :--- |
| **Tiền xử lý hình ảnh** | Phân tích ảnh nguyên bản toàn trang (Full-page analysis), downscale + tối ưu cho chữ in nhiệt/dot-matrix mờ, nhăn. | Áp dụng **Smart Crop** khoanh vùng nhãn chứa tên thương hiệu và hàm lượng để tăng chất lượng vùng nhận dạng. |
| **Công nghệ AI áp dụng** | **Model OCR tự huấn luyện, chạy on-premise**, chuyên biệt cho hóa đơn/toa thuốc in nhiệt (nền tảng khởi điểm: PP-OCRv6 ONNX; sẽ train lại chuyên sâu ở giai đoạn sau). Không gọi VLM thương mại bên ngoài. | **Model OCR tự huấn luyện, chạy on-premise**, chuyên biệt cho nhãn vỏ hộp/lọ/vỉ (chữ 3D, cong vồng, bóng sáng). Không gọi VLM thương mại bên ngoài. |
| **Truy vấn thông tin sản phẩm** | Sau khi OCR ra tên thuốc, gọi **API OpenSource trong/ngoài nước** (OpenFDA + CSDL thuốc Việt Nam nội bộ) để lấy đầy đủ thông tin hoạt chất, hàm lượng chuẩn, liều khuyến cáo. | Tương tự: sau khi OCR ra tên thuốc, gọi **API OpenSource trong/ngoài nước** để lấy thông tin sản phẩm chuẩn hóa. |
| **Các chỉ số trích xuất** | Tên thương mại, Hoạt chất, Hàm lượng, Số lượng, Hướng dẫn liều dùng (Liều lượng/Tần suất) do bác sĩ kê. | Tên thương mại, Hàm lượng. |
| **Xử lý Liều dùng** | AI trích xuất tự động liều bác sĩ kê từ toa; hệ thống **đối chiếu liều được kê với liều khuyến cáo chuẩn theo tuổi/bệnh nền của User** (xem Layer 4, mục 4.2). | Không có sẵn liều dùng trên nhãn ➔ Kích hoạt **One-tap Form bắt buộc**, yêu cầu User tự nhập liều lượng và chọn buổi uống trong ngày (Sáng/Trưa/Chiều/Tối) để hệ thống tư vấn phù hợp. |
| **Mục tiêu luồng** | Trích xuất nhanh toàn bộ đơn thuốc theo chỉ định của bác sĩ, đồng thời kiểm tra tính phù hợp của liều đã kê. | Bổ sung nhanh các thuốc tự mua ngoài đơn vào Tủ thuốc để đánh giá chéo. |

---

## 4. Chuẩn Hóa Dữ Liệu & Engine Đánh Giá Chéo (Normalization & Cross-Eval)

### 🧪 4.1. Chiến Lược Chuẩn Hóa Hoạt Chất (Normalization Strategy)
Một biệt dược có thể có nhiều tên thương mại khác nhau tại Việt Nam (Ví dụ: *Panadol, Efferalgan, Hapacol*). Nếu không chuẩn hóa về hoạt chất gốc, hệ thống sẽ bỏ sót các tương tác nguy hiểm hoặc cảnh báo trùng lặp.
* **Hoạt chất hóa (Active Ingredient Mapping):**
  Hệ thống sử dụng cơ sở dữ liệu thuốc quốc gia kết hợp thuật toán **Fuzzy Matching** (như Levenshtein Distance) và tra cứu từ điển cục bộ (Dictionary Lookup) để khớp chính xác tên thương mại về mã định danh hoạt chất gốc chuẩn (*Paracetamol*).
* **Smart Search Autocomplete:**
  Khi người dùng nhập thủ công hoặc chỉnh sửa thông tin do AI nhận diện sai, hệ thống hiển thị danh sách gợi ý tự động hoàn thành từ cơ sở dữ liệu đã chuẩn hóa, buộc dữ liệu nhập vào phải thuộc danh mục kiểm soát.

### ⚠️ 4.2. Logic Cảnh Báo Tương Tác 3 Lớp (3-Tier Alert System)
Sau khi đưa tất cả các thuốc về dạng hoạt chất gốc, Cross-Evaluation Engine thực hiện quét qua cơ sở dữ liệu tương tác y học và đưa ra phân cấp cảnh báo trực quan:

| Mức Độ Cảnh Báo | Phân Loại | Ý Nghĩa Y Khoa | Hành Động Khuyến Nghị trên UI |
| :---: | :--- | :--- | :--- |
| **🔴 HIGH** | **Đỏ (Nguy hiểm)** | Tương tác chống chỉ định (Contraindicated) có nguy cơ đe dọa tính mạng hoặc quá liều tối đa cho phép của một hoạt chất. | Hiển thị Banner lớn cảnh báo, khuyên người dùng tạm dừng uống thuốc và liên hệ ngay bác sĩ điều trị. |
| **🟡 MEDIUM** | **Vàng (Cảnh giác)** | Tương tác có điều kiện (Drug-Drug interaction) làm giảm dược lực học hoặc gây tác dụng phụ ở mức trung bình. | Hướng dẫn người dùng điều chỉnh thời gian sử dụng thuốc (Ví dụ: uống cách nhau ít nhất 2 giờ). |
| **🟢 LOW** | **Xanh (Thông tin)** | Khuyến nghị hướng dẫn sử dụng an toàn thông thường. | Nhắc nhở thời điểm uống tối ưu (Trước ăn, sau ăn, sáng, tối). |

### 🧮 4.3. Layer 4 — Đối Chiếu Liều Dùng Thực Tế vs. Liều Khuyến Cáo (Dosage Appropriateness Layer)

Ngoài 3 lớp cảnh báo tương tác ở trên, Cross-Evaluation Engine thực hiện thêm **Layer 4** để trả lời câu hỏi: *"Liều đang dùng có phù hợp với User này không?"*

* **Với User Pipeline 2 (Toa thuốc in nhiệt):** Hệ thống lấy `dosage_instruction` do bác sĩ kê (đã trích xuất tự động), so sánh với **liều khuyến cáo chuẩn theo hoạt chất** (điều chỉnh theo tuổi, cân nặng nếu có, và bệnh nền trong `UserProfile`). Nếu liều kê vượt ngưỡng an toàn hoặc không phù hợp với bệnh nền (vd: chống chỉ định theo tuổi), hệ thống gắn cảnh báo tương ứng — **nhưng luôn ưu tiên khuyến nghị User xác nhận lại với bác sĩ kê đơn**, không tự ý kết luận toa sai.
* **Với User Pipeline 1 (Vỏ hộp/lọ thuốc):** Hệ thống lấy liều + buổi uống do User tự nhập ở bước Smart Form, so sánh với liều khuyến cáo chuẩn từ CSDL thuốc để đưa ra lời khuyên điều chỉnh (nếu cần).
* **Đầu ra cuối cùng (Final Summary):** Sau khi chạy đủ 4 layer, hệ thống tổng hợp toàn bộ cảnh báo thành một **bản tóm tắt (Summary) và lời khuyên cuối cùng** duy nhất hiển thị ở đầu báo cáo, giúp User nắm nhanh tình trạng tổng thể trước khi xem chi tiết từng cảnh báo.

---

## 5. Thiết Kế Cơ Sở Dữ Liệu & Data Schemas

Dưới đây là các cấu trúc dữ liệu chuẩn được định nghĩa bằng **Pydantic (Python Backend)** và giao tiếp tương đương **TypeScript Interfaces (Frontend)**:

### 🛡️ 5.1. Định Nghĩa Phía Backend (Pydantic Schemas)

```python
from typing import List, Optional
from pydantic import BaseModel, Field

class UserProfile(BaseModel):
    age: int = Field(..., ge=0, le=120, description="Tuổi bệnh nhân")
    conditions: List[str] = Field(default=[], description="Danh sách mã/tên bệnh nền (Ví dụ: Hypertension, Diabetes)")
    allergies: List[str] = Field(default=[], description="Danh sách hoạt chất dị ứng")

class DrugItem(BaseModel):
    brand_name: str = Field(..., description="Tên thương mại trích xuất được")
    active_ingredient: Optional[str] = Field(None, description="Tên hoạt chất sau khi chuẩn hóa")
    strength: str = Field(..., description="Hàm lượng (Ví dụ: 500mg, 10ml)")
    dosage_instruction: Optional[str] = Field(None, description="Hướng dẫn liều dùng")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Độ tin cậy trích xuất của AI")
    is_verified: bool = Field(False, description="Người dùng đã xác nhận tính chính xác chưa")

class Prescription(BaseModel):
    source_type: str = Field(..., description="Nguồn trích xuất: 'prescription' hoặc 'packaging'")
    items: List[DrugItem] = Field(..., description="Danh sách các loại thuốc trích xuất được")

class InteractionAlert(BaseModel):
    severity: str = Field(..., description="Mức độ nghiêm trọng: 'HIGH', 'MEDIUM', 'LOW'")
    title: str = Field(..., description="Tiêu đề cảnh báo ngắn gọn")
    description: str = Field(..., description="Chi tiết tương tác/xung đột thuốc")
    recommendation: str = Field(..., description="Lời khuyên y tế hướng xử lý")

class DosageCheckResult(BaseModel):
    """Kết quả Layer 4: Đối chiếu liều thực tế (kê toa hoặc tự nhập) với liều khuyến cáo."""
    drug_name: str = Field(..., description="Tên thuốc được kiểm tra")
    prescribed_or_input_dosage: str = Field(..., description="Liều được kê trên toa hoặc User tự nhập")
    recommended_dosage: str = Field(..., description="Liều khuyến cáo chuẩn theo hoạt chất/tuổi/bệnh nền")
    is_appropriate: bool = Field(..., description="Liều hiện tại có phù hợp hay không")
    note: Optional[str] = Field(None, description="Ghi chú giải thích, luôn khuyến nghị xác nhận lại với bác sĩ nếu có sai lệch")

class EvaluationResponse(BaseModel):
    total_drugs_analyzed: int
    alerts: List[InteractionAlert]
    dosage_checks: List[DosageCheckResult] = Field(default=[], description="Kết quả Layer 4 - đối chiếu liều dùng")
    schedule_suggestions: List[str] = Field(default=[], description="Gợi ý phân chia lịch uống thuốc an toàn")
    final_summary: str = Field(..., description="Tóm tắt tổng quan tình trạng và lời khuyên cuối cùng cho User")

class MedicationHistoryEntry(BaseModel):
    """Một lần quét/đánh giá đã lưu vào Lịch Sử của User."""
    scan_id: str = Field(..., description="Định danh duy nhất của lần quét")
    scanned_at: str = Field(..., description="Thời điểm quét (ISO 8601)")
    source_type: str = Field(..., description="'prescription' hoặc 'packaging'")
    drug_names: List[str] = Field(default=[], description="Danh sách tên thuốc trong lần quét này")
    highest_severity: Optional[str] = Field(None, description="Mức cảnh báo cao nhất phát hiện được: HIGH/MEDIUM/LOW")

class MedicationReminder(BaseModel):
    """Nhắc nhở uống thuốc định kỳ cho một thuốc trong Tủ Thuốc."""
    reminder_id: str = Field(..., description="Định danh duy nhất")
    drug_name: str
    times_of_day: List[str] = Field(..., description="Các buổi uống trong ngày, vd: ['Sáng','Trưa','Tối']")
    is_active: bool = Field(True, description="Nhắc nhở còn hiệu lực hay đã tắt")
```

### 💻 5.2. Định Nghĩa Phía Frontend (TypeScript Interfaces)

```typescript
export interface IUserProfile {
  age: number;
  conditions: string[];
  allergies: string[];
}

export interface IDrugItem {
  brandName: string;
  activeIngredient?: string;
  strength: string;
  dosageInstruction?: string;
  confidenceScore: number;
  isVerified: boolean;
}

export interface IPrescription {
  sourceType: 'prescription' | 'packaging';
  items: IDrugItem[];
}

export interface IInteractionAlert {
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  description: string;
  recommendation: string;
}

export interface IDosageCheckResult {
  drugName: string;
  prescribedOrInputDosage: string;
  recommendedDosage: string;
  isAppropriate: boolean;
  note?: string;
}

export interface IEvaluationResponse {
  totalDrugsAnalyzed: number;
  alerts: IInteractionAlert[];
  dosageChecks: IDosageCheckResult[];
  scheduleSuggestions: string[];
  finalSummary: string;
}

export interface IMedicationHistoryEntry {
  scanId: string;
  scannedAt: string;
  sourceType: 'prescription' | 'packaging';
  drugNames: string[];
  highestSeverity?: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface IMedicationReminder {
  reminderId: string;
  drugName: string;
  timesOfDay: string[];
  isActive: boolean;
}
```

---

## 6. Cấu Trúc Kiến Trúc Mã Nguồn (Monorepo System Structure)

Hệ thống được tổ chức theo kiến trúc Monorepo để dễ dàng đồng bộ cấu hình và triển khai độc lập:

```text
mediscan-ai/
├── backend/                  # Python FastAPI Backend Services
│   ├── app/
│   │   ├── api/v1/endpoints/ # Định nghĩa các API endpoints REST
│   │   │   ├── ocr.py        # API tiếp nhận ảnh - User Pipeline 1 & 2 (POST /api/v1/ocr/scan)
│   │   │   ├── evaluate.py   # API phân tích tương tác chéo (4 Layers)
│   │   │   ├── history.py    # API Lịch sử quét thuốc của User
│   │   │   └── reminders.py  # API Nhắc nhở uống thuốc
│   │   ├── core/config.py    # Quản lý cấu hình toàn cục & API Keys (.env)
│   │   ├── schemas/          # Các Pydantic Models mô tả dữ liệu API
│   │   ├── data/vietnam_drugs_db.json # CSDL thuốc Việt Nam mẫu (100+ thuốc)
│   │   ├── services/         # Logic xử lý cốt lõi độc lập
│   │   │   ├── ocr_engine.py           # Model OCR tự train on-premise (Pipeline 1 & 2), KHÔNG gọi VLM ngoài
│   │   │   ├── drug_database.py        # Truy vấn API OpenSource (OpenFDA + VN Drug DB)
│   │   │   ├── normalization_service.py# Chuẩn hóa tên thuốc & Fuzzy Matching (RapidFuzz)
│   │   │   ├── evaluation_service.py   # Engine 4-Layer: Quá liều / Thuốc-Thuốc / Thuốc-Bệnh nền / Đối chiếu Liều
│   │   │   └── clinical_service.py     # Local LLM (Ollama) hỗ trợ suy luận lâm sàng
│   │   └── main.py            # File chạy chính khởi động uvicorn ASGI
│   └── requirements.txt      # Thư viện Python phụ thuộc
│
└── frontend/                  # Next.js Web Desktop Application (App Router)
    ├── src/app/                # Các trang nghiệp vụ (Routing) — 3 trang chính
    │   ├── onboarding/         # Trang 1: Hồ sơ User (tuổi, bệnh nền, dị ứng)
    │   ├── scan/                # Trang 2: MediScan AI chính — Trích xuất/Tổng hợp/Đánh giá
    │   ├── eval-report/         # Báo cáo kết quả phân tích tương tác chi tiết (thuộc Trang 2)
    │   └── account/              # Trang 3: Quản lý User — Tủ thuốc, Lịch sử, Nhắc nhở
    │       ├── cabinet/          # Kho thuốc hiện tại
    │       ├── history/          # Lịch sử các lần quét
    │       └── reminders/        # Quản lý lịch nhắc uống thuốc
    ├── src/components/           # Các Component dùng chung tối ưu
    │   ├── ui/                    # Thành phần cơ bản (Buttons, Inputs từ Shadcn UI)
    │   ├── scan/SmartCropModal.tsx        # Logic Crop ảnh vỏ hộp thuốc phía Client
    │   ├── scan/DrugVerificationForm.tsx  # HITL — xác nhận/sửa kết quả OCR
    │   ├── cabinet/ActiveCabinet.tsx      # Giao diện Tủ thuốc tập trung (Inventory)
    │   ├── history/HistoryTimeline.tsx    # Danh sách lịch sử các lần quét
    │   └── reminders/ReminderScheduler.tsx# UI thiết lập nhắc nhở uống thuốc
    ├── src/services/              # Xử lý kết nối API, Axios, TanStack Query hooks
    ├── package.json               # Dependencies quản lý bởi Node / npm
    └── tailwind.config.js         # Cấu hình UI theme của TailwindCSS
```

---

## 7. Quy Trình Bảo Mật & Trách Nhiệm Pháp Lý (Security & Legal)

### 🔒 7.1. Bảo Vệ Dữ Liệu Riêng Tư (Data Privacy)
Để tuân thủ các nguyên tắc bảo mật dữ liệu y tế nhạy cảm (HIPAA/GDPR-like):
* **In-memory Processing:** Mọi tệp hình ảnh đơn thuốc/vỏ hộp tải lên Backend chỉ được nạp trực tiếp vào RAM (In-memory buffer), gửi tới API VLM của Cloud Node qua kết nối HTTPS bảo mật và giải phóng ngay lập tức.
* **Không lưu trữ ảnh thô:** Hệ thống không lưu trữ ảnh đơn thuốc vật lý lên đĩa cứng của server trừ khi người dùng kích hoạt tính năng "Lịch sử Toa thuốc" và đồng ý bằng văn bản điện tử (Consent Checkbox).

### ⚖️ 7.2. Bộ Lọc Điều Khoản Miễn Trừ Trách Nhiệm (Disclaimer Interceptor)
Quy trình hiển thị kết quả y khoa bắt buộc tuân theo quy tắc an toàn nghiêm ngặt:
* **First-run Interceptor:** Khi người dùng truy cập trang Phân Tích Báo Cáo lần đầu tiên, hệ thống sẽ kích hoạt một cửa sổ Modal yêu cầu người dùng đọc và chấp nhận các điều khoản miễn trừ trách nhiệm y tế.
* **Nhắc nhở thường trực:** Mọi trang kết quả đánh giá tương tác thuốc đều đính kèm một dòng cảnh báo dễ nhìn ở chân trang, ghi rõ: *"Các kết quả phân tích từ AI chỉ mang tính chất tham khảo, không có giá trị thay thế chỉ định chuyên môn của Bác sĩ."*
