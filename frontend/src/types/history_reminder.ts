/**
 * TypeScript DTOs cho Medication History & Smart Reminders (Stage 10).
 * Khớp 100% camelCase wire format với Pydantic Schemas Backend.
 */

export interface IScanHistoryCreate {
  sourceType: 'prescription' | 'packaging' | 'manual';
  drugNames: string[];
  highestSeverity: 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE';
  summary?: string;
  rawPayload?: Record<string, unknown>;
}

export interface IScanHistoryItem {
  id: string;
  userId: string;
  scannedAt: string;
  sourceType: 'prescription' | 'packaging' | 'manual';
  drugNames: string[];
  highestSeverity: 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE';
  summary?: string;
  rawPayload?: Record<string, unknown>;
}

export interface IReminderCreate {
  drugName: string;
  dosageInstruction?: string;
  timeOfDay: 'morning' | 'noon' | 'afternoon' | 'evening';
  reminderTime: string;
  isActive?: boolean;
}

export interface IReminderUpdate {
  dosageInstruction?: string;
  timeOfDay?: string;
  reminderTime?: string;
  isActive?: boolean;
}

export interface IReminderLogCreate {
  status: 'taken' | 'skipped';
  notes?: string;
}

export interface IReminderLogItem {
  logId: string;
  status: 'taken' | 'skipped';
  timestamp: string;
  notes?: string;
}

export interface IReminderItem {
  id: string;
  userId: string;
  drugName: string;
  dosageInstruction?: string;
  timeOfDay: 'morning' | 'noon' | 'afternoon' | 'evening';
  reminderTime: string;
  isActive: boolean;
  createdAt: string;
  logs: IReminderLogItem[];
}

export interface IAdherenceStats {
  totalReminders: number;
  takenCount: number;
  skippedCount: number;
  adherenceRate: number;
}

export interface IRemindersOverview {
  reminders: IReminderItem[];
  stats: IAdherenceStats;
}
