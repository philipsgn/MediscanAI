/**
 * Zustand store cho Authentication State (Stage 8).
 * Quản lý user session, tokens, đồng bộ localStorage & Cookies (phục vụ Next.js Middleware).
 */

import { create } from 'zustand';
import { IUser, ILoginRequest, IRegisterRequest } from '@/types/auth';
import { authService } from '@/services/authService';

const TOKEN_KEY = 'mediscan_access_token';
const USER_KEY = 'mediscan_auth_user';
const COOKIE_KEY = 'mediscan_auth_token';

interface AuthState {
  user: IUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isHydrated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (credentials: ILoginRequest) => Promise<void>;
  register: (data: IRegisterRequest) => Promise<void>;
  logout: () => void;
  hydrateFromStorage: () => Promise<void>;
  clearError: () => void;
}

function setAuthCookie(token: string) {
  if (typeof document === 'undefined') return;
  const expires = new Date(Date.now() + 7 * 86400000).toUTCString();
  document.cookie = `${COOKIE_KEY}=${encodeURIComponent(token)}; expires=${expires}; path=/; SameSite=Lax`;
}

function removeAuthCookie() {
  if (typeof document === 'undefined') return;
  document.cookie = `${COOKIE_KEY}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isHydrated: false,
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),

  login: async (credentials: ILoginRequest) => {
    set({ isLoading: true, error: null });
    try {
      const res = await authService.login(credentials);
      const { accessToken, user } = res;

      if (typeof window !== 'undefined') {
        localStorage.setItem(TOKEN_KEY, accessToken);
        localStorage.setItem(USER_KEY, JSON.stringify(user));
        setAuthCookie(accessToken);
      }

      set({
        user,
        accessToken,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (err: unknown) {
      const errorMsg =
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
        'Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.';
      set({ error: errorMsg, isLoading: false });
      throw new Error(errorMsg);
    }
  },

  register: async (data: IRegisterRequest) => {
    set({ isLoading: true, error: null });
    try {
      const res = await authService.register(data);
      const { accessToken, user } = res;

      if (typeof window !== 'undefined') {
        localStorage.setItem(TOKEN_KEY, accessToken);
        localStorage.setItem(USER_KEY, JSON.stringify(user));
        setAuthCookie(accessToken);
      }

      set({
        user,
        accessToken,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (err: unknown) {
      const errorMsg =
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
        'Đăng ký thất bại. Vui lòng kiểm tra thông tin nhập vào.';
      set({ error: errorMsg, isLoading: false });
      throw new Error(errorMsg);
    }
  },

  logout: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      removeAuthCookie();
    }
    set({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      error: null,
    });
  },

  hydrateFromStorage: async () => {
    if (get().isHydrated || typeof window === 'undefined') return;

    const storedToken = localStorage.getItem(TOKEN_KEY);
    const storedUserRaw = localStorage.getItem(USER_KEY);

    if (!storedToken) {
      set({ isHydrated: true, isAuthenticated: false });
      return;
    }

    try {
      let storedUser: IUser | null = null;
      if (storedUserRaw) {
        storedUser = JSON.parse(storedUserRaw);
      }

      // Đã có token, thử gọi /auth/me để kiểm tra token còn sống không
      const me = await authService.getMe(storedToken);

      localStorage.setItem(USER_KEY, JSON.stringify(me));
      setAuthCookie(storedToken);

      set({
        user: me,
        accessToken: storedToken,
        isAuthenticated: true,
        isHydrated: true,
      });
    } catch {
      // Token hết hạn hoặc không hợp lệ -> xóa kho lưu trữ
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      removeAuthCookie();

      set({
        user: null,
        accessToken: null,
        isAuthenticated: false,
        isHydrated: true,
      });
    }
  },
}));
