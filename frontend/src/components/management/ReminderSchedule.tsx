'use client';

/**
 * ReminderSchedule — Nhắc Nhở Uống Thuốc & Theo Dõi Tuân Thủ Điều Trị.
 * Hỗ trợ theo dõi Tuân thủ trong ngày (Daily) & Cả quá trình (Overall).
 * Giới hạn ghi nhận 1 lần/ngày/nhắc nhở để chống tăng ảo số lần uống.
 */

import React, { useState, useEffect } from 'react';
import {
  Clock, CheckCircle2, XCircle, Plus, Trash2, Power, Sun, Sunset, Moon, Sunrise,
  TrendingUp, Pill, Loader2, Check, X, CalendarCheck, Award, AlertCircle
} from 'lucide-react';
import { useHistoryReminderStore } from '@/store/historyReminderStore';
import { IReminderCreate, IReminderItem, IReminderLogItem } from '@/types/history_reminder';
import { toast } from '@/components/common/Toast';

const TIME_OF_DAY_SLOTS = [
  { key: 'morning', label: 'Buổi sáng', defaultTime: '08:00', icon: Sunrise, color: 'text-amber-500 bg-amber-50' },
  { key: 'noon', label: 'Buổi trưa', defaultTime: '12:00', icon: Sun, color: 'text-orange-500 bg-orange-50' },
  { key: 'afternoon', label: 'Buổi chiều', defaultTime: '17:00', icon: Sunset, color: 'text-sky-500 bg-sky-50' },
  { key: 'evening', label: 'Buổi tối', defaultTime: '21:00', icon: Moon, color: 'text-indigo-500 bg-indigo-50' },
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

  const getTodayDateString = () => {
    const d = new Date();
    return d.toISOString().split('T')[0];
  };

  const getTodayLog = (logs?: IReminderLogItem[]): IReminderLogItem | null => {
    if (!logs || logs.length === 0) return null;
    const todayStr = getTodayDateString();
    return logs.find((log) => log.timestamp.startsWith(todayStr)) || null;
  };

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
        toast.success(`Đã ghi nhận: Đã uống ${drugName} hôm nay!`);
      } else {
        toast.info(`Đã ghi nhận: Bỏ qua ${drugName} hôm nay.`);
      }
    } catch {
      toast.error('Có lỗi xảy ra.');
    }
  };

  const todayRate = stats.todayAdherenceRate ?? 0;
  const overallRate = stats.adherenceRate ?? 0;
  const todayTaken = stats.todayTakenCount ?? 0;
  const todayScheduled = stats.todayTotalScheduled ?? stats.totalReminders ?? 0;
  const todaySkipped = stats.todaySkippedCount ?? 0;

  return (
    <div className="space-y-6 font-[var(--font-inter)] text-xs">

      {/* ── Dual Treatment Adherence Metric Cards ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Card 1: Tuân thủ trong ngày hôm nay */}
        <div className="bg-white rounded-2xl border border-sky-100 p-5 shadow-sm space-y-3 relative overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <div className="p-1.5 rounded-lg bg-sky-50 text-sky-600">
                <CalendarCheck size={18} />
              </div>
              <div>
                <span>Tuân thủ trong ngày</span>
                <span className="block text-[11px] font-normal text-slate-400">Tiến độ cữ thuốc hôm nay</span>
              </div>
            </div>

            <div className={`px-3 py-1 rounded-full text-xs font-bold border ${
              todayRate >= 80
                ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                : todayRate >= 50
                ? 'bg-amber-50 border-amber-200 text-amber-700'
                : 'bg-sky-50 border-sky-200 text-sky-700'
            }`}>
              {todayRate}% Hôm nay
            </div>
          </div>

          <div className="space-y-2">
            <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  todayRate >= 80 ? 'bg-emerald-500' : todayRate >= 50 ? 'bg-amber-500' : 'bg-sky-500'
                }`}
                style={{ width: `${Math.min(todayRate, 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-slate-500 pt-1">
              <span>Đã uống: <strong className="text-emerald-700 font-bold">{todayTaken} / {todayScheduled}</strong> cữ</span>
              <span>Bỏ qua: <strong className="text-rose-600 font-bold">{todaySkipped}</strong> cữ</span>
              <span>Còn lại: <strong className="text-slate-700 font-bold">{Math.max(0, todayScheduled - todayTaken - todaySkipped)}</strong></span>
            </div>
          </div>
        </div>

        {/* Card 2: Tuân thủ cả quá trình */}
        <div className="bg-white rounded-2xl border border-slate-100 p-5 shadow-sm space-y-3 relative overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
                <Award size={18} />
              </div>
              <div>
                <span>Tuân thủ cả quá trình</span>
                <span className="block text-[11px] font-normal text-slate-400">Đánh giá toàn bộ lịch sử điều trị</span>
              </div>
            </div>

            <div className="px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-bold">
              {overallRate}% Tích lũy
            </div>
          </div>

          <div className="space-y-2">
            <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(overallRate, 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-slate-500 pt-1">
              <span>Tổng đã uống: <strong className="text-slate-800">{stats.takenCount}</strong> lần</span>
              <span>Tổng bỏ qua: <strong className="text-slate-800">{stats.skippedCount}</strong> lần</span>
              <span>Tổng lịch: <strong className="text-slate-800">{stats.totalReminders}</strong></span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Header & Add Button ── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-slate-900">Lịch uống theo buổi trong ngày</h2>
          <p className="text-xs text-slate-500 mt-0.5">Theo dõi lịch uống và ghi nhận trạng thái hàng ngày</p>
        </div>

        <button
          type="button"
          onClick={() => setShowAddForm(!showAddForm)}
          className="h-9 px-3.5 bg-sky-600 hover:bg-sky-700 text-white font-semibold text-xs rounded-lg flex items-center gap-1.5 transition-all shadow-sm shadow-sky-500/20"
        >
          <Plus size={15} />
          <span>Thêm nhắc nhở</span>
        </button>
      </div>

      {/* ── Inline Add Form ── */}
      {showAddForm && (
        <form onSubmit={handleAddReminder} className="bg-white rounded-2xl border border-sky-100 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <span className="font-bold text-slate-900 text-xs">Tạo lịch nhắc uống thuốc mới</span>
            <button type="button" onClick={() => setShowAddForm(false)} className="text-slate-400 hover:text-slate-700">
              <X size={16} />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Tên thuốc *</label>
              <input
                type="text"
                value={newDrugName}
                onChange={(e) => setNewDrugName(e.target.value)}
                placeholder="VD: Amlodipine 5mg"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 outline-none focus:border-sky-500 focus:bg-white focus:ring-2 focus:ring-sky-100 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Liều dùng (Tùy chọn)</label>
              <input
                type="text"
                value={newDosage}
                onChange={(e) => setNewDosage(e.target.value)}
                placeholder="VD: 1 viên sau ăn sáng"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 outline-none focus:border-sky-500 focus:bg-white focus:ring-2 focus:ring-sky-100 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Buổi trong ngày</label>
              <select
                value={newTimeOfDay}
                onChange={(e) => {
                  const val = e.target.value as typeof newTimeOfDay;
                  setNewTimeOfDay(val);
                  const slot = TIME_OF_DAY_SLOTS.find((s) => s.key === val);
                  if (slot) setNewTime(slot.defaultTime);
                }}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 outline-none focus:border-sky-500 focus:bg-white focus:ring-2 focus:ring-sky-100 text-xs"
              >
                <option value="morning">Buổi Sáng (08:00)</option>
                <option value="noon">Buổi Trưa (12:00)</option>
                <option value="afternoon">Buổi Chiều (17:00)</option>
                <option value="evening">Buổi Tối (21:00)</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Giờ nhắc nhở</label>
              <input
                type="time"
                value={newTime}
                onChange={(e) => setNewTime(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 outline-none focus:border-sky-500 focus:bg-white focus:ring-2 focus:ring-sky-100 text-xs"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="px-3.5 py-1.5 border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 font-semibold rounded-lg text-xs"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-1.5 bg-sky-600 hover:bg-sky-700 text-white font-semibold rounded-lg flex items-center gap-1.5 text-xs shadow-sm shadow-sky-500/20"
            >
              {isSubmitting ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              <span>Lưu lịch uống</span>
            </button>
          </div>
        </form>
      )}

      {/* ── 4 Slot Grid ── */}
      {isLoadingReminders ? (
        <div className="p-8 text-center text-slate-500 text-xs flex items-center justify-center gap-2 rounded-2xl border border-slate-100 bg-white">
          <Loader2 size={16} className="animate-spin text-sky-600" />
          <span>Đang tải lịch nhắc nhở...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {TIME_OF_DAY_SLOTS.map((slot) => {
            const SlotIcon = slot.icon;
            const slotReminders = reminders.filter((r) => r.timeOfDay === slot.key);

            return (
              <div key={slot.key} className="bg-white rounded-2xl border border-slate-100 p-4 space-y-3 shadow-sm">
                {/* Header */}
                <div className="p-2.5 bg-slate-50/80 rounded-xl flex items-center justify-between">
                  <div className="flex items-center gap-2 font-bold text-slate-900 text-xs">
                    <div className={`p-1 rounded-lg ${slot.color}`}>
                      <SlotIcon size={15} />
                    </div>
                    <span>{slot.label}</span>
                  </div>
                  <span className="text-[11px] text-slate-500 font-medium">{slot.defaultTime}</span>
                </div>

                {/* Items */}
                {slotReminders.length === 0 ? (
                  <div className="p-4 text-center text-slate-400 text-xs rounded-xl border border-dashed border-slate-200">
                    Chưa có lịch uống trong buổi này
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {slotReminders.map((r) => {
                      const todayLog = getTodayLog(r.logs);
                      const isTakenToday = todayLog?.status === 'taken';
                      const isSkippedToday = todayLog?.status === 'skipped';

                      return (
                        <div
                          key={r.id}
                          className={`p-3.5 rounded-xl border transition-all space-y-2.5 ${
                            !r.isActive
                              ? 'bg-slate-50/60 border-slate-100 opacity-60'
                              : isTakenToday
                              ? 'bg-emerald-50/30 border-emerald-200 shadow-sm'
                              : isSkippedToday
                              ? 'bg-rose-50/30 border-rose-200 shadow-sm'
                              : 'bg-white border-slate-200 shadow-sm'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <div className={`p-1.5 rounded-lg ${
                                isTakenToday ? 'bg-emerald-100 text-emerald-700' : 'bg-sky-50 text-sky-600'
                              }`}>
                                <Pill size={15} className="shrink-0" />
                              </div>
                              <div>
                                <span className="font-bold text-slate-900 text-xs block">{r.drugName}</span>
                                {r.dosageInstruction && (
                                  <span className="text-xs text-slate-500 block">{r.dosageInstruction}</span>
                                )}
                              </div>
                            </div>

                            <div className="flex items-center gap-1">
                              <button
                                type="button"
                                onClick={() => handleToggleActive(r)}
                                title={r.isActive ? 'Tắt nhắc nhở' : 'Bật nhắc nhở'}
                                className={`p-1.5 rounded-lg text-xs transition-all ${
                                  r.isActive
                                    ? 'bg-sky-50 text-sky-600 hover:bg-sky-100'
                                    : 'bg-slate-100 text-slate-400 hover:bg-slate-200'
                                }`}
                              >
                                <Power size={13} />
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDelete(r.id, r.drugName)}
                                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-all"
                                title="Xóa lịch"
                              >
                                <Trash2 size={13} />
                              </button>
                            </div>
                          </div>

                          <div className="flex items-center justify-between text-xs text-slate-500 border-t border-slate-100 pt-2">
                            <span className="flex items-center gap-1 font-medium text-slate-700">
                              <Clock size={12} className="text-slate-400" />
                              {r.reminderTime}
                            </span>

                            {todayLog ? (
                              <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold flex items-center gap-1 ${
                                isTakenToday
                                  ? 'text-emerald-700 bg-emerald-100 border border-emerald-200'
                                  : 'text-rose-700 bg-rose-100 border border-rose-200'
                              }`}>
                                {isTakenToday ? (
                                  <>
                                    <Check size={11} className="stroke-[3]" />
                                    <span>Đã uống hôm nay</span>
                                  </>
                                ) : (
                                  <>
                                    <X size={11} className="stroke-[3]" />
                                    <span>Đã bỏ qua hôm nay</span>
                                  </>
                                )}
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded-full text-[11px] font-medium text-amber-700 bg-amber-50 border border-amber-200 flex items-center gap-1">
                                <AlertCircle size={11} />
                                <span>Chưa uống hôm nay</span>
                              </span>
                            )}
                          </div>

                          {/* Action Buttons: 1 lần trong ngày, có thể chuyển đổi taken <-> skipped */}
                          <div className="grid grid-cols-2 gap-2 pt-0.5">
                            <button
                              type="button"
                              onClick={() => handleLogStatus(r.id, 'taken', r.drugName)}
                              disabled={!r.isActive || isTakenToday}
                              className={`py-1.5 px-2 font-semibold text-xs rounded-lg flex items-center justify-center gap-1.5 transition-all ${
                                isTakenToday
                                  ? 'bg-emerald-600 text-white cursor-default shadow-sm ring-2 ring-emerald-200 opacity-95'
                                  : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-600 hover:text-white border border-emerald-200'
                              } disabled:cursor-not-allowed`}
                            >
                              <CheckCircle2 size={13} className={isTakenToday ? 'text-white' : 'text-emerald-600'} />
                              <span>{isTakenToday ? 'Đã uống' : 'Đã uống'}</span>
                            </button>

                            <button
                              type="button"
                              onClick={() => handleLogStatus(r.id, 'skipped', r.drugName)}
                              disabled={!r.isActive || isSkippedToday}
                              className={`py-1.5 px-2 font-semibold text-xs rounded-lg flex items-center justify-center gap-1.5 transition-all ${
                                isSkippedToday
                                  ? 'bg-rose-600 text-white cursor-default shadow-sm ring-2 ring-rose-200 opacity-95'
                                  : 'bg-slate-100 text-slate-700 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-200 border border-slate-200'
                              } disabled:cursor-not-allowed`}
                            >
                              <XCircle size={13} className={isSkippedToday ? 'text-white' : 'text-slate-500'} />
                              <span>{isSkippedToday ? 'Bỏ qua' : 'Bỏ qua'}</span>
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
