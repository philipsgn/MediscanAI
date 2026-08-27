'use client';

/**
 * Clinical Dashboard & Medication Cabinet — Route /cabinet (Phase 3 Harmonization).
 * Không gian Quản lý Tủ thuốc, Lịch nhắc nhở 4 khung giờ & Lịch sử phiên quét.
 * Primary CTA: [+ QUÉT ĐƠN THUỐC MỚI] ➔ /scan.
 */

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ActiveCabinet } from '@/components/cabinet/ActiveCabinet';
import { ReminderSchedule } from '@/components/management/ReminderSchedule';
import { HistoryTimeline } from '@/components/management/HistoryTimeline';
import { InteractionAlertCards } from '@/components/report/InteractionAlertCards';
import { IEvaluationResponse } from '@/types/medication';
import { Plus, Pill, Clock, History, FileText, ArrowRight, ShieldCheck, Activity } from 'lucide-react';

export default function CabinetDashboardPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'cabinet' | 'reminders' | 'history'>('cabinet');
  const [report, setReport] = useState<IEvaluationResponse | null>(null);

  const handleReportReady = (newReport: IEvaluationResponse) => {
    setReport(newReport);
    // Cuộn xuống khu vực báo cáo nếu có
    window.scrollTo({ top: 400, behavior: 'smooth' });
  };

  return (
    <div className="min-h-full bg-slate-50 font-[var(--font-inter)] text-slate-900 pb-16">
      
      {/* ── Dashboard Sub-Header ── */}
      <div className="bg-white border-b border-slate-200 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-slate-500 uppercase">
                MEDISCAN CLINICAL WORKSPACE
              </span>
              <span className="px-1.5 py-0.2 bg-slate-100 border border-slate-300 text-[10px] font-mono text-slate-700">
                ACTIVE
              </span>
            </div>
            <h1 className="text-lg font-black tracking-tight text-slate-900 uppercase">
              Tủ Thuốc Cá Nhân & Quản Lý Điều Trị
            </h1>
          </div>

          {/* Primary CTA: [+ QUÉT ĐƠN THUỐC MỚI] */}
          <Link
            href="/scan"
            className="h-10 px-4 bg-slate-900 hover:bg-slate-800 text-white font-mono font-bold text-xs flex items-center gap-2 transition-colors shrink-0 shadow-sm"
          >
            <Plus size={15} />
            <span>[+ QUÉT ĐƠN THUỐC MỚI]</span>
            <ArrowRight size={14} className="text-slate-400" />
          </Link>
        </div>
      </div>

      {/* ── Main Workspace ── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 pt-6 space-y-6">

        {/* ── Tab Switcher Index ── */}
        <div className="flex border-b border-slate-200 gap-2 overflow-x-auto">
          {[
            { key: 'cabinet', label: '[01] TỦ THUỐC ĐANG DÙNG', icon: Pill },
            { key: 'reminders', label: '[02] LỊCH UỐNG & TUÂN THỦ', icon: Clock },
            { key: 'history', label: '[03] LỊCH SỬ PHIÊN QUÉT', icon: History },
          ].map((tab) => {
            const TabIcon = tab.icon;
            const isCurrent = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key as typeof activeTab)}
                className={`py-2.5 px-4 font-mono font-bold text-xs flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
                  isCurrent
                    ? 'border-slate-900 text-slate-900 bg-white'
                    : 'border-transparent text-slate-500 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <TabIcon size={14} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* ── Tab Content Views ── */}
        {activeTab === 'cabinet' && (
          <div className="space-y-6">
            <ActiveCabinet onReportReady={handleReportReady} />

            {/* Interaction Evaluation Report (if triggered) */}
            {report && (
              <div className="border border-slate-300 bg-white p-6 space-y-4">
                <div className="border-b border-slate-200 pb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-mono font-bold text-slate-900 uppercase">
                    <Activity size={16} />
                    <span>KẾT QUẢ ĐÁNH GIÁ TƯƠNG TÁC LÂM SÀNG (4 LỚP)</span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-500">
                    Phát hiện: {report.alerts.length} cảnh báo
                  </span>
                </div>

                <InteractionAlertCards report={report} />
              </div>
            )}
          </div>
        )}

        {activeTab === 'reminders' && (
          <ReminderSchedule />
        )}

        {activeTab === 'history' && (
          <HistoryTimeline />
        )}

      </main>

    </div>
  );
}
