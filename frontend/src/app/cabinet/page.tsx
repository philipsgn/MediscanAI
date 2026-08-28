'use client';

/**
 * Clinical Dashboard & Medication Cabinet — Route /cabinet (Material 3 Clinical Design System).
 * Rebranding: MediScan.
 * Tabs: Tủ thuốc | Lịch uống | Lịch sử quét.
 */

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ActiveCabinet } from '@/components/cabinet/ActiveCabinet';
import { ReminderSchedule } from '@/components/management/ReminderSchedule';
import { HistoryTimeline } from '@/components/management/HistoryTimeline';
import { InteractionAlertCards } from '@/components/report/InteractionAlertCards';
import { IEvaluationResponse } from '@/types/medication';
import { Plus, Pill, Clock, History, ArrowRight, Activity } from 'lucide-react';

export default function CabinetDashboardPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'cabinet' | 'reminders' | 'history'>('cabinet');
  const [report, setReport] = useState<IEvaluationResponse | null>(null);

  const handleReportReady = (newReport: IEvaluationResponse) => {
    setReport(newReport);
    window.scrollTo({ top: 400, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-background font-[var(--font-inter)] text-on-background flex flex-col justify-between">
      
      <div className="flex-grow pb-16">
        {/* ── Dashboard Sub-Header ── */}
        <div className="bg-surface border-b border-outline-variant/30 py-5">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-secondary" />
                <span className="text-xs font-bold text-secondary tracking-wider uppercase">
                  KHÔNG GIAN QUẢN LÝ ĐIỀU TRỊ
                </span>
              </div>
              <h1 className="text-2xl md:text-3xl font-semibold text-primary mt-1">
                Tủ thuốc cá nhân & Lịch uống
              </h1>
            </div>

            {/* Primary CTA: + Quét đơn mới -> */}
            <Link
              href="/scan"
              className="bg-primary hover:bg-primary-container text-on-primary py-3 px-6 rounded-lg shadow-layer-1 flex items-center gap-2 group transition-all shrink-0 text-xs font-semibold"
            >
              <Plus size={16} />
              <span>Quét đơn mới</span>
              <ArrowRight size={14} className="text-on-primary/80 group-hover:translate-x-0.5 transition-transform" />
            </Link>
          </div>
        </div>

        {/* ── Main Workspace ── */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 pt-6 space-y-6">

          {/* ── Tab Switcher (No numbers) ── */}
          <div className="flex border-b border-outline-variant/40 gap-6 overflow-x-auto">
            {[
              { key: 'cabinet', label: 'Tủ thuốc đang dùng', icon: Pill },
              { key: 'reminders', label: 'Lịch uống & Tuân thủ', icon: Clock },
              { key: 'history', label: 'Lịch sử phiên quét', icon: History },
            ].map((tab) => {
              const TabIcon = tab.icon;
              const isCurrent = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setActiveTab(tab.key as typeof activeTab)}
                  className={`py-3 font-bold text-xs flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                    isCurrent
                      ? 'border-primary text-primary pb-3'
                      : 'border-transparent text-on-surface-variant pb-3 hover:text-primary'
                  }`}
                >
                  <TabIcon size={15} />
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
                <div className="border border-outline-variant/30 bg-surface-container-lowest rounded-xl p-6 shadow-layer-1 space-y-4">
                  <div className="border-b border-outline-variant/30 pb-3 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-bold text-primary">
                      <Activity size={18} className="text-primary" />
                      <span>Kết quả đánh giá an toàn đơn thuốc</span>
                    </div>
                    <span className="text-xs text-on-surface-variant font-medium">
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

      {/* ── Footer ── */}
      <footer className="bg-surface-container-low border-t border-outline-variant py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-on-surface-variant font-medium">
          <div className="flex items-center gap-2">
            <span className="font-bold text-primary">MediScan</span>
            <span>&copy; {new Date().getFullYear()} MediScan. All rights reserved.</span>
          </div>
          <div className="flex gap-4">
            <a href="#" className="hover:text-primary transition-colors">Quy định</a>
            <span>|</span>
            <a href="#" className="hover:text-primary transition-colors">Bảo mật</a>
            <span>|</span>
            <a href="#" className="hover:text-primary transition-colors">Trợ giúp</a>
          </div>
        </div>
      </footer>

    </div>
  );
}
