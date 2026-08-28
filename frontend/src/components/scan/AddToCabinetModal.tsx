'use client';

import React, { useState, useEffect } from 'react';
import { IExtractedDrugItem, IDrugItem } from '@/types/medication';
import {
  Pill, Clock, Calendar, Check, X, ShieldAlert,
  CheckCircle2, Sparkles, Sun, Sunset, Moon, Coffee, AlertCircle
} from 'lucide-react';

interface AddToCabinetModalProps {
  isOpen: boolean;
  rawDrugs: IDrugItem[];
  sourceStream: 'prescription' | 'packaging';
  onClose: () => void;
  onOnlySaveHistory: () => void;
  onConfirmAddToCabinetAndReminders: (items: IExtractedDrugItem[]) => Promise<void> | void;
}

const DEFAULT_SLOT_TIMES: Record<string, string> = {
  morning: '08:00',
  noon: '12:00',
  afternoon: '17:00',
  evening: '21:00',
};

const SLOT_LABELS: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  morning: { label: 'Sáng', icon: Coffee, color: 'text-amber-600 bg-amber-50 border-amber-200' },
  noon: { label: 'Trưa', icon: Sun, color: 'text-sky-600 bg-sky-50 border-sky-200' },
  afternoon: { label: 'Chiều', icon: Sunset, color: 'text-orange-600 bg-orange-50 border-orange-200' },
  evening: { label: 'Tối', icon: Moon, color: 'text-indigo-600 bg-indigo-50 border-indigo-200' },
};

function parseTimeSlotsFromInstruction(instruction: string) {
  const text = (instruction || '').toLowerCase();
  const slots: string[] = [];
  const times: Record<string, string> = { ...DEFAULT_SLOT_TIMES };

  if (text.includes('sáng') || text.includes('morning') || text.includes('am')) {
    slots.push('morning');
  }
  if (text.includes('trưa') || text.includes('noon')) {
    slots.push('noon');
  }
  if (text.includes('chiều') || text.includes('afternoon')) {
    slots.push('afternoon');
  }
  if (text.includes('tối') || text.includes('đêm') || text.includes('evening') || text.includes('night') || text.includes('pm')) {
    slots.push('evening');
  }

  const isTimeExtracted = slots.length > 0;
  return { slots, times, isTimeExtracted };
}

