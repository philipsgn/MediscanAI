/**
 * TypeScript DTOs cho Medication History, Cabinet & Smart Reminders (Stage 10).
 * Khớp 100% camelCase wire format với Pydantic Schemas Backend.
 */

export interface IPaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

export interface IUserMedication {
  id: string;
  userId: string;
  brandName: string;
  activeIngredient?: string;
  strength?: string;
  dosageInstruction?: string;
  durationDays?: number;
  isActive: boolean;
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

export interface IUserMedicationCreate {
  brandName: string;
  activeIngredient?: string;
  strength?: string;
  dosageInstruction?: string;
  durationDays?: number;
  isActive?: boolean;
  notes?: string;
}

export interface IUserMedicationUpdate {
  brandName?: string;
  activeIngredient?: string;
  strength?: string;
  dosageInstruction?: string;
  durationDays?: number;
  isActive?: boolean;
  notes?: string;
}

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
  medicationId?: string;
  drugName: string;
  dosageInstruction?: string;
  timeOfDay: 'morning' | 'noon' | 'afternoon' | 'evening';
  reminderTime: string;
  isActive?: boolean;
}

export interface IReminderUpdate {
  medicationId?: string;
  drugName?: string;
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
  medicationId?: string;
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
  todayTakenCount: number;
  todaySkippedCount: number;
  todayTotalScheduled: number;
  todayAdherenceRate: number;
  takenCount: number;
  skippedCount: number;
  adherenceRate: number;
}

export interface IRemindersOverview extends IPaginatedResponse<IReminderItem> {
  stats: IAdherenceStats;
}
