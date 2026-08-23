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
