/**
 * History & Reminder & Cabinet Service — Kết nối REST APIs (Stage 10).
 * Tuân thủ AGENTS.md §3.D.3: tập trung mọi API calls trong src/services/.
 */

import { apiClient, API_ENDPOINTS } from './api';
import {
  IPaginatedResponse,
  IScanHistoryItem,
  IReminderItem,
  IReminderCreate,
  IReminderUpdate,
  IReminderLogCreate,
  IRemindersOverview,
  IUserMedication,
  IUserMedicationCreate,
  IUserMedicationUpdate,
} from '@/types/history_reminder';

export const historyReminderService = {
  // ── History APIs (Read & Delete Only) ──
  async getHistories(params?: {
    limit?: number;
    offset?: number;
    severity?: string;
  }): Promise<IPaginatedResponse<IScanHistoryItem>> {
    const response = await apiClient.get<IPaginatedResponse<IScanHistoryItem>>(
      API_ENDPOINTS.historyMe,
      { params }
    );
    return response.data;
  },

  async getHistoryDetail(historyId: string): Promise<IScanHistoryItem> {
    const response = await apiClient.get<IScanHistoryItem>(
      `${API_ENDPOINTS.historyMe.replace('/me', '')}/${historyId}`
    );
    return response.data;
  },

  async deleteHistory(historyId: string): Promise<{ message: string; id: string }> {
    const response = await apiClient.delete<{ message: string; id: string }>(
      `${API_ENDPOINTS.historyMe.replace('/me', '')}/${historyId}`
    );
    return response.data;
  },

  // ── Reminders APIs ──
  async getRemindersOverview(params?: {
    limit?: number;
    offset?: number;
    activeOnly?: boolean;
  }): Promise<IRemindersOverview> {
    const response = await apiClient.get<IRemindersOverview>(
      API_ENDPOINTS.remindersMe,
      { params }
    );
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
      `${API_ENDPOINTS.remindersCreate}/${id}`,
      payload
    );
    return response.data;
  },

  async deleteReminder(id: string): Promise<{ message: string; id: string }> {
    const response = await apiClient.delete<{ message: string; id: string }>(
      `${API_ENDPOINTS.remindersCreate}/${id}`
    );
    return response.data;
  },

  async logReminderStatus(id: string, payload: IReminderLogCreate): Promise<IReminderItem> {
    const response = await apiClient.post<IReminderItem>(
      `${API_ENDPOINTS.remindersCreate}/${id}/log`,
      payload
    );
    return response.data;
  },

  // ── Cabinet / Medications APIs ──
  async getMedications(params?: {
    limit?: number;
    offset?: number;
    activeOnly?: boolean;
  }): Promise<IPaginatedResponse<IUserMedication>> {
    const response = await apiClient.get<IPaginatedResponse<IUserMedication>>(
      API_ENDPOINTS.medicationsMe,
      { params }
    );
    return response.data;
  },

  async createMedication(payload: IUserMedicationCreate): Promise<IUserMedication> {
    const response = await apiClient.post<IUserMedication>(
      API_ENDPOINTS.medications,
      payload
    );
    return response.data;
  },

  async updateMedication(
    id: string,
    payload: IUserMedicationUpdate
  ): Promise<IUserMedication> {
    const response = await apiClient.put<IUserMedication>(
      `${API_ENDPOINTS.medications}/${id}`,
      payload
    );
    return response.data;
  },

  async deleteMedication(id: string): Promise<{ message: string; id: string }> {
    const response = await apiClient.delete<{ message: string; id: string }>(
      `${API_ENDPOINTS.medications}/${id}`
    );
    return response.data;
  },
};
