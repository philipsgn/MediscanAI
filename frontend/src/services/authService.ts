/**
 * Authentication Service — gọi các REST endpoints /auth/register, /auth/login, /auth/me.
 * Tuân thủ quy tắc kiến trúc tập trung trong src/services/.
 */

import { isAxiosError } from 'axios';
import { apiClient, API_ENDPOINTS } from './api';
import { ILoginRequest, IRegisterRequest, ITokenResponse, IUser } from '@/types/auth';

export const authService = {
  async register(payload: IRegisterRequest): Promise<ITokenResponse> {
    try {
      const cleanPayload = {
        username: payload.username.trim(),
        email: payload.email.trim(),
        password: payload.password,
        fullName: payload.fullName?.trim() || undefined,
      };
      const response = await apiClient.post<ITokenResponse>(
        API_ENDPOINTS.authRegister,
        cleanPayload
      );
      return response.data;
    } catch (error: unknown) {
      if (isAxiosError(error)) {
        console.error('Register API Error:', error.response?.data);
        const detail = error.response?.data?.detail;
        const msg =
          typeof detail === 'string'
            ? detail
            : Array.isArray(detail)
            ? detail.map((d: { msg?: string }) => d.msg || 'Lỗi dữ liệu').join(', ')
            : 'Đăng ký không thành công. Vui lòng kiểm tra lại thông tin.';
        throw new Error(msg);
      }
      throw error;
    }
  },

  async login(payload: ILoginRequest): Promise<ITokenResponse> {
    try {
      const cleanPayload = {
        usernameOrEmail: payload.usernameOrEmail.trim(),
        password: payload.password,
      };
      const response = await apiClient.post<ITokenResponse>(
        API_ENDPOINTS.authLogin,
        cleanPayload
      );
      return response.data;
    } catch (error: unknown) {
      if (isAxiosError(error)) {
        console.error('Login API Error:', error.response?.data);
        const detail = error.response?.data?.detail;
        const msg =
          typeof detail === 'string'
            ? detail
            : 'Tên đăng nhập hoặc mật khẩu không chính xác.';
        throw new Error(msg);
      }
      throw error;
    }
  },

  async getMe(token?: string): Promise<IUser> {
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
    const response = await apiClient.get<IUser>(API_ENDPOINTS.authMe, { headers });
    return response.data;
  },
};
