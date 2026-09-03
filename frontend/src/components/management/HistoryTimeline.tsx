'use client';

/**
 * HistoryTimeline — Dòng Thời Gian Lịch Sử Quét (Sky Blue & Borderless Minimalism).
 * Tái dựng chi tiết báo cáo lâm sàng từ rawPayload không cần ảnh gốc (Privacy Invariant).
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Clock, AlertTriangle, AlertCircle, CheckCircle2, FileText, RotateCcw,
  Calendar, ChevronRight, X, Filter, Pill, Search, Trash2
} from 'lucide-react';
import { useHistoryReminderStore } from '@/store/historyReminderStore';
import { useCabinetStore } from '@/store/cabinetStore';
import { IScanHistoryItem } from '@/types/history_reminder';
import { toast } from '@/components/common/Toast';

export function HistoryTimeline() {
  const router = useRouter();
  const { histories, fetchHistories, deleteHistory, isLoadingHistories } = useHistoryReminderStore();
  const { addDrugs } = useCabinetStore();

  const [selectedItem, setSelectedItem] = useState<IScanHistoryItem | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const loadData = useCallback(() => {
    fetchHistories({ severity: filterSeverity });
  }, [fetchHistories, filterSeverity]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const filteredHistories = histories.filter((item) => {
    const matchesSearch =
      !searchTerm ||
      item.drugNames.some((d) => d.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (item.summary && item.summary.toLowerCase().includes(searchTerm.toLowerCase()));
    return matchesSearch;
  });

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'HIGH':
        return {
          label: 'Cảnh báo nặng',
          color: 'text-rose-700 bg-rose-50 border-rose-200',
          icon: AlertCircle,
        };
      case 'MEDIUM':
        return {
          label: 'Cần chú ý',
          color: 'text-amber-700 bg-amber-50 border-amber-200',
          icon: AlertTriangle,
        };
      case 'LOW':
        return {
          label: 'Thông tin nhẹ',
          color: 'text-sky-700 bg-sky-50 border-sky-200',
          icon: AlertCircle,
        };
      default:
        return {
          label: 'Đạt an toàn',
          color: 'text-emerald-700 bg-emerald-50 border-emerald-200',
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

  const handleDeleteHistory = async (id: string) => {
    if (!confirm('Bạn có chắc chắn muốn xóa bản ghi lịch sử này?')) return;
    try {
      await deleteHistory(id);
      toast.success('Đã xóa phiên lịch sử quét.');
    } catch {
      toast.error('Không thể xóa lịch sử quét. Vui lòng thử lại.');
    }
  };

  return (
    <div className="space-y-4 font-[var(--font-inter)] text-xs">
      
      {/* ── Top Filter & Search Bar ── */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-white p-3.5 rounded-2xl border border-slate-100 shadow-sm">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Tìm kiếm theo tên thuốc hoặc nội dung..."
            className="w-full pl-9 pr-3.5 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-sky-500 focus:bg-white focus:ring-2 focus:ring-sky-100 transition-all"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter size={14} className="text-slate-400 shrink-0" />
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 outline-none focus:border-sky-500 focus:bg-white"
          >
            <option value="ALL">Tất cả mức độ</option>
            <option value="HIGH">Cảnh báo nặng</option>
            <option value="MEDIUM">Cần chú ý</option>
            <option value="LOW">Thông tin nhẹ</option>
            <option value="NONE">Đạt an toàn</option>
          </select>
        </div>
      </div>

      {/* ── Timeline Sessions ── */}
      {isLoadingHistories ? (
        <div className="p-8 text-center text-slate-500 text-xs flex items-center justify-center gap-2 rounded-2xl border border-slate-100 bg-white">
          <Clock size={16} className="animate-spin text-sky-600" />
          <span>Đang tải dữ liệu lịch sử...</span>
        </div>
      ) : filteredHistories.length === 0 ? (
        <div className="p-10 text-center bg-white rounded-2xl border border-slate-100 text-slate-500 space-y-1.5 shadow-sm">
          <FileText size={28} className="mx-auto text-slate-300" />
          <p className="text-sm font-semibold text-slate-800">Chưa có lịch sử phiên quét nào</p>
          <p className="text-xs text-slate-400">Các phiên đánh giá đơn thuốc sẽ được lưu tự động tại đây.</p>
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
              <div key={item.id} className="bg-white rounded-2xl border border-slate-100 p-5 space-y-3 shadow-sm hover:border-slate-200 transition-all">
                {/* Header Row */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2 text-xs text-slate-600">
                    <Calendar size={13} className="text-slate-400" />
                    <span className="font-semibold text-slate-900">{dateStr}</span>
                    <span className="text-slate-300">•</span>
                    <span className="text-slate-500">
                      Nguồn: {item.sourceType === 'prescription' ? 'Toa thuốc' : item.sourceType === 'packaging' ? 'Vỏ hộp' : 'Nhập tay'}
                    </span>
                  </div>

                  <div className={`px-2.5 py-0.5 rounded-full border text-[11px] font-semibold flex items-center gap-1.5 ${badge.color}`}>
                    <BadgeIcon size={12} />
                    <span>{badge.label}</span>
                  </div>
                </div>

                {/* Drug Items */}
                <div>
                  <span className="text-[11px] font-semibold text-slate-500 block mb-1.5">
                    Danh mục thuốc ({item.drugNames.length}):
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {item.drugNames.map((d, i) => (
                      <span key={i} className="px-2.5 py-1 bg-slate-50 text-slate-800 border border-slate-100 rounded-lg text-xs font-medium flex items-center gap-1.5">
                        <Pill size={12} className="text-sky-600" />
                        {d}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Summary */}
                {item.summary && (
                  <p className="text-xs text-slate-700 bg-slate-50/60 p-3 rounded-xl border border-slate-100 leading-relaxed">
                    {item.summary}
                  </p>
                )}

                {/* Actions */}
                <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => setSelectedItem(item)}
                      className="text-sky-600 hover:text-sky-700 font-semibold flex items-center gap-1"
                    >
                      <span>Xem chi tiết</span>
                      <ChevronRight size={14} />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteHistory(item.id)}
                      className="text-rose-500 hover:text-rose-700 font-medium flex items-center gap-1"
                    >
                      <Trash2 size={13} />
                      <span>Xóa</span>
                    </button>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleRestoreToCabinet(item)}
                    className="px-3.5 py-1.5 bg-slate-100 hover:bg-sky-50 text-slate-700 hover:text-sky-700 font-semibold rounded-lg flex items-center gap-1.5 transition-all"
                  >
                    <RotateCcw size={13} />
                    <span>Khôi phục vào tủ</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Detail Modal ── */}
      {selectedItem && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-100 w-full max-w-lg p-6 space-y-4 shadow-xl max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <span className="font-bold text-sm text-slate-900">
                Chi tiết phiên quét & Báo cáo lâm sàng
              </span>
              <button
                type="button"
                onClick={() => setSelectedItem(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-all"
              >
                <X size={16} />
              </button>
            </div>

            <div className="space-y-3.5 text-xs">
              <div>
                <span className="text-slate-500 font-semibold block mb-0.5">Thời gian:</span>
                <span className="text-slate-900 font-medium">{new Date(selectedItem.scannedAt).toLocaleString('vi-VN')}</span>
              </div>

              <div>
                <span className="text-slate-500 font-semibold block mb-1">Thuốc đã trích xuất:</span>
                <ul className="list-disc list-inside text-slate-800 space-y-1">
                  {selectedItem.drugNames.map((name, i) => (
                    <li key={i}>{name}</li>
                  ))}
                </ul>
              </div>

              {selectedItem.summary && (
                <div>
                  <span className="text-slate-500 font-semibold block mb-1">Tóm tắt đánh giá:</span>
                  <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl text-slate-800 leading-relaxed">
                    {selectedItem.summary}
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-between items-center pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => {
                  handleDeleteHistory(selectedItem.id);
                  setSelectedItem(null);
                }}
                className="px-3 py-1.5 text-rose-600 hover:bg-rose-50 rounded-lg font-medium flex items-center gap-1"
              >
                <Trash2 size={13} />
                <span>Xóa lịch sử</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  handleRestoreToCabinet(selectedItem);
                  setSelectedItem(null);
                }}
                className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white font-semibold rounded-lg flex items-center gap-1.5 shadow-sm shadow-sky-500/20 text-xs transition-all"
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
