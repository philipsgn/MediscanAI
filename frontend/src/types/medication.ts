/**
 * TypeScript Interfaces cho Dự án Mediscan AI Frontend
 * Khớp 100% với Pydantic Schemas Backend (backend/app/schemas/ — package init __init__.py)
 */

export interface IUserProfile {
  userId?: string;
  age: number;
  birthYear?: number | null;
  weightKg?: number | null;
  heightCm?: number | null;
  bmi?: number | null;
  gender?: 'male' | 'female' | 'other' | null;
  conditions: string[];
  allergies: string[];
  isPregnant?: boolean;
  isBreastfeeding?: boolean;
  updatedAt?: string;
}

export interface IDrugItem {
  brandName: string;
  activeIngredient?: string;
  strength: string;
  dosageInstruction?: string;
  confidenceScore: number;
  isVerified: boolean;
  // Extended fields from Drug Database (khớp backend/app/schemas/__init__.py DrugItem)
  drugId?: string;
  category?: string;
  maxDailyDosage?: string;
  warnings?: string[];
  /** [P3/F3.6 đồng bộ §3.A.2] exact | fuzzy | ingredient_fallback | openfda | openfda_ingredient */
  matchMethod?: 'exact' | 'fuzzy' | 'ingredient_fallback' | 'openfda' | 'openfda_ingredient';
  /** [F3.7] Cảnh báo nhẹ hàm lượng nhập khác DB chuẩn — hiển thị UI, không chặn submit. */
  strengthMismatchWarning?: string | null;
}

export interface IExtractedDrugItem {
  id: string;
  drugName: string;
  activeIngredient?: string | null;
  strength?: string | null;
  dosageForm?: string | null;
  dosageInstruction?: string | null;
  timeSlots: string[]; // ['morning', 'noon', 'afternoon', 'evening']
  slotTimes: Record<string, string>; // { morning: '08:00', noon: '12:00', afternoon: '17:00', evening: '21:00' }
  durationDays?: number | null;
  startDate?: string | null; // YYYY-MM-DD
  isTimeExtracted: boolean;
  sourceStream: 'prescription' | 'packaging' | 'manual';
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

/** [Task 5.5] Layer 4: kết quả đối chiếu liều dùng — khớp DosageCheckResult backend. */
export interface IDosageCheckResult {
  drugName: string;
  prescribedOrInputDosage: string;
  recommendedDosage: string;
  /** true=phù hợp, false=chênh lệch, null=không đủ dữ liệu/trẻ em ngoài phạm vi */
  isAppropriate: boolean | null;
  note: string;
}

export interface IEvaluationResponse {
  totalDrugsAnalyzed: number;
  alerts: IInteractionAlert[];
  scheduleSuggestions: string[];
  /** [Task 5.5] Layer 4 — kết quả đối chiếu liều theo population */
  dosageChecks: IDosageCheckResult[];
  /** [Task 5.5] Tóm tắt tổng hợp toàn bộ 4 layer */
  finalSummary: string;
}

export interface IDrugEvaluationRequest {
  userProfile?: IUserProfile;
  drugs: IDrugItem[];
}

/* ═══════════════════════════════════════════════════════════════════════════
   [P0/F4.2] Full Scan Response — đồng bộ 100% với backend FullScanResponse
   (backend/app/schemas/ocr_schema.py).
   WIRE-FORMAT LƯU Ý (quyết định Audit-S3/P0, có test pin phía backend):
   - Envelope NGOÀI: camelCase (to_camel alias).
   - Payload `clinicalAssessment` BÊN TRONG: GIỮ snake_case lịch sử
     (4 model clinical không có alias — đổi sẽ phá contract §3.A).
   ═══════════════════════════════════════════════════════════════════════════ */

export interface IOCRItem {
  text: string;
  confidence: number;
  box: number[];
}

/** Alert trong payload clinicalAssessment — snake_case theo wire-format legacy. */
export interface IClinicalInteractionAlert {
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  description: string;
  recommendation: string;
  interacting_drugs?: string[];
  evidence_level?: string | null;
}

export interface IClinicalConditionAlert {
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  description: string;
  recommendation: string;
  drug_name: string;
  condition: string;
  evidence_level?: string | null;
}

export interface IOverdoseAlert {
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  description: string;
  recommendation: string;
  ingredient: string;
  total_daily_mg: number;
  max_safe_mg?: number | null;
}

export interface IClinicalAssessmentPayload {
  drug_drug_interactions: IClinicalInteractionAlert[];
  drug_condition_interactions: IClinicalConditionAlert[];
  overdose_duplication_alerts: IOverdoseAlert[];
  clinical_recommendations: string[];
  monitoring_parameters: string[];
  disclaimer: string;
}

export interface IClinicalAlertSummary {
  totalAlerts: number;
  highCount: number;
  mediumCount: number;
  lowCount: number;
  drugDrugInteractions: number;
  drugConditionInteractions: number;
  overdoseDuplication: number;
}

/**
 * Response thật của POST /api/v1/ocr/scan.
 * `mappedDrugs` ≡ IDrugItem[] (MappedDrugItem backend trùng shape DrugItem,
 * bao gồm matchMethod: exact | fuzzy | ingredient_fallback | openfda*).
 */
/**
 * [S4-Closeout/F4.3] Kết quả autocomplete rút gọn — khớp 100% backend
 * DrugSearchResult (camelCase wire). KHÔNG phải full IDrugItem.
 */
export interface IDrugSearchResult {
  drugId: string;
  brandName: string;
  activeIngredient?: string | null;
  strength: string;
}

export interface IFullScanResponse {
  engine: string;
  sourceType: 'prescription' | 'packaging';
  rawOcrItems: IOCRItem[];
  ocrLatencyMs: number;
  slaExceeded: boolean;
  imageWidth: number;
  imageHeight: number;
  mappedDrugs: IDrugItem[];
  clinicalAssessment: IClinicalAssessmentPayload | null;
  clinicalSummary: IClinicalAlertSummary | null;
  totalLatencyMs: number;
  normalizationLatencyMs: number;
  clinicalLatencyMs: number;
}
