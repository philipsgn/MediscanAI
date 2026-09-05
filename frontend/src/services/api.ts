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
  /** Auth endpoints (Stage 8) */
  authRegister: '/auth/register',
  authLogin: '/auth/login',
  authRefresh: '/auth/refresh',
  authMe: '/auth/me',
  /** Profile endpoints (Stage 9) */
  profileMe: '/profile/me',
  profileUpsert: '/profile/me',
  /** History endpoints (Stage 10) */
  historyMe: '/history/me',
  /** Reminder endpoints (Stage 10) */
  remindersMe: '/reminders/me',
  remindersCreate: '/reminders',
  /** Cabinet / Medications endpoints (Stage 10) */
  medications: '/medications',
  medicationsMe: '/medications/me',
  /** AI Telemetry & Active Learning endpoints (Stage 18) */
  verifyLearnedDrug: '/drugs/verify-learned',
  aiCacheMetrics: '/metrics/ai-cache',
} as const;

export type ApiEndpointPath = keyof typeof API_ENDPOINTS;

/** Axios instance dùng chung toàn app (timeout mặc định cho call JSON ngắn). */
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
});

/** Thêm Interceptor đính kèm JWT Token vào Header nếu có */
apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('mediscan_access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

/** Interceptor tự động làm mới Access Token (Auto-Refresh) khi nhận HTTP 401 */
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (!originalRequest || typeof window === 'undefined') {
      return Promise.reject(error);
    }

    const isAuthEndpoint =
      originalRequest.url?.includes('/auth/login') ||
      originalRequest.url?.includes('/auth/register') ||
      originalRequest.url?.includes('/auth/refresh');

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('mediscan_refresh_token');
      if (!refreshToken) {
        isRefreshing = false;
        return Promise.reject(error);
      }

      try {
        const refreshResponse = await axios.post<{
          accessToken: string;
          refreshToken: string;
        }>(`${API_BASE_URL}${API_ENDPOINTS.authRefresh}`, {
          refreshToken,
          refresh_token: refreshToken,
        });

        const newAccessToken = refreshResponse.data.accessToken;
        localStorage.setItem('mediscan_access_token', newAccessToken);
        const expires = new Date(Date.now() + 7 * 86400000).toUTCString();
        document.cookie = `mediscan_auth_token=${encodeURIComponent(newAccessToken)}; expires=${expires}; path=/; SameSite=Lax`;

        processQueue(null, newAccessToken);
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return apiClient(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        localStorage.removeItem('mediscan_access_token');
        localStorage.removeItem('mediscan_refresh_token');
        localStorage.removeItem('mediscan_auth_user');
        document.cookie = 'mediscan_auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        if (
          window.location.pathname !== '/login' &&
          window.location.pathname !== '/register'
        ) {
          window.location.href = '/login';
        }
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);


/** Dựng URL đầy đủ từ bảng endpoint (dùng trong service layer / script kiểm chứng). */
export function buildEndpoint(path: ApiEndpointPath): string {
  return `${API_BASE_URL}${API_ENDPOINTS[path]}`;
}
