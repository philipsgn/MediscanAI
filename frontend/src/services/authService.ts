/**
 * Authentication Service — gọi các REST endpoints /auth/register, /auth/login, /auth/me.
 * Tuân thủ quy tắc kiến trúc tập trung trong src/services/.
 */

import { apiClient, API_ENDPOINTS } from './api';
import { ILoginRequest, IRegisterRequest, ITokenResponse, IUser } from '@/types/auth';

export const authService = {
  async register(payload: IRegisterRequest): Promise<ITokenResponse> {
    const response = await apiClient.post<ITokenResponse>(
      API_ENDPOINTS.authRegister,
      payload
    );
    return response.data;
  },

  async login(payload: ILoginRequest): Promise<ITokenResponse> {
    const response = await apiClient.post<ITokenResponse>(
      API_ENDPOINTS.authLogin,
      payload
    );
    return response.data;
  },

  async getMe(token?: string): Promise<IUser> {
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
    const response = await apiClient.get<IUser>(API_ENDPOINTS.authMe, { headers });
    return response.data;
  },
};
