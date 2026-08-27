/**
 * Zustand store cho Scan History, Medication Reminders & Treatment Adherence (Stage 10).
 */

import { create } from 'zustand';
import {
  IScanHistoryItem,
  IScanHistoryCreate,
  IReminderItem,
  IReminderCreate,
  IReminderUpdate,
  IAdherenceStats,
} from '@/types/history_reminder';
import { historyReminderService } from '@/services/historyReminderService';

interface HistoryReminderState {
  histories: IScanHistoryItem[];
  reminders: IReminderItem[];
  stats: IAdherenceStats;

  isLoadingHistories: boolean;
  isLoadingReminders: boolean;
  error: string | null;

  fetchHistories: () => Promise<void>;
  saveHistory: (payload: IScanHistoryCreate) => Promise<IScanHistoryItem>;

  fetchReminders: () => Promise<void>;
  createReminder: (payload: IReminderCreate) => Promise<IReminderItem>;
  updateReminder: (id: string, payload: IReminderUpdate) => Promise<void>;
  deleteReminder: (id: string) => Promise<void>;
  logReminderStatus: (id: string, status: 'taken' | 'skipped', notes?: string) => Promise<void>;
}

export const useHistoryReminderStore = create<HistoryReminderState>((set, get) => ({
  histories: [],
  reminders: [],
  stats: {
    totalReminders: 0,
    takenCount: 0,
    skippedCount: 0,
    adherenceRate: 0,
  },

  isLoadingHistories: false,
  isLoadingReminders: false,
  error: null,

  fetchHistories: async () => {
    set({ isLoadingHistories: true, error: null });
    try {
      const items = await historyReminderService.getHistories();
      set({ histories: items, isLoadingHistories: false });
    } catch {
      set({ isLoadingHistories: false });
    }
  },

  saveHistory: async (payload: IScanHistoryCreate) => {
    try {
      const newItem = await historyReminderService.saveHistory(payload);
      set((state) => ({
        histories: [newItem, ...state.histories],
      }));
      return newItem;
    } catch (err: unknown) {
      console.warn('Lỗi khi lưu lịch sử quét:', err);
      throw err;
    }
  },

  fetchReminders: async () => {
    set({ isLoadingReminders: true, error: null });
    try {
      const overview = await historyReminderService.getRemindersOverview();
      set({
        reminders: overview.reminders,
        stats: overview.stats,
        isLoadingReminders: false,
      });
    } catch {
      set({ isLoadingReminders: false });
    }
  },

  createReminder: async (payload: IReminderCreate) => {
    set({ isLoadingReminders: true });
    try {
      const created = await historyReminderService.createReminder(payload);
      await get().fetchReminders(); // Re-fetch to get updated stats
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
      set((state) => ({
        reminders: state.reminders.filter((r) => r.id !== id),
      }));
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
}));
