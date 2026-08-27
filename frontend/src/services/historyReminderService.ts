/**
 * History & Reminder Service — gọi REST APIs cho Lịch sử quét & Nhắc nhở uống thuốc (Stage 10).
 * Tuân thủ AGENTS.md §3.D.3: tập trung mọi API call trong src/services/.
 */

import { apiClient, API_ENDPOINTS } from './api';
import {
  IScanHistoryCreate,
  IScanHistoryItem,
  IReminderCreate,
  IReminderUpdate,
  IReminderLogCreate,
  IReminderItem,
  IRemindersOverview,
} from '@/types/history_reminder';

export const historyReminderService = {
  // ── History API ──
  async getHistories(): Promise<IScanHistoryItem[]> {
    const response = await apiClient.get<IScanHistoryItem[]>(API_ENDPOINTS.historyMe);
    return response.data;
  },

  async saveHistory(payload: IScanHistoryCreate): Promise<IScanHistoryItem> {
    const response = await apiClient.post<IScanHistoryItem>(
      API_ENDPOINTS.historySave,
      payload
    );
    return response.data;
  },

  // ── Reminders API ──
  async getRemindersOverview(): Promise<IRemindersOverview> {
    const response = await apiClient.get<IRemindersOverview>(API_ENDPOINTS.remindersMe);
    return response.data;
  },

  async createReminder(payload: IReminderCreate): Promise<IReminderItem> {
    const response = await apiClient.post<IReminderItem>(
      API_ENDPOINTS.remindersCreate,
      payload
    );
    return response.data;
  },

  async updateReminder(id: string, payload: IReminderUpdate): Promise<IReminderItem> {
    const response = await apiClient.put<IReminderItem>(
      `/reminders/${id}`,
      payload
    );
    return response.data;
  },

  async deleteReminder(id: string): Promise<{ message: string; id: string }> {
    const response = await apiClient.delete<{ message: string; id: string }>(
      `/reminders/${id}`
    );
    return response.data;
  },

  async logReminderStatus(id: string, payload: IReminderLogCreate): Promise<IReminderItem> {
    const response = await apiClient.post<IReminderItem>(
      `/reminders/${id}/log`,
      payload
    );
    return response.data;
  },
};
