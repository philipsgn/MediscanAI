/**
 * Zustand store cho UserProfile — dữ liệu local-only (không round-trip API).
 *
 * Persist thủ công vào localStorage key `mediscan_user_profile`,
 * đúng convention với MedicalDisclaimerModal (key `mediscan_disclaimer_accepted`).
 * Pattern: create<T>() Zustand, giống cabinetStore.ts.
 */
import { create } from 'zustand';
import { IUserProfile } from '@/types/medication';

const STORAGE_KEY = 'mediscan_user_profile';

interface UserProfileState {
  profile: IUserProfile | null;
  /** Lưu profile vào store + localStorage */
  setProfile: (p: IUserProfile) => void;
  /** Xóa profile khỏi store + localStorage */
  clearProfile: () => void;
  /** Đọc từ localStorage vào store (gọi 1 lần khi mount) */
  hydrateFromStorage: () => void;
}

/**
 * Kiểm tra xem một object parsed từ JSON có phải UserProfile hợp lệ không.
 * "Hợp lệ" = có `age` là number > 0.
 */
function isValidProfile(obj: unknown): obj is IUserProfile {
  if (typeof obj !== 'object' || obj === null) return false;
  const record = obj as Record<string, unknown>;
  return typeof record.age === 'number' && record.age > 0;
}

/**
 * Đọc profile từ localStorage — trả null nếu không tồn tại hoặc invalid.
 */
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

export const useUserProfileStore = create<UserProfileState>((set) => ({
  profile: null,

  setProfile: (p: IUserProfile) => {
    set({ profile: p });
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(p));
    }
  },

  clearProfile: () => {
    set({ profile: null });
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

/** Utility: kiểm tra nhanh user đã hoàn tất onboarding chưa (đọc localStorage trực tiếp). */
export function isOnboardingComplete(): boolean {
  return readProfileFromStorage() !== null;
}
