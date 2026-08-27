'use client';

/**
 * ReminderSchedule — Component Nhắc Nhở Uống Thuốc & Theo Dõi Tuân Thủ Điều Trị (Stage 10).
 * Thẻ nhắc nhở theo 4 khung giờ trong ngày (Sáng, Trưa, Chiều, Tối).
 * Nút đánh dấu "Đã uống" (Taken) / "Bỏ qua" (Skipped), Switch toggle, và Thanh tiến độ Tuân thủ (Adherence Rate %).
 */

import React, { useState, useEffect } from 'react';
import {
  Clock, CheckCircle2, XCircle, Plus, Trash2, Power, Sun, Sunset, Moon, Sunrise,
  TrendingUp, Pill, AlertCircle, Loader2, Sparkles, Check
} from 'lucide-react';
import { useHistoryReminderStore } from '@/store/historyReminderStore';
import { IReminderCreate, IReminderItem } from '@/types/history_reminder';
import { toast } from '@/components/common/Toast';

const TIME_OF_DAY_SLOTS = [
  { key: 'morning', label: 'Buổi Sáng', defaultTime: '08:00', icon: Sunrise, color: 'text-amber-400 border-amber-900/60 bg-amber-950/30' },
  { key: 'noon', label: 'Buổi Trưa', defaultTime: '12:00', icon: Sun, color: 'text-yellow-400 border-yellow-900/60 bg-yellow-950/30' },
  { key: 'afternoon', label: 'Buổi Chiều', defaultTime: '17:00', icon: Sunset, color: 'text-orange-400 border-orange-900/60 bg-orange-950/30' },
  { key: 'evening', label: 'Buổi Tối', defaultTime: '21:00', icon: Moon, color: 'text-sky-400 border-sky-900/60 bg-sky-950/30' },
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

  const getAdherenceBadgeColor = (rate: number) => {
    if (rate >= 80) return 'text-emerald-400 bg-emerald-950/60 border-emerald-700';
    if (rate >= 50) return 'text-amber-400 bg-amber-950/60 border-amber-700';
    return 'text-rose-400 bg-rose-950/60 border-rose-700';
  };

  return (
    <div className="space-y-6">

      {/* ── Treatment Adherence Progress Card ── */}
      <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 shadow-xl backdrop-blur-md space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-teal-950 text-teal-400 border border-teal-800/80">
              <TrendingUp size={22} />
            </div>
            <div>
              <h3 className="text-sm font-extrabold text-white flex items-center gap-2">
                Tiến Độ Tuân Thủ Điều Trị (Treatment Adherence)
              </h3>
              <p className="text-xs text-slate-400">Tỉ lệ dựa trên số lần bạn đánh dấu Đã uống / Bỏ qua</p>
            </div>
          </div>

          <div className={`px-3 py-1.5 rounded-xl border text-xs font-black flex items-center gap-1.5 ${getAdherenceBadgeColor(stats.adherenceRate)}`}>
            <span>{stats.adherenceRate}% Tuân Thủ</span>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="space-y-1.5">
          <div className="w-full h-3 bg-slate-950 rounded-full overflow-hidden p-0.5 border border-slate-800 flex">
            <div
              className="h-full rounded-full bg-gradient-to-r from-teal-500 to-emerald-400 transition-all duration-500"
              style={{ width: `${Math.min(stats.adherenceRate, 100)}%` }}
            />
          </div>
          <div className="flex justify-between text-[11px] text-slate-400 font-semibold px-1">
            <span>Đã uống: <strong className="text-emerald-400">{stats.takenCount}</strong> lần</span>
            <span>Bỏ qua: <strong className="text-rose-400">{stats.skippedCount}</strong> lần</span>
            <span>Tổng nhắc nhở: <strong className="text-white">{stats.totalReminders}</strong></span>
          </div>
        </div>
      </div>

      {/* ── Top Header & Add Button ── */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-extrabold text-white flex items-center gap-2">
            <Clock size={18} className="text-teal-400" />
            Lịch Nhắc Nhở Uống Thuốc Theo Khung Giờ
          </h3>
          <p className="text-xs text-slate-400">Tự động sắp xếp thuốc theo 4 buổi trong ngày</p>
        </div>

        <button
          type="button"
          onClick={() => setShowAddForm(!showAddForm)}
          className="px-3.5 py-2 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white font-bold text-xs shadow-lg shadow-teal-950 flex items-center gap-1.5 transition-all"
        >
          <Plus size={16} />
          <span>Thêm Nhắc Nhở</span>
        </button>
      </div>

      {/* ── Inline Add Form ── */}
      {showAddForm && (
        <form onSubmit={handleAddReminder} className="bg-slate-900/90 rounded-2xl border border-teal-900/60 p-5 shadow-2xl space-y-4 animate-in fade-in duration-200">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="text-xs font-bold text-teal-300 uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles size={14} />
              Tạo Lịch Nhắc Nhở Uống Thuốc Mới
            </span>
            <button type="button" onClick={() => setShowAddForm(false)} className="text-slate-500 hover:text-white">
              <XCircle size={16} />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div>
              <label className="block text-xs font-bold text-slate-300 mb-1">Tên thuốc *</label>
              <input
                type="text"
                value={newDrugName}
                onChange={(e) => setNewDrugName(e.target.value)}
                placeholder="VD: Panadol Extra 500mg"
                className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 outline-none focus:border-teal-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-300 mb-1">Liều dùng (Tùy chọn)</label>
              <input
                type="text"
                value={newDosage}
                onChange={(e) => setNewDosage(e.target.value)}
                placeholder="VD: 1 viên sau khi ăn"
                className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 outline-none focus:border-teal-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-300 mb-1">Buổi trong ngày</label>
              <select
                value={newTimeOfDay}
                onChange={(e) => {
                  const val = e.target.value as typeof newTimeOfDay;
                  setNewTimeOfDay(val);
                  const slot = TIME_OF_DAY_SLOTS.find((s) => s.key === val);
                  if (slot) setNewTime(slot.defaultTime);
                }}
                className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white outline-none focus:border-teal-500 font-semibold"
              >
                <option value="morning">🌅 Buổi Sáng (08:00)</option>
                <option value="noon">☀️ Buổi Trưa (12:00)</option>
                <option value="afternoon">🌇 Buổi Chiều (17:00)</option>
                <option value="evening">🌙 Buổi Tối (21:00)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-300 mb-1">Giờ nhắc nhở cụ thể</label>
              <input
                type="time"
                value={newTime}
                onChange={(e) => setNewTime(e.target.value)}
                className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white outline-none focus:border-teal-500 font-semibold"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="px-4 py-2 rounded-xl bg-slate-950 hover:bg-slate-800 text-slate-300 font-bold text-xs border border-slate-800"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-bold text-xs flex items-center gap-1.5 disabled:opacity-50"
            >
              {isSubmitting ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              <span>Lưu Nhắc Nhở</span>
            </button>
          </div>
        </form>
      )}

      {/* ── 4 Time of Day Slot Columns / Grid ── */}
      {isLoadingReminders ? (
        <div className="p-10 text-center text-xs text-slate-400 flex flex-col items-center gap-2">
          <Loader2 size={24} className="animate-spin text-teal-400" />
          <span>Đang tải danh sách nhắc nhở...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {TIME_OF_DAY_SLOTS.map((slot) => {
            const SlotIcon = slot.icon;
            const slotReminders = reminders.filter((r) => r.timeOfDay === slot.key);

            return (
              <div key={slot.key} className="bg-slate-900/90 rounded-2xl border border-slate-800 p-4 shadow-xl backdrop-blur-md space-y-3">
                {/* Slot Header */}
                <div className={`p-2.5 rounded-xl border flex items-center justify-between ${slot.color}`}>
                  <div className="flex items-center gap-2">
                    <SlotIcon size={18} />
                    <span className="font-extrabold text-xs tracking-tight">{slot.label}</span>
                  </div>
                  <span className="text-[11px] font-mono font-bold opacity-80">Mặc định: {slot.defaultTime}</span>
                </div>

                {/* Reminders List in this Slot */}
                {slotReminders.length === 0 ? (
                  <div className="p-4 text-center text-slate-500 text-xs italic border border-dashed border-slate-800/80 rounded-xl">
                    Chưa có nhắc nhở nào cho {slot.label.toLowerCase()}
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {slotReminders.map((r) => {
                      const latestLog = r.logs && r.logs.length > 0 ? r.logs[0] : null;

                      return (
                        <div
                          key={r.id}
                          className={`p-3.5 rounded-xl border transition-all space-y-2.5 ${
                            r.isActive
                              ? 'bg-slate-950/80 border-slate-800'
                              : 'bg-slate-950/30 border-slate-900 opacity-60'
                          }`}
                        >
                          {/* Card Title Row */}
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <Pill size={15} className="text-teal-400 shrink-0" />
                              <div>
                                <h4 className="text-xs font-bold text-white">{r.drugName}</h4>
                                {r.dosageInstruction && (
                                  <p className="text-[11px] text-slate-400 mt-0.5">{r.dosageInstruction}</p>
                                )}
                              </div>
                            </div>

                            <div className="flex items-center gap-2">
                              {/* Active Switch Toggle */}
                              <button
                                type="button"
                                onClick={() => handleToggleActive(r)}
                                title={r.isActive ? 'Đang bật nhắc nhở' : 'Đang tắt'}
                                className={`p-1.5 rounded-lg border transition-colors ${
                                  r.isActive
                                    ? 'bg-teal-950 text-teal-300 border-teal-800'
                                    : 'bg-slate-900 text-slate-600 border-slate-800'
                                }`}
                              >
                                <Power size={13} />
                              </button>

                              {/* Delete Button */}
                              <button
                                type="button"
                                onClick={() => handleDelete(r.id, r.drugName)}
                                className="p-1.5 rounded-lg bg-slate-900 text-slate-500 hover:text-rose-400 border border-slate-800 transition-colors"
                              >
                                <Trash2 size={13} />
                              </button>
                            </div>
                          </div>

                          {/* Time & Last Status Row */}
                          <div className="flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-900 pt-2">
                            <span className="font-mono font-semibold text-slate-300 flex items-center gap-1">
                              <Clock size={12} className="text-teal-500" />
                              {r.reminderTime}
                            </span>

                            {latestLog && (
                              <span className={`font-semibold px-2 py-0.5 rounded text-[10px] ${
                                latestLog.status === 'taken'
                                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                  : 'bg-rose-950 text-rose-300 border border-rose-800'
                              }`}>
                                Gần nhất: {latestLog.status === 'taken' ? 'Đã uống' : 'Bỏ qua'}
                              </span>
                            )}
                          </div>

                          {/* Action Buttons: Taken / Skipped */}
                          <div className="grid grid-cols-2 gap-2 pt-1">
                            <button
                              type="button"
                              onClick={() => handleLogStatus(r.id, 'taken', r.drugName)}
                              disabled={!r.isActive}
                              className="py-1.5 px-2.5 rounded-lg bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 border border-emerald-800/80 font-bold text-[11px] flex items-center justify-center gap-1.5 transition-all active:scale-95 disabled:opacity-40"
                            >
                              <CheckCircle2 size={13} />
                              <span>Đã uống</span>
                            </button>

                            <button
                              type="button"
                              onClick={() => handleLogStatus(r.id, 'skipped', r.drugName)}
                              disabled={!r.isActive}
                              className="py-1.5 px-2.5 rounded-lg bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-800/80 font-bold text-[11px] flex items-center justify-center gap-1.5 transition-all active:scale-95 disabled:opacity-40"
                            >
                              <XCircle size={13} />
                              <span>Bỏ qua</span>
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
