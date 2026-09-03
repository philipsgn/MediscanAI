/**
 * Zustand store cho UserProfile — Quản lý Hồ sơ Y tế Cá nhân hóa (Stage 9).
 * Backend REST API (/api/v1/profile/me) là Single Source of Truth.
 * Dữ liệu lưu trong Zustand memory, tự động dọn sạch khi Logout.
 */

import { create } from 'zustand';
import { IUserProfile } from '@/types/medication';
import { profileService } from '@/services/profileService';
import { useAuthStore } from '@/store/authStore';

const LEGACY_STORAGE_KEY = 'mediscan_user_profile';

interface UserProfileState {
  profile: IUserProfile | null;
  isLoading: boolean;
  error: string | null;

  /** Lưu/Cập nhật profile lên backend API */
  setProfile: (p: IUserProfile) => Promise<IUserProfile>;
  /** Truy xuất profile từ Backend API */
  fetchProfile: () => Promise<IUserProfile | null>;
  /** Xóa profile khỏi Zustand memory và localStorage */
  clearProfile: () => void;
  /** Xóa thông báo lỗi */
  clearError: () => void;
}

export const useUserProfileStore = create<UserProfileState>((set) => ({
  profile: null,
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),

  setProfile: async (p: IUserProfile): Promise<IUserProfile> => {
    set({ isLoading: true, error: null });
    try {
      const saved = await profileService.upsertProfile(p);
      set({ profile: saved, isLoading: false, error: null });
      return saved;
    } catch (err: unknown) {
      const errorMsg =
        err instanceof Error
          ? err.message
          : 'Lưu hồ sơ y tế không thành công. Vui lòng thử lại.';
      set({ isLoading: false, error: errorMsg });
      throw new Error(errorMsg);
    }
  },

  fetchProfile: async (): Promise<IUserProfile | null> => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('mediscan_access_token') : null;
    if (!token) {
      set({ profile: null, isLoading: false });
      return null;
    }

    set({ isLoading: true, error: null });
    try {
      const serverProfile = await profileService.getProfile();
      set({ profile: serverProfile, isLoading: false, error: null });
      return serverProfile;
    } catch {
      // 404 (Chưa khai báo profile) hoặc lỗi token -> reset memory
      set({ profile: null, isLoading: false });
      return null;
    }
  },

  clearProfile: () => {
    set({ profile: null, error: null, isLoading: false });
    if (typeof window !== 'undefined') {
      localStorage.removeItem(LEGACY_STORAGE_KEY);
    }
  },
}));

/** Utility: kiểm tra nhanh user đã hoàn tất onboarding chưa dựa trên JWT User state. */
export function isOnboardingComplete(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const authUser = useAuthStore.getState().user;
    if (authUser && authUser.isProfileCompleted === true) {
      return true;
    }
    const rawUser = localStorage.getItem('mediscan_auth_user');
    if (rawUser) {
      const user = JSON.parse(rawUser);
      if (user && user.isProfileCompleted === true) {
        return true;
      }
    }
  } catch {
    // fallback
  }
  return useUserProfileStore.getState().profile !== null;
}

