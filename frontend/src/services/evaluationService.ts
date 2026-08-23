/**
 * [P1/F4.4] Evaluation Service — Single Source of Truth cho POST /evaluate.
 *
 * Tuân thủ AGENTS.md §3.D.3: mọi API call qua src/services/.
 * Component (ActiveCabinet) KHÔNG được tự ghép URL hay hardcode base path.
 *
 * Endpoint path điều khiển tập trung trong api.ts::API_ENDPOINTS — nếu backend
 * đổi route, sửa duy nhất ở đây.
 */
import { useMutation, UseMutationResult } from '@tanstack/react-query';
import { apiClient, API_ENDPOINTS } from './api';
import {
  IDrugEvaluationRequest,
  IEvaluationResponse,
} from '@/types/medication';

/**
 * Core mutation: gửi hàng danh sách thuốc + user profile tới /evaluate.
 * Timeout 45s (rule-engine + LLM enrichment có thể chậm trên máy yếu).
 */
export const useEvaluation = (): UseMutationResult<
  IEvaluationResponse,
  Error,
  IDrugEvaluationRequest
> => {
  return useMutation({
    mutationFn: async (payload: IDrugEvaluationRequest) => {
      const response = await apiClient.post<IEvaluationResponse>(
        API_ENDPOINTS.evaluate,
        payload,
        {
          headers: { 'Content-Type': 'application/json' },
          timeout: 45_000,
        }
      );
            return response.data;
    },
    retry: 1,
  });
};
