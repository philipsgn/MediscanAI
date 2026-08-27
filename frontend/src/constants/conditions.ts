/**
 * Constants bệnh nền & dị ứng — Single Source of Truth cho toàn bộ Frontend.
 *
 * Các giá trị `value` PHẢI khớp chính xác (case-insensitive) với chuỗi
 * trong `DRUG_CONDITION_CONFLICTS` tại backend/app/services/evaluation_service.py
 * để Layer 3 (Drug-Condition) match đúng khi đánh giá tương tác.
 *
 * Backend so khớp bằng: user_conditions.add(c.strip().lower())
 * → "Cao huyết áp".lower() === "cao huyết áp" ∈ conflict.conditions
 */

export interface ConditionOption {
  /** Giá trị lưu vào UserProfile.conditions — khớp backend rule-engine */
  value: string;
  /** Nhãn hiển thị trên UI */
  label: string;
  /** true = backend DRUG_CONDITION_CONFLICTS có rule cho bệnh này */
  hasBackendRule: boolean;
}

export interface AllergyOption {
  /** Giá trị lưu vào UserProfile.allergies — khớp backend rule-engine */
  value: string;
  /** Nhãn hiển thị trên UI */
  label: string;
}

/**
 * Danh sách bệnh nền — mỗi entry map 1:1 với condition tags
 * trong DRUG_CONDITION_CONFLICTS (evaluation_service.py dòng 107-164).
 *
 * Các mục có `hasBackendRule: false` chỉ mang tính tham khảo —
 * backend chưa có rule kích hoạt cảnh báo cho chúng.
 */
export const KNOWN_CONDITIONS: readonly ConditionOption[] = [
  // ── Có rule trong DRUG_CONDITION_CONFLICTS ──
  { value: 'Cao huyết áp',       label: 'Cao huyết áp',       hasBackendRule: true },
  { value: 'Loét dạ dày',        label: 'Loét dạ dày',        hasBackendRule: true },
  { value: 'Suy thận',           label: 'Suy thận',           hasBackendRule: true },
  { value: 'Suy gan',            label: 'Suy gan',            hasBackendRule: true },
  { value: 'Hen suyễn',          label: 'Hen suyễn',          hasBackendRule: true },
  { value: 'Mang thai',          label: 'Mang thai',          hasBackendRule: true },
  // ── Tham khảo — backend chưa có rule ──
  { value: 'Tim mạch',           label: 'Tim mạch (tham khảo)',     hasBackendRule: false },
  { value: 'Đái tháo đường',     label: 'Đái tháo đường (tham khảo)', hasBackendRule: false },
] as const;

/**
 * Danh sách dị ứng phổ biến — quick-select chips.
 * Backend gộp allergies vào user_conditions (dòng 652),
 * nên "Dị ứng Penicillin" sẽ match conflict dòng 141-147.
 */
export const KNOWN_ALLERGIES: readonly AllergyOption[] = [
  { value: 'Dị ứng Penicillin',      label: 'Dị ứng Penicillin' },
  { value: 'Dị ứng Aspirin/NSAID',    label: 'Dị ứng Aspirin/NSAID' },
] as const;
