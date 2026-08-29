# 📋 MediscanAI OCR & Normalization — Backlog & Tracking Issues

Tài liệu này ghi nhận các đầu việc theo dõi và cải tiến sau khi hoàn thành tích hợp **PP-OCRv6_tiny ONNX** (Giai đoạn 2).

---

## 📌 Danh Sách Task Theo Dõi & Kế Hoạch Tiếp Theo

### 1. [ISSUE-OCR-01] [Priority: HIGH] Mở rộng Test Set Đánh Giá Thực Tế (N=10-15 ảnh/loại)
- **Mô tả:** Mở rộng tập dữ liệu benchmark từ $N=1$ hiện tại lên tối thiểu 10–15 ảnh cho mỗi loại hình đầu vào:
  - Vỏ hộp thuốc (Packaging / Box)
  - Lọ thuốc (Bottle / Container)
  - Toa thuốc (Prescription / Receipt)
  - Vỉ thuốc (Blister pack)
- **Yêu cầu:** Ưu tiên ảnh chụp bằng camera điện thoại thực tế trong điều kiện ánh sáng đa dạng (bóng mờ, góc chụp nghiêng, nếp nhăn, vệt sáng) để đo lường Character Error Rate (CER), Word Error Rate (WER) và Latency sát với điều kiện sử dụng thực tế.
- **Nhãn:** `dataset`, `benchmark`, `priority-high`

---

### 2. [ISSUE-NORM-02] [Priority: MEDIUM] Giám sát & Đánh giá Thực tế Tier 4 OpenFDA Fallback
- **Mô tả:** Tiếp tục theo dõi các ca truy vấn thực tế rơi xuống tầng tra cứu OpenFDA (`match_method="openfda"`).
- **Yêu cầu:** 
  - Đảm bảo cơ chế tìm kiếm cụm từ chính xác (`openfda.brand_name:"..."`) không còn hiện tượng gán bừa biệt dược không liên quan (như trường hợp `Betadine`/`Varenicline` trước đây).
  - Duy trì nguyên tắc `is_verified = False` và bắt buộc xác nhận qua Human-in-the-Loop (HITL).
- **Nhãn:** `normalization`, `openfda`, `safety`, `priority-medium`

---

### 3. [ISSUE-DATA-03] [Priority: MEDIUM] Mở rộng Danh mục CSDL Thuốc Việt Nam (`vietnam_drugs_db.json`)
- **Mô tả:** CSDL mẫu hiện tại có 100 bản ghi thuốc. Cần bổ sung các thuốc và hoạt chất phổ biến thường gặp trên đơn thuốc Việt Nam nhưng chưa có trong DB:
  - `Alphachymotrypsin` / `Chymotrypsin` (4.2mg / 21 microkatals)
  - Các kháng sinh, kháng viêm và thuốc tim mạch phổ biến khác.
- **Mục tiêu:** Giảm tỷ lệ thuốc rơi vào trạng thái `match_method: null` / `is_verified: False`.
- **Nhãn:** `data`, `drug-database`, `priority-medium`

---

### 4. [ISSUE-OCR-04] [Priority: LOW] Phát triển Parser Chuyên Biệt Nâng Cao Cho Bao Bì Thuốc
- **Mô tả:** Hiện tại pipeline packaging sử dụng bộ lọc từ khóa/slogan và trích xuất hàm lượng cơ bản.
- **Yêu cầu:** Khi thu thập thêm nhiều mẫu bao bì/hộp thuốc có cấu trúc đồ họa phức tạp, cân nhắc phát triển parser vị trí/heuristic chuyên biệt (phân tích kích thước font chữ, phân cấp tiêu đề, nhận diện thành phần `w/w`, `w/v`) tương tự như parser dòng đã hoàn thiện cho toa thuốc.
- **Nhãn:** `ocr`, `packaging`, `enhancement`, `priority-low`
