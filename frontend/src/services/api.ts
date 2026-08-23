/**
 * [P0/F4.1] API Configuration — SINGLE SOURCE OF TRUTH cho mọi endpoint.
 *
 * AGENTS.md §3.D.3 + ARCHITECTURE.md §6: mọi lời gọi API phải đi qua lớp
 * `src/services/`. Component KHÔNG được tự ghép URL/path hay hardcode base.
 *
 * Base URL: override qua NEXT_PUBLIC_API_URL (xem frontend/.env.example và
 * docker-compose.yml — mặc định đồng nhất http://localhost:8000/api/v1).
 */
import axios from 'axios';

export const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

/** Bảng endpoint tường minh — path riêng của từng API, cấm ghép chuỗi nơi khác. */
export const API_ENDPOINTS = {
  ocrScan: '/ocr/scan',
  evaluate: '/evaluate',
  /** [S4-Closeout/F4.3] Autocomplete từ điển thuốc (GET ?q=...&limit=...). */
  drugSearch: '/drugs/search',
} as const;

export type ApiEndpointPath = keyof typeof API_ENDPOINTS;

/** Axios instance dùng chung toàn app (timeout mặc định cho call JSON ngắn). */
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
});

/** Dựng URL đầy đủ từ bảng endpoint (dùng trong service layer / script kiểm chứng). */
export function buildEndpoint(path: ApiEndpointPath): string {
  return `${API_BASE_URL}${API_ENDPOINTS[path]}`;
}
