/**
 * Zustand store cho Scan History, Medication Reminders & Treatment Adherence (Stage 10).
 * Quản lý bộ nhớ tạm client-side; Backend REST APIs là Single Source of Truth.
 */

import { create } from 'zustand';
import {
  IScanHistoryItem,
  IReminderItem,
  IReminderCreate,
  IReminderUpdate,
  IAdherenceStats,
  IUserMedication,
  IUserMedicationCreate,
  IUserMedicationUpdate,
} from '@/types/history_reminder';
import { historyReminderService } from '@/services/historyReminderService';

interface HistoryReminderState {
  histories: IScanHistoryItem[];
  totalHistories: number;
  reminders: IReminderItem[];
  totalReminders: number;
  stats: IAdherenceStats;
  medications: IUserMedication[];
  totalMedications: number;

  isLoadingHistories: boolean;
  isLoadingReminders: boolean;
  isLoadingMedications: boolean;
  error: string | null;

  fetchHistories: (params?: { limit?: number; offset?: number; severity?: string }) => Promise<void>;
  deleteHistory: (id: string) => Promise<void>;

  fetchReminders: (params?: { limit?: number; offset?: number; activeOnly?: boolean }) => Promise<void>;
  createReminder: (payload: IReminderCreate) => Promise<IReminderItem>;
  updateReminder: (id: string, payload: IReminderUpdate) => Promise<void>;
  deleteReminder: (id: string) => Promise<void>;
  logReminderStatus: (id: string, status: 'taken' | 'skipped', notes?: string) => Promise<void>;

  fetchMedications: (params?: { limit?: number; offset?: number; activeOnly?: boolean }) => Promise<void>;
  createMedication: (payload: IUserMedicationCreate) => Promise<IUserMedication>;
  updateMedication: (id: string, payload: IUserMedicationUpdate) => Promise<void>;
  deleteMedication: (id: string) => Promise<void>;

  clearStore: () => void;
}

const initialStats: IAdherenceStats = {
  totalReminders: 0,
  todayTakenCount: 0,
  todaySkippedCount: 0,
  todayTotalScheduled: 0,
  todayAdherenceRate: 0,
  takenCount: 0,
  skippedCount: 0,
  adherenceRate: 0,
};

export const useHistoryReminderStore = create<HistoryReminderState>((set, get) => ({
  histories: [],
  totalHistories: 0,
  reminders: [],
  totalReminders: 0,
  stats: initialStats,
  medications: [],
  totalMedications: 0,

  isLoadingHistories: false,
  isLoadingReminders: false,
  isLoadingMedications: false,
  error: null,

  fetchHistories: async (params) => {
    set({ isLoadingHistories: true, error: null });
    try {
      const res = await historyReminderService.getHistories(params);
      set({
        histories: res.items,
        totalHistories: res.total,
        isLoadingHistories: false,
      });
    } catch (err) {
      set({ isLoadingHistories: false, error: 'Không thể tải lịch sử đánh giá.' });
    }
  },

  deleteHistory: async (id: string) => {
    try {
      await historyReminderService.deleteHistory(id);
      set((state) => ({
        histories: state.histories.filter((h) => h.id !== id),
        totalHistories: Math.max(0, state.totalHistories - 1),
      }));
    } catch (err) {
      console.warn('Lỗi khi xóa lịch sử:', err);
      throw err;
    }
  },

  fetchReminders: async (params) => {
    set({ isLoadingReminders: true, error: null });
    try {
      const res = await historyReminderService.getRemindersOverview(params);
      set({
        reminders: res.items,
        totalReminders: res.total,
        stats: res.stats || initialStats,
        isLoadingReminders: false,
      });
    } catch {
      set({ isLoadingReminders: false, error: 'Không thể tải danh sách nhắc nhở.' });
    }
  },

  createReminder: async (payload: IReminderCreate) => {
    set({ isLoadingReminders: true });
    try {
      const created = await historyReminderService.createReminder(payload);
      await get().fetchReminders();
      return created;
    } catch (err: unknown) {
      set({ isLoadingReminders: false });
      throw err;
    }
  },

  updateReminder: async (id: string, payload: IReminderUpdate) => {
    try {
      await historyReminderService.updateReminder(id, payload);
      await get().fetchReminders();
    } catch (err: unknown) {
      console.warn('Lỗi khi cập nhật nhắc nhở:', err);
      throw err;
    }
  },

  deleteReminder: async (id: string) => {
    try {
      await historyReminderService.deleteReminder(id);
      await get().fetchReminders();
    } catch (err: unknown) {
      console.warn('Lỗi khi xóa nhắc nhở:', err);
      throw err;
    }
  },

  logReminderStatus: async (id: string, status: 'taken' | 'skipped', notes?: string) => {
    try {
      await historyReminderService.logReminderStatus(id, { status, notes });
      await get().fetchReminders();
    } catch (err: unknown) {
      console.warn('Lỗi khi ghi nhật ký uống thuốc:', err);
      throw err;
    }
  },

  fetchMedications: async (params) => {
    set({ isLoadingMedications: true, error: null });
    try {
      const res = await historyReminderService.getMedications(params);
      set({
        medications: res.items,
        totalMedications: res.total,
        isLoadingMedications: false,
      });
    } catch {
      set({ isLoadingMedications: false, error: 'Không thể tải danh sách thuốc trong tủ.' });
    }
  },

  createMedication: async (payload: IUserMedicationCreate) => {
    set({ isLoadingMedications: true });
    try {
      const created = await historyReminderService.createMedication(payload);
      await get().fetchMedications();
      return created;
    } catch (err: unknown) {
      set({ isLoadingMedications: false });
      throw err;
    }
  },

  updateMedication: async (id: string, payload: IUserMedicationUpdate) => {
    try {
      await historyReminderService.updateMedication(id, payload);
      await get().fetchMedications();
    } catch (err: unknown) {
      console.warn('Lỗi khi cập nhật thuốc:', err);
      throw err;
    }
  },

  deleteMedication: async (id: string) => {
    try {
      await historyReminderService.deleteMedication(id);
      await get().fetchMedications();
      await get().fetchReminders();
    } catch (err: unknown) {
      console.warn('Lỗi khi xóa thuốc:', err);
      throw err;
    }
  },

  clearStore: () => {
    set({
      histories: [],
      totalHistories: 0,
      reminders: [],
      totalReminders: 0,
      stats: initialStats,
      medications: [],
      totalMedications: 0,
      isLoadingHistories: false,
      isLoadingReminders: false,
      isLoadingMedications: false,
      error: null,
    });
  },
}));
