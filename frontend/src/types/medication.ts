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
