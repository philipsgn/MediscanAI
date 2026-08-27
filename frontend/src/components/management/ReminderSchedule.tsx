'use client';

/**
 * ReminderSchedule — Nhắc Nhở Uống Thuốc & Theo Dõi Tuân Thủ (Minimalist Clinical Grade).
 * Border 1px slate-200, Nền trắng/xám, rounded-none / rounded-sm.
 * Khung giờ 4 buổi trong ngày, Nút đánh dấu Đã uống / Bỏ qua & Chỉ số Tuân thủ điều trị %.
 */

import React, { useState, useEffect } from 'react';
import {
  Clock, CheckCircle2, XCircle, Plus, Trash2, Power, Sun, Sunset, Moon, Sunrise,
  TrendingUp, Pill, Loader2, Check, X
} from 'lucide-react';
import { useHistoryReminderStore } from '@/store/historyReminderStore';
import { IReminderCreate, IReminderItem } from '@/types/history_reminder';
import { toast } from '@/components/common/Toast';

const TIME_OF_DAY_SLOTS = [
  { key: 'morning', label: 'BUỔI SÁNG', defaultTime: '08:00', icon: Sunrise },
  { key: 'noon', label: 'BUỔI TRƯA', defaultTime: '12:00', icon: Sun },
  { key: 'afternoon', label: 'BUỔI CHIỀU', defaultTime: '17:00', icon: Sunset },
  { key: 'evening', label: 'BUỔI TỐI', defaultTime: '21:00', icon: Moon },
] as const;