export function AddToCabinetModal({
  isOpen,
  rawDrugs,
  sourceStream,
  onClose,
  onOnlySaveHistory,
  onConfirmAddToCabinetAndReminders,
}: AddToCabinetModalProps) {
  const [items, setItems] = useState<IExtractedDrugItem[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (rawDrugs && rawDrugs.length > 0) {
      const today = new Date().toISOString().split('T')[0];
      const initialized: IExtractedDrugItem[] = rawDrugs.map((d) => {
        const { slots, times, isTimeExtracted } = parseTimeSlotsFromInstruction(d.dosageInstruction || '');
        return {
          id: d.drugId || crypto.randomUUID(),
          drugName: d.brandName,
          activeIngredient: d.activeIngredient || d.brandName,
          strength: d.strength || '',
          dosageForm: d.category || 'viên',
          dosageInstruction: d.dosageInstruction || '',
          timeSlots: slots,
          slotTimes: times,
          durationDays: 7,
          startDate: today,
          isTimeExtracted,
          sourceStream,
        };
      });
      setItems(initialized);
    }
  }, [rawDrugs, sourceStream]);

  if (!isOpen) return null;

  const updateItemField = (id: string, field: keyof IExtractedDrugItem, value: any) => {
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, [field]: value } : item))
    );
  };

  const toggleSlot = (id: string, slotKey: string) => {
    setItems((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item;
        const hasSlot = item.timeSlots.includes(slotKey);
        const newSlots = hasSlot
          ? item.timeSlots.filter((s) => s !== slotKey)
          : [...item.timeSlots, slotKey];
        return { ...item, timeSlots: newSlots };
      })
    );
  };

  const updateSlotTime = (id: string, slotKey: string, timeValue: string) => {
    setItems((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item;
        return {
          ...item,
          slotTimes: { ...item.slotTimes, [slotKey]: timeValue },
        };
      })
    );
  };

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      await onConfirmAddToCabinetAndReminders(items);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fade-in font-[var(--font-inter)]">
      <div className="bg-surface rounded-xl border border-outline-variant shadow-layer-1 w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden">
        
        {/* Modal Header */}
        <div className="p-5 border-b border-outline-variant/30 flex items-center justify-between bg-surface-container-low">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary text-on-primary flex items-center justify-center font-bold shrink-0">
              <Pill size={20} />
            </div>
            <div>
              <h2 className="text-base font-bold text-primary">
                Xác nhận & Thiết lập Lịch uống thuốc
              </h2>
              <p className="text-xs text-on-surface-variant mt-0.5">
                Chuẩn hóa thông tin trích xuất, ngày bắt đầu và các khung giờ uống trước khi lưu.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body - Items List */}
        <div className="p-6 overflow-y-auto space-y-6 flex-grow bg-background">
          {items.map((item, idx) => (
            <div
              key={item.id}
              className="bg-surface rounded-xl border border-outline-variant/40 p-5 space-y-4 shadow-sm"
            >
              {/* Item Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-outline-variant/20 pb-3">
                <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-on-surface-variant mb-1">
                      Tên thuốc (#{idx + 1}) <span className="text-error">*</span>
                    </label>
                    <input
                      type="text"
                      value={item.drugName}
                      onChange={(e) => updateItemField(item.id, 'drugName', e.target.value)}
                      className="w-full px-3 py-1.5 bg-white border border-outline-variant rounded-lg text-xs font-bold text-primary outline-none focus:border-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-on-surface-variant mb-1">
                      Hoạt chất gốc / Hàm lượng
                    </label>
                    <input
                      type="text"
                      value={`${item.activeIngredient || ''}${item.strength ? ` (${item.strength})` : ''}`}
                      onChange={(e) => updateItemField(item.id, 'activeIngredient', e.target.value)}
                      className="w-full px-3 py-1.5 bg-white border border-outline-variant rounded-lg text-xs text-on-surface outline-none focus:border-primary"
                    />
                  </div>
                </div>
              </div>

              {/* Start Date & Duration */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-surface-container-low/40 p-3 rounded-lg border border-outline-variant/20">
                <div>
                  <label className="block text-[11px] font-bold text-on-surface-variant mb-1 flex items-center gap-1">
                    <Calendar size={13} className="text-primary" />
                    <span>Ngày bắt đầu uống</span>
                  </label>
                  <input
                    type="date"
                    value={item.startDate || ''}
                    onChange={(e) => updateItemField(item.id, 'startDate', e.target.value)}
                    className="w-full px-3 py-1.5 bg-white border border-outline-variant rounded-lg text-xs text-on-surface outline-none focus:border-primary"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-on-surface-variant mb-1 flex items-center gap-1">
                    <Clock size={13} className="text-primary" />
                    <span>Số ngày uống (đợt điều trị)</span>
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="365"
                    value={item.durationDays || 7}
                    onChange={(e) => updateItemField(item.id, 'durationDays', Number(e.target.value))}
                    className="w-full px-3 py-1.5 bg-white border border-outline-variant rounded-lg text-xs text-on-surface outline-none focus:border-primary"
                  />
                </div>
              </div>

              {/* Time Slots & Fallback Scheduler */}
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-primary flex items-center gap-1.5">
                    <Clock size={14} />
                    <span>Khung giờ uống & Buổi trong ngày</span>
                  </span>
                  {!item.isTimeExtracted && (
                    <span className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full font-semibold flex items-center gap-1">
                      <AlertCircle size={12} />
                      <span>Graceful Fallback — Vui lòng tick chọn giờ</span>
                    </span>
                  )}
                </div>

                {!item.isTimeExtracted && (
                  <p className="text-[11px] text-on-surface-variant italic">
                    * OCR chưa nhận diện đủ giờ uống chi tiết. Vui lòng tick chọn các buổi bác sĩ dặn để cài đặt nhắc nhở tự động.
                  </p>
                )}

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                  {(['morning', 'noon', 'afternoon', 'evening'] as const).map((slotKey) => {
                    const slotInfo = SLOT_LABELS[slotKey];
                    const IconComp = slotInfo.icon;
                    const isChecked = item.timeSlots.includes(slotKey);
                    const currentTime = item.slotTimes[slotKey] || DEFAULT_SLOT_TIMES[slotKey];

                    return (
                      <div
                        key={slotKey}
                        className={`p-2.5 rounded-lg border transition-all space-y-2 ${
                          isChecked
                            ? 'bg-surface-container border-primary shadow-sm'
                            : 'bg-white border-outline-variant/40 opacity-70 hover:opacity-100'
                        }`}
                      >
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => toggleSlot(item.id, slotKey)}
                            className="rounded text-primary focus:ring-primary"
                          />
                          <IconComp size={14} className="text-primary shrink-0" />
                          <span className="text-xs font-bold text-on-surface">{slotInfo.label}</span>
                        </label>

                        {isChecked && (
                          <input
                            type="time"
                            value={currentTime}
                            onChange={(e) => updateSlotTime(item.id, slotKey, e.target.value)}
                            className="w-full px-2 py-1 bg-white border border-outline-variant rounded text-[11px] font-mono text-primary text-center outline-none"
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

            </div>
          ))}
        </div>

        {/* Modal Footer Actions */}
        <div className="p-4 border-t border-outline-variant/30 bg-surface-container-low flex flex-col sm:flex-row items-center justify-between gap-3">
          <button
            type="button"
            onClick={onOnlySaveHistory}
            className="w-full sm:w-auto h-11 px-5 border border-outline-variant bg-white hover:bg-surface-container text-on-surface-variant text-xs font-semibold rounded-lg transition-all shadow-sm"
          >
            Chỉ lưu vào Lịch sử phân tích
          </button>

          <button
            type="button"
            disabled={isSubmitting}
            onClick={handleConfirm}
            className="w-full sm:w-auto h-11 px-6 bg-primary hover:bg-primary-container text-on-primary text-xs font-bold rounded-lg flex items-center justify-center gap-2 transition-all shadow-layer-1 disabled:opacity-50"
          >
            <CheckCircle2 size={16} />
            <span>Xác nhận thêm vào Tủ thuốc & Bật nhắc nhở</span>
          </button>
        </div>

      </div>
    </div>
  );
}
