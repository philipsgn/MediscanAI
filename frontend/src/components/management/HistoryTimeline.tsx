'use client';

/**
 * HistoryTimeline — Component Dòng Thời Gian Lịch Sử Quét & Đánh Giá Thuốc (Stage 10).
 * Clinical Teal Palette (#0F766E), Slate (#0F172A).
 * Phân cấp Severity (Đỏ/Vàng/Xanh), Modal xem lại báo cáo chi tiết & Nút "Khôi phục vào Tủ thuốc".
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Clock, AlertTriangle, AlertCircle, CheckCircle2, FileText, RotateCcw,
  Calendar, ChevronRight, X, Sparkles, Filter, Pill, Search
} from 'lucide-react';
import { useHistoryReminderStore } from '@/store/historyReminderStore';
import { useCabinetStore } from '@/store/cabinetStore';
import { IScanHistoryItem } from '@/types/history_reminder';
import { toast } from '@/components/common/Toast';

export function HistoryTimeline() {
  const router = useRouter();
  const { histories, fetchHistories, isLoadingHistories } = useHistoryReminderStore();
  const { addDrugs } = useCabinetStore();

  const [selectedItem, setSelectedItem] = useState<IScanHistoryItem | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');

  useEffect(() => {
    fetchHistories();
  }, [fetchHistories]);

  const filteredHistories = histories.filter((item) => {
    const matchesSev = filterSeverity === 'ALL' || item.highestSeverity === filterSeverity;
    const matchesSearch =
      !searchTerm ||
      item.drugNames.some((d) => d.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (item.summary && item.summary.toLowerCase().includes(searchTerm.toLowerCase()));
    return matchesSev && matchesSearch;
  });

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'HIGH':
        return {
          label: 'HIGH SEVERITY (Cảnh Báo Nặng)',
          color: 'bg-rose-950/80 text-rose-300 border-rose-700/80',
          icon: AlertCircle,
        };
      case 'MEDIUM':
        return {
          label: 'MEDIUM SEVERITY (Cảnh Báo Vừa)',
          color: 'bg-amber-950/80 text-amber-300 border-amber-700/80',
          icon: AlertTriangle,
        };
      case 'LOW':
        return {
          label: 'LOW SEVERITY (Cảnh Báo Nhẹ)',
          color: 'bg-sky-950/80 text-sky-300 border-sky-700/80',
          icon: AlertCircle,
        };
      default:
        return {
          label: 'SAFE / NO ALERTS (An Toàn)',
          color: 'bg-emerald-950/80 text-emerald-300 border-emerald-700/80',
          icon: CheckCircle2,
        };
    }
  };

  const handleRestoreToCabinet = (item: IScanHistoryItem) => {
    if (!item.drugNames || item.drugNames.length === 0) {
      toast.error('Không tìm thấy danh sách thuốc trong phiên scan này.');
      return;
    }

    const newCabinetItems = item.drugNames.map((name) => ({
      brandName: name,
      strength: 'Theo toa cũ',
      confidenceScore: 1.0,
      isVerified: true,
      inputSource: item.sourceType as 'prescription' | 'packaging' | 'manual',
    }));

    addDrugs(newCabinetItems);
    toast.success(`Đã khôi phục ${newCabinetItems.length} thuốc vào Tủ thuốc!`);
    router.push('/scan');
  };

  return (
    <div className="space-y-6">
      {/* ── Top Filter & Search Bar ── */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/80 p-4 rounded-2xl border border-slate-800 backdrop-blur-md">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3.5 top-3 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Tìm kiếm theo tên thuốc hoặc tóm tắt..."
            className="w-full pl-10 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 outline-none focus:border-teal-500 transition-all"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter size={15} className="text-slate-400 shrink-0" />
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-300 outline-none focus:border-teal-500 transition-all font-semibold"
          >
            <option value="ALL">Tất cả mức cảnh báo</option>
            <option value="HIGH">🔴 Cảnh báo Nặng (HIGH)</option>
            <option value="MEDIUM">🟡 Cảnh báo Vừa (MEDIUM)</option>
            <option value="LOW">🔵 Cảnh báo Nhẹ (LOW)</option>
            <option value="NONE">🟢 An toàn (NONE)</option>
          </select>
        </div>
      </div>

      {/* ── Timeline Sessions Stream ── */}
      {isLoadingHistories ? (
        <div className="p-12 text-center text-slate-400 text-xs flex flex-col items-center gap-2">
          <Clock size={24} className="animate-spin text-teal-400" />
          <span>Đang tải lịch sử phiên quét...</span>
        </div>
      ) : filteredHistories.length === 0 ? (
        <div className="p-12 text-center bg-slate-900/50 border border-slate-800/60 rounded-2xl text-slate-400 space-y-2">
          <FileText size={32} className="mx-auto text-slate-600" />
          <p className="text-sm font-bold text-slate-300">Chưa có lịch sử phiên quét nào</p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Mỗi lần bạn thực hiện quét toa hoặc phân tích tủ thuốc, thông tin sẽ được lưu vết tại đây.
          </p>
        </div>
      ) : (
        <div className="relative border-l-2 border-slate-800 ml-4 sm:ml-6 space-y-6 pl-6 sm:pl-8 py-2">
          {filteredHistories.map((item) => {
            const badge = getSeverityBadge(item.highestSeverity);
            const BadgeIcon = badge.icon;
            const dateStr = new Date(item.scannedAt).toLocaleString('vi-VN', {
              day: '2-digit',
              month: '2-digit',
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            });

            return (
              <div key={item.id} className="relative group">
                {/* Timeline Dot Indicator */}
                <div className="absolute -left-[31px] sm:-left-[39px] top-4 w-4 h-4 rounded-full bg-slate-900 border-2 border-teal-500 group-hover:scale-125 transition-transform" />

                {/* Main Session Card */}
                <div className="bg-slate-900/90 rounded-2xl border border-slate-800/90 p-5 shadow-xl hover:border-teal-900/80 transition-all space-y-3.5 backdrop-blur-md">
                  
                  {/* Top Header Row */}
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
                      <Calendar size={14} className="text-teal-400" />
                      <span>{dateStr}</span>
                      <span className="text-slate-600">•</span>
                      <span className="capitalize text-slate-300">
                        Nguồn: {item.sourceType === 'prescription' ? 'Toa thuốc' : item.sourceType === 'packaging' ? 'Vỏ hộp' : 'Nhập tay'}
                      </span>
                    </div>

                    <div className={`px-2.5 py-1 rounded-lg border text-[11px] font-bold flex items-center gap-1.5 ${badge.color}`}>
                      <BadgeIcon size={13} />
                      <span>{badge.label}</span>
                    </div>
                  </div>

                  {/* Drug List Badges */}
                  <div>
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1.5">
                      Danh sách thuốc ({item.drugNames.length})
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {item.drugNames.map((d, i) => (
                        <span key={i} className="px-2.5 py-1 rounded-lg bg-slate-950 text-slate-200 border border-slate-800 text-xs font-semibold flex items-center gap-1.5">
                          <Pill size={12} className="text-teal-400" />
                          {d}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Summary Text if present */}
                  {item.summary && (
                    <p className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded-xl border border-slate-850 italic">
                      &quot;{item.summary}&quot;
                    </p>
                  )}

                  {/* Bottom Action Row */}
                  <div className="flex items-center justify-between pt-1 text-xs">
                    <button
                      type="button"
                      onClick={() => setSelectedItem(item)}
                      className="text-teal-400 hover:text-teal-300 font-bold flex items-center gap-1 transition-colors"
                    >
                      <span>Xem báo cáo chi tiết</span>
                      <ChevronRight size={14} />
                    </button>

                    <button
                      type="button"
                      onClick={() => handleRestoreToCabinet(item)}
                      className="px-3 py-1.5 rounded-lg bg-teal-950 hover:bg-teal-900 text-teal-300 border border-teal-800/80 font-bold flex items-center gap-1.5 transition-all active:scale-95"
                    >
                      <RotateCcw size={13} />
                      <span>Khôi phục vào Tủ thuốc</span>
                    </button>
                  </div>

                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Detail Modal for Past Report ── */}
      {selectedItem && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl p-6 shadow-2xl space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-white font-extrabold text-sm">
                <Sparkles size={18} className="text-teal-400" />
                <span>Chi Tiết Phiên Scan ({selectedItem.id})</span>
              </div>
              <button
                type="button"
                onClick={() => setSelectedItem(null)}
                className="text-slate-400 hover:text-white"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-500 font-bold block mb-1">Thời gian quét:</span>
                <span className="text-slate-200 font-mono">{new Date(selectedItem.scannedAt).toLocaleString('vi-VN')}</span>
              </div>

              <div>
                <span className="text-slate-500 font-bold block mb-1">Danh sách thuốc:</span>
                <ul className="list-disc list-inside text-slate-200 space-y-0.5">
                  {selectedItem.drugNames.map((name, i) => (
                    <li key={i} className="font-semibold">{name}</li>
                  ))}
                </ul>
              </div>

              {selectedItem.summary && (
                <div>
                  <span className="text-slate-500 font-bold block mb-1">Tóm tắt kết quả:</span>
                  <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-300">
                    {selectedItem.summary}
                  </div>
                </div>
              )}

              {selectedItem.rawPayload && (
                <div>
                  <span className="text-slate-500 font-bold block mb-1">Payload JSON nguyên bản:</span>
                  <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[10px] font-mono text-teal-300 overflow-x-auto max-h-48">
                    {JSON.stringify(selectedItem.rawPayload, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => {
                  handleRestoreToCabinet(selectedItem);
                  setSelectedItem(null);
                }}
                className="px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-bold text-xs flex items-center gap-1.5"
              >
                <RotateCcw size={14} />
                <span>Khôi phục vào Tủ thuốc</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
