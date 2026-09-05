/**
 * [S4-Closeout/F4.3] Drug Lookup Service — duy nhất cổng giao tiếp với
 * GET /drugs/search (autocomplete từ điển thuốc).
 *
 * Component KHÔNG tự gọi axios hay ghép URL (AGENTS §3.D.3).
 */
import { apiClient, API_ENDPOINTS } from './api';
import { IDrugSearchResult } from '@/types/medication';

/**
 * Tìm thuốc theo từ khóa (brand fuzzy / hoạt chất substring) — DB thật
 * phía backend. `signal` cho phép abort khi user gõ tiếp (debounce cleanup).
 */
export async function searchDrugs(
  q: string,
  signal?: AbortSignal
): Promise<IDrugSearchResult[]> {
  const response = await apiClient.get<IDrugSearchResult[]>(
    API_ENDPOINTS.drugSearch,
    {
      params: { q },
      signal,
      // Autocomplete phải nhanh — 8s là đủ cho local DB lookup
      timeout: 8_000,
    }
  );
  return response.data;
}

export interface IVerifyLearnedDrugPayload {
  brand_name: string;
  confirmed_active_ingredient: string;
  strength?: string;
  category?: string;
  is_supplement?: boolean;
  user_notes?: string;
}

/**
 * [Task 18.3] Active Learning Loop & Anti-Poisoning Feedback API.
 * Gửi xác nhận hoặc chỉnh sửa của người dùng lên Backend để cập nhật CSDL.
 */
export async function verifyLearnedDrug(payload: IVerifyLearnedDrugPayload) {
  const response = await apiClient.post(API_ENDPOINTS.verifyLearnedDrug, payload);
  return response.data;
}

export interface IAICacheMetrics {
  total_lookups: number;
  cache_hits: number;
  cache_misses: number;
  cache_hit_ratio_percent: number;
  estimated_tokens_saved_session: number;
  estimated_tokens_saved_all_time: number;
  estimated_cost_saved_usd: number;
  estimated_latency_saved_seconds: number;
  storage_stats: {
    total_learned_drugs: number;
    verified_count: number;
    pending_review_count: number;
    user_corrected_count: number;
    cumulative_db_hits: number;
  };
  top_reused_drugs: Array<{
    brand_name: string;
    active_ingredient?: string;
    hit_count: number;
    status: string;
    is_supplement: boolean;
  }>;
}

/**
 * [Task 18.4] AI Telemetry & Cost Observability API.
 */
export async function getAICacheMetrics(): Promise<IAICacheMetrics> {
  const response = await apiClient.get<IAICacheMetrics>(API_ENDPOINTS.aiCacheMetrics);
  return response.data;
}