export function ReminderSchedule() {
  const {
    reminders,
    stats,
    fetchReminders,
    createReminder,
    updateReminder,
    deleteReminder,
    logReminderStatus,
    isLoadingReminders,
  } = useHistoryReminderStore();

  const [showAddForm, setShowAddForm] = useState(false);
  const [newDrugName, setNewDrugName] = useState('');
  const [newDosage, setNewDosage] = useState('');
  const [newTimeOfDay, setNewTimeOfDay] = useState<'morning' | 'noon' | 'afternoon' | 'evening'>('morning');
  const [newTime, setNewTime] = useState('08:00');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchReminders();
  }, [fetchReminders]);

  const handleAddReminder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDrugName.trim()) {
      toast.error('Vui lòng nhập tên thuốc');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: IReminderCreate = {
        drugName: newDrugName.trim(),
        dosageInstruction: newDosage.trim() || undefined,
        timeOfDay: newTimeOfDay,
        reminderTime: newTime || '08:00',
        isActive: true,
      };
      await createReminder(payload);
      toast.success('Đã tạo lịch nhắc uống thuốc thành công!');
      setNewDrugName('');
      setNewDosage('');
      setShowAddForm(false);
    } catch {
      toast.error('Không thể tạo nhắc nhở. Vui lòng thử lại.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleActive = async (item: IReminderItem) => {
    try {
      await updateReminder(item.id, { isActive: !item.isActive });
      toast.success(`Đã ${!item.isActive ? 'bật' : 'tắt'} nhắc nhở cho ${item.drugName}`);
    } catch {
      toast.error('Lỗi khi thay đổi trạng thái.');
    }
  };

  const handleDelete = async (id: string, name: string) => {
    try {
      await deleteReminder(id);
      toast.success(`Đã xóa nhắc nhở cho ${name}`);
    } catch {
      toast.error('Không thể xóa nhắc nhở.');
    }
  };

  const handleLogStatus = async (id: string, status: 'taken' | 'skipped', drugName: string) => {
    try {
      await logReminderStatus(id, status);
      if (status === 'taken') {
        toast.success(`Đã ghi nhận: Đã uống ${drugName}!`);
      } else {
        toast.info(`Đã ghi nhận: Bỏ qua ${drugName}.`);
      }
    } catch {
      toast.error('Có lỗi xảy ra.');
    }
  };

  return (
    <div className="space-y-4">

      {/* ── Treatment Adherence Metric Bar ── */}
      <div className="bg-white border border-slate-200 p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
          <div className="flex items-center gap-2 text-xs font-mono font-bold text-slate-900 uppercase">
            <TrendingUp size={15} className="text-slate-700" />
            <span>CHỈ SỐ TUÂN THỦ ĐIỀU TRỊ (TREATMENT ADHERENCE RATE)</span>
          </div>

          <div className="px-2.5 py-0.5 border border-slate-900 bg-slate-900 text-white text-xs font-mono font-bold">
            {stats.adherenceRate}% TUÂN THỦ
          </div>
        </div>

        {/* Progress bar */}
        <div className="space-y-1.5 font-mono text-xs">
          <div className="w-full h-2 bg-slate-100 border border-slate-200">
            <div
              className="h-full bg-slate-900 transition-all duration-300"
              style={{ width: `${Math.min(stats.adherenceRate, 100)}%` }}
            />
          </div>
          <div className="flex justify-between text-[11px] text-slate-600">
            <span>Đã uống: <strong className="text-slate-900">{stats.takenCount}</strong> lần</span>
            <span>Bỏ qua: <strong className="text-slate-900">{stats.skippedCount}</strong> lần</span>
            <span>Tổng số lịch: <strong className="text-slate-900">{stats.totalReminders}</strong></span>
          </div>
        </div>
      </div>

      {/* ── Top Header & Add Button ── */}
      <div className="flex items-center justify-between pt-1">
        <div className="text-xs font-mono font-bold text-slate-900 uppercase">
          LỊCH UỐNG THEO 4 KHUNG GIỜ LÂM SÀNG
        </div>

        <button
          type="button"
          onClick={() => setShowAddForm(!showAddForm)}
          className="h-8 px-3 bg-slate-900 hover:bg-slate-800 text-white font-mono font-bold text-xs flex items-center gap-1.5 transition-colors"
        >
          <Plus size={14} />
          <span>THÊM NHẮC NHỞ</span>
        </button>
      </div>

      {/* ── Inline Add Form ── */}
      {showAddForm && (
        <form onSubmit={handleAddReminder} className="bg-white border border-slate-300 p-4 space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-slate-200 pb-2">
            <span className="font-bold text-slate-900 uppercase">KHỞI TẠO LỊCH UỐNG THUỐC MỚI</span>
            <button type="button" onClick={() => setShowAddForm(false)} className="text-slate-400 hover:text-slate-900">
              <X size={15} />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block font-bold text-slate-700 uppercase mb-1">Tên thuốc *</label>
              <input
                type="text"
                value={newDrugName}
                onChange={(e) => setNewDrugName(e.target.value)}
                placeholder="VD: Amlodipine 5mg"
                className="w-full px-3 py-1.5 bg-slate-50 border border-slate-300 text-slate-900 outline-none focus:border-slate-900"
              />
            </div>

            <div>
              <label className="block font-bold text-slate-700 uppercase mb-1">Liều dùng (Tùy chọn)</label>
              <input
                type="text"
                value={newDosage}
                onChange={(e) => setNewDosage(e.target.value)}
                placeholder="VD: 1 viên sau ăn sáng"
                className="w-full px-3 py-1.5 bg-slate-50 border border-slate-300 text-slate-900 outline-none focus:border-slate-900"
              />
            </div>

            <div>
              <label className="block font-bold text-slate-700 uppercase mb-1">Buổi trong ngày</label>
              <select
                value={newTimeOfDay}
                onChange={(e) => {
                  const val = e.target.value as typeof newTimeOfDay;
                  setNewTimeOfDay(val);
                  const slot = TIME_OF_DAY_SLOTS.find((s) => s.key === val);
                  if (slot) setNewTime(slot.defaultTime);
                }}
                className="w-full px-3 py-1.5 bg-slate-50 border border-slate-300 text-slate-900 outline-none focus:border-slate-900 font-mono"
              >
                <option value="morning">Buổi Sáng (08:00)</option>
                <option value="noon">Buổi Trưa (12:00)</option>
                <option value="afternoon">Buổi Chiều (17:00)</option>
                <option value="evening">Buổi Tối (21:00)</option>
              </select>
            </div>

            <div>
              <label className="block font-bold text-slate-700 uppercase mb-1">Giờ nhắc nhở</label>
              <input
                type="time"
                value={newTime}
                onChange={(e) => setNewTime(e.target.value)}
                className="w-full px-3 py-1.5 bg-slate-50 border border-slate-300 text-slate-900 outline-none focus:border-slate-900 font-mono"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="px-3 py-1.5 border border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-700 font-bold"
            >
              HỦY
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-bold flex items-center gap-1.5"
            >
              {isSubmitting ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
              <span>LƯU LỊCH UỐNG</span>
            </button>
          </div>
        </form>
      )}

      {/* ── 4 Slot Grid ── */}
      {isLoadingReminders ? (
        <div className="p-8 text-center text-slate-500 text-xs font-mono flex items-center justify-center gap-2 border border-slate-200 bg-white">
          <Loader2 size={16} className="animate-spin text-slate-700" />
          <span>ĐANG TẢI LỊCH NHẮC NHỞ...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {TIME_OF_DAY_SLOTS.map((slot) => {
            const SlotIcon = slot.icon;
            const slotReminders = reminders.filter((r) => r.timeOfDay === slot.key);

            return (
              <div key={slot.key} className="bg-white border border-slate-200 p-3.5 space-y-2.5">
                {/* Header */}
                <div className="p-2 border border-slate-200 bg-slate-50 flex items-center justify-between font-mono text-xs">
                  <div className="flex items-center gap-1.5 font-bold text-slate-900">
                    <SlotIcon size={14} className="text-slate-700" />
                    <span>{slot.label}</span>
                  </div>
                  <span className="text-[10px] text-slate-500 font-bold">Mặc định: {slot.defaultTime}</span>
                </div>

                {/* Items */}
                {slotReminders.length === 0 ? (
                  <div className="p-3 text-center text-slate-400 font-mono text-[11px] border border-dashed border-slate-200">
                    Chưa có thuốc trong khung giờ này
                  </div>
                ) : (
                  <div className="space-y-2">
                    {slotReminders.map((r) => {
                      const latestLog = r.logs && r.logs.length > 0 ? r.logs[0] : null;

                      return (
                        <div
                          key={r.id}
                          className={`p-2.5 border font-mono text-xs space-y-2 ${
                            r.isActive ? 'bg-white border-slate-300' : 'bg-slate-50 border-slate-200 opacity-60'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center gap-1.5">
                              <Pill size={13} className="text-slate-600 shrink-0" />
                              <div>
                                <span className="font-bold text-slate-900 block">{r.drugName}</span>
                                {r.dosageInstruction && (
                                  <span className="text-[11px] text-slate-500 block">{r.dosageInstruction}</span>
                                )}
                              </div>
                            </div>

                            <div className="flex items-center gap-1">
                              <button
                                type="button"
                                onClick={() => handleToggleActive(r)}
                                title={r.isActive ? 'Bật' : 'Tắt'}
                                className={`p-1 border text-xs ${
                                  r.isActive
                                    ? 'bg-slate-900 text-white border-slate-900'
                                    : 'bg-slate-100 text-slate-400 border-slate-200'
                                }`}
                              >
                                <Power size={11} />
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDelete(r.id, r.drugName)}
                                className="p-1 border border-slate-200 bg-slate-50 text-slate-400 hover:text-rose-600 hover:border-rose-300"
                              >
                                <Trash2 size={11} />
                              </button>
                            </div>
                          </div>

                          <div className="flex items-center justify-between text-[10px] text-slate-500 border-t border-slate-100 pt-1.5">
                            <span className="flex items-center gap-1 font-bold text-slate-700">
                              <Clock size={10} />
                              {r.reminderTime}
                            </span>

                            {latestLog && (
                              <span className={`px-1.5 py-0.2 border font-bold ${
                                latestLog.status === 'taken'
                                  ? 'text-emerald-800 bg-emerald-50 border-emerald-300'
                                  : 'text-rose-800 bg-rose-50 border-rose-300'
                              }`}>
                                {latestLog.status === 'taken' ? 'Đã uống' : 'Bỏ qua'}
                              </span>
                            )}
                          </div>

                          <div className="grid grid-cols-2 gap-1.5 pt-0.5">
                            <button
                              type="button"
                              onClick={() => handleLogStatus(r.id, 'taken', r.drugName)}
                              disabled={!r.isActive}
                              className="py-1 px-2 border border-slate-900 bg-slate-900 hover:bg-slate-800 text-white font-bold text-[10px] flex items-center justify-center gap-1 disabled:opacity-40"
                            >
                              <CheckCircle2 size={11} />
                              <span>ĐÃ UỐNG</span>
                            </button>

                            <button
                              type="button"
                              onClick={() => handleLogStatus(r.id, 'skipped', r.drugName)}
                              disabled={!r.isActive}
                              className="py-1 px-2 border border-slate-300 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-[10px] flex items-center justify-center gap-1 disabled:opacity-40"
                            >
                              <XCircle size={11} />
                              <span>BỎ QUA</span>
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
