import { isAxiosError } from 'axios';
import { apiClient, API_ENDPOINTS } from './api';
import { ILoginRequest, IRegisterRequest, ITokenResponse, IUser } from '@/types/auth';

export interface IAuthErrorDetail {
  error_code?: string;
  message?: string;
  service?: string;
  stage?: string;
  request_id?: string;
  retryable?: boolean;
}

export function extractAuthErrorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error)) {
    if (!error.response) {
      return 'Không thể kết nối đến máy chủ Backend. Vui lòng kiểm tra lại kết nối mạng hoặc máy chủ.';
    }
    const detail = error.response.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (typeof detail === 'object' && detail !== null) {
      if (Array.isArray(detail)) {
        return detail
          .map((d: { msg?: string; loc?: string[] }) => {
            const field = d.loc ? d.loc[d.loc.length - 1] : '';
            return field ? `Trường ${field}: ${d.msg || 'Dữ liệu không hợp lệ'}` : d.msg || 'Dữ liệu không hợp lệ';
          })
          .join('; ');
      }
      if ('message' in detail && typeof (detail as IAuthErrorDetail).message === 'string') {
        return (detail as IAuthErrorDetail).message || fallback;
      }
    }
    return fallback;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}

export const authService = {
  async register(payload: IRegisterRequest): Promise<ITokenResponse> {
    try {
      const cleanPayload = {
        username: payload.username.trim(),
        email: payload.email.trim(),
        password: payload.password,
        full_name: payload.fullName?.trim() || undefined,
        fullName: payload.fullName?.trim() || undefined,
      };
      const response = await apiClient.post<ITokenResponse>(
        API_ENDPOINTS.authRegister,
        cleanPayload
      );
      return response.data;
    } catch (error: unknown) {
      const msg = extractAuthErrorMessage(
        error,
        'Đăng ký không thành công. Vui lòng kiểm tra lại thông tin nhập vào.'
      );
      throw new Error(msg);
    }
  },

  async login(payload: ILoginRequest): Promise<ITokenResponse> {
    try {
      const cleanPayload = {
        username: payload.usernameOrEmail.trim(),
        usernameOrEmail: payload.usernameOrEmail.trim(),
        password: payload.password,
      };
      const response = await apiClient.post<ITokenResponse>(
        API_ENDPOINTS.authLogin,
        cleanPayload
      );
      return response.data;
    } catch (error: unknown) {
      const msg = extractAuthErrorMessage(
        error,
        'Tên đăng nhập hoặc mật khẩu không chính xác.'
      );
      throw new Error(msg);
    }
  },

  async getMe(token?: string): Promise<IUser> {
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
    const response = await apiClient.get<IUser>(API_ENDPOINTS.authMe, { headers });
    return response.data;
  },
};

