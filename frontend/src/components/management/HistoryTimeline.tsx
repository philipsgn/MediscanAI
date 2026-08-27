'use client';

/**
 * HistoryTimeline — Dòng Thời Gian Lịch Sử Quét & Đánh Giá Thuốc (Minimalist Clinical Grade).
 * Border 1px slate-200, Nền trắng/xám, rounded-none / rounded-sm.
 * Phân cấp Severity đơn sắc, Modal xem báo cáo & Nút "Khôi phục vào Tủ thuốc".
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Clock, AlertTriangle, AlertCircle, CheckCircle2, FileText, RotateCcw,
  Calendar, ChevronRight, X, Filter, Pill, Search
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
          label: 'CẢNH BÁO NẶNG (HIGH)',
          color: 'text-rose-800 bg-rose-50 border-rose-300',
          icon: AlertCircle,
        };
      case 'MEDIUM':
        return {
          label: 'CẢNH BÁO VỪA (MEDIUM)',
          color: 'text-amber-800 bg-amber-50 border-amber-300',
          icon: AlertTriangle,
        };
      case 'LOW':
        return {
          label: 'CẢNH BÁO NHẸ (LOW)',
          color: 'text-sky-800 bg-sky-50 border-sky-300',
          icon: AlertCircle,
        };
      default:
        return {
          label: 'AN TOÀN (NONE)',
          color: 'text-emerald-800 bg-emerald-50 border-emerald-300',
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
    router.push('/cabinet');
  };

  return (
    <div className="space-y-4">
      {/* ── Top Filter & Search Bar ── */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-white p-3 border border-slate-200">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Tìm kiếm theo tên thuốc hoặc tóm tắt..."
            className="w-full pl-9 pr-3 py-1.5 bg-slate-50 border border-slate-300 text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-slate-900 font-mono"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter size={14} className="text-slate-500 shrink-0" />
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="px-2.5 py-1.5 bg-slate-50 border border-slate-300 text-xs text-slate-800 outline-none focus:border-slate-900 font-mono"
          >
            <option value="ALL">Tất cả mức độ</option>
            <option value="HIGH">Cảnh báo Nặng (HIGH)</option>
            <option value="MEDIUM">Cảnh báo Vừa (MEDIUM)</option>
            <option value="LOW">Cảnh báo Nhẹ (LOW)</option>
            <option value="NONE">An toàn (NONE)</option>
          </select>
        </div>
      </div>

      {/* ── Timeline Sessions ── */}
      {isLoadingHistories ? (
        <div className="p-8 text-center text-slate-500 text-xs font-mono flex items-center justify-center gap-2 border border-slate-200 bg-white">
          <Clock size={16} className="animate-spin text-slate-700" />
          <span>ĐANG TẢI DỮ LIỆU LỊCH SỬ...</span>
        </div>
      ) : filteredHistories.length === 0 ? (
        <div className="p-8 text-center bg-white border border-slate-200 text-slate-500 font-mono space-y-1">
          <FileText size={24} className="mx-auto text-slate-400" />
          <p className="text-xs font-bold text-slate-700">CHƯA CÓ LỊCH SỬ PHIÊN QUÉT NÀO</p>
          <p className="text-[11px] text-slate-400">Các phiên phân tích thuốc sẽ được lưu vết tự động tại đây.</p>
        </div>
      ) : (
        <div className="space-y-3">
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
              <div key={item.id} className="bg-white border border-slate-200 p-4 space-y-3">
                {/* Header Row */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
                  <div className="flex items-center gap-2 text-xs font-mono text-slate-600">
                    <Calendar size={13} className="text-slate-500" />
                    <span className="font-bold">{dateStr}</span>
                    <span className="text-slate-300">•</span>
                    <span className="uppercase text-[11px]">
                      NGUỒN: {item.sourceType === 'prescription' ? 'TOA THUỐC' : item.sourceType === 'packaging' ? 'VỎ HỘP' : 'NHẬP TAY'}
                    </span>
                  </div>

                  <div className={`px-2 py-0.5 border text-[10px] font-mono font-bold flex items-center gap-1 ${badge.color}`}>
                    <BadgeIcon size={12} />
                    <span>{badge.label}</span>
                  </div>
                </div>

                {/* Drug Items */}
                <div>
                  <span className="text-[10px] font-mono font-bold text-slate-500 uppercase block mb-1">
                    Danh mục thuốc ({item.drugNames.length}):
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {item.drugNames.map((d, i) => (
                      <span key={i} className="px-2 py-0.5 bg-slate-50 text-slate-800 border border-slate-200 text-xs font-mono flex items-center gap-1">
                        <Pill size={11} className="text-slate-500" />
                        {d}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Summary */}
                {item.summary && (
                  <p className="text-xs text-slate-700 bg-slate-50 p-2.5 border border-slate-200 font-mono">
                    {item.summary}
                  </p>
                )}

                {/* Actions */}
                <div className="flex items-center justify-between pt-1 border-t border-slate-100 text-xs font-mono">
                  <button
                    type="button"
                    onClick={() => setSelectedItem(item)}
                    className="text-slate-900 hover:text-slate-700 font-bold flex items-center gap-1"
                  >
                    <span>Xem báo cáo chi tiết</span>
                    <ChevronRight size={13} />
                  </button>

                  <button
                    type="button"
                    onClick={() => handleRestoreToCabinet(item)}
                    className="px-3 py-1 bg-slate-900 hover:bg-slate-800 text-white font-bold flex items-center gap-1.5 transition-colors"
                  >
                    <RotateCcw size={12} />
                    <span>Khôi phục vào Tủ thuốc</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Detail Modal ── */}
      {selectedItem && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-none flex items-center justify-center p-4">
          <div className="bg-white border border-slate-300 w-full max-w-xl p-6 space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <span className="font-mono font-bold text-xs text-slate-900 uppercase">
                CHI TIẾT PHIÊN LÂM SÀNG ({selectedItem.id})
              </span>
              <button
                type="button"
                onClick={() => setSelectedItem(null)}
                className="text-slate-400 hover:text-slate-900"
              >
                <X size={16} />
              </button>
            </div>

            <div className="space-y-3 text-xs font-mono">
              <div>
                <span className="text-slate-500 font-bold block mb-0.5">Thời gian quét:</span>
                <span className="text-slate-900">{new Date(selectedItem.scannedAt).toLocaleString('vi-VN')}</span>
              </div>

              <div>
                <span className="text-slate-500 font-bold block mb-0.5">Danh sách thuốc:</span>
                <ul className="list-disc list-inside text-slate-900 space-y-0.5">
                  {selectedItem.drugNames.map((name, i) => (
                    <li key={i}>{name}</li>
                  ))}
                </ul>
              </div>

              {selectedItem.summary && (
                <div>
                  <span className="text-slate-500 font-bold block mb-0.5">Tóm tắt đánh giá:</span>
                  <div className="p-2.5 bg-slate-50 border border-slate-200 text-slate-800">
                    {selectedItem.summary}
                  </div>
                </div>
              )}

              {selectedItem.rawPayload && (
                <div>
                  <span className="text-slate-500 font-bold block mb-0.5">Payload Dữ liệu Thô (JSON):</span>
                  <pre className="p-2.5 bg-slate-900 text-slate-100 text-[10px] overflow-x-auto max-h-40 font-mono">
                    {JSON.stringify(selectedItem.rawPayload, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-200 font-mono text-xs">
              <button
                type="button"
                onClick={() => {
                  handleRestoreToCabinet(selectedItem);
                  setSelectedItem(null);
                }}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold flex items-center gap-1.5"
              >
                <RotateCcw size={13} />
                <span>Khôi phục vào Tủ thuốc</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
