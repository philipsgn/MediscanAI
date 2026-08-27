/**
 * Zustand store cho UserProfile — Quản lý Hồ sơ Y tế Cá nhân hóa (Stage 9).
 * Đồng bộ với Backend API (/api/v1/profile) khi người dùng đã xác thực,
 * đồng thời duy trì fallback localStorage khi offline hoặc chưa đăng nhập.
 */

import { create } from 'zustand';
import { IUserProfile } from '@/types/medication';
import { profileService } from '@/services/profileService';

const STORAGE_KEY = 'mediscan_user_profile';

interface UserProfileState {
  profile: IUserProfile | null;
  isLoading: boolean;
  error: string | null;

  /** Lưu/Cập nhật profile vào backend API (nếu đã login) + localStorage */
  setProfile: (p: IUserProfile) => Promise<void>;
  /** Truy xuất profile từ Backend API */
  fetchProfile: () => Promise<void>;
  /** Xóa profile khỏi store + localStorage */
  clearProfile: () => void;
  /** Đọc từ localStorage vào store (dùng làm fallback) */
  hydrateFromStorage: () => void;
}

function isValidProfile(obj: unknown): obj is IUserProfile {
  if (typeof obj !== 'object' || obj === null) return false;
  const record = obj as Record<string, unknown>;
  return typeof record.age === 'number' && record.age > 0;
}

function readProfileFromStorage(): IUserProfile | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    return isValidProfile(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export const useUserProfileStore = create<UserProfileState>((set, get) => ({
  profile: null,
  isLoading: false,
  error: null,

  setProfile: async (p: IUserProfile) => {
    set({ isLoading: true, error: null });

    // Lưu vào localStorage trước để giữ trải nghiệm mượt mà
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(p));
    }
    set({ profile: p });

    // Nếu có JWT token -> lưu lên backend API
    const token = typeof window !== 'undefined' ? localStorage.getItem('mediscan_access_token') : null;
    if (token) {
      try {
        const saved = await profileService.upsertProfile(p);
        set({ profile: saved, isLoading: false });
        if (typeof window !== 'undefined') {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
        }
      } catch (err: unknown) {
        logger_warn("Lưu profile lên backend API không thành công, giữ local fallback", err);
        set({ isLoading: false });
      }
    } else {
      set({ isLoading: false });
    }
  },

  fetchProfile: async () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('mediscan_access_token') : null;
    if (!token) {
      get().hydrateFromStorage();
      return;
    }

    set({ isLoading: true, error: null });
    try {
      const serverProfile = await profileService.getProfile();
      set({ profile: serverProfile, isLoading: false });
      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(serverProfile));
      }
    } catch {
      // Nếu 404 (chưa tạo profile trên backend) -> fallback đọc localStorage
      get().hydrateFromStorage();
      set({ isLoading: false });
    }
  },

  clearProfile: () => {
    set({ profile: null, error: null });
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY);
    }
  },

  hydrateFromStorage: () => {
    const stored = readProfileFromStorage();
    if (stored) {
      set({ profile: stored });
    }
  },
}));

function logger_warn(msg: string, err: unknown) {
  if (process.env.NODE_ENV !== 'production') {
    console.warn(msg, err);
  }
}

/** Utility: kiểm tra nhanh user đã hoàn tất onboarding chưa. */
export function isOnboardingComplete(): boolean {
  return readProfileFromStorage() !== null;
}
