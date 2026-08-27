/**
 * Profile Service — Gọi REST APIs cho /profile/me và /profile.
 * Tuân thủ AGENTS.md §3.D.3: tập trung mọi API calls trong src/services/.
 */

import { apiClient, API_ENDPOINTS } from './api';
import { IUserProfile } from '@/types/medication';

export const profileService = {
  async getProfile(): Promise<IUserProfile> {
    const response = await apiClient.get<IUserProfile>(API_ENDPOINTS.profileMe);
    return response.data;
  },

  async upsertProfile(payload: IUserProfile): Promise<IUserProfile> {
    const response = await apiClient.post<IUserProfile>(
      API_ENDPOINTS.profileUpsert,
      payload
    );
    return response.data;
  },
};
