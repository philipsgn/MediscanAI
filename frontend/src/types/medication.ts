/**
 * TypeScript Interfaces cho Dự án Mediscan AI Frontend
 * Khớp 100% với Pydantic Schemas Backend (backend/app/schemas/ — package init __init__.py)
 */

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
  // Extended fields from Drug Database (khớp backend/app/schemas/__init__.py DrugItem)
  drugId?: string;
  category?: string;
  maxDailyDosage?: string;
  warnings?: string[];
  /** [P3/F3.6 đồng bộ §3.A.2] exact | fuzzy | ingredient_fallback | openfda | openfda_ingredient */
  matchMethod?: 'exact' | 'fuzzy' | 'ingredient_fallback' | 'openfda' | 'openfda_ingredient';
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

export interface IEvaluationResponse {
  totalDrugsAnalyzed: number;
  alerts: IInteractionAlert[];
  scheduleSuggestions: string[];
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
