'use client';

/**
 * Medical Management Dashboard Page — Route /history (Stage 10).
 * Quản lý Lịch sử Quét (HistoryTimeline) & Nhắc nhở Uống thuốc (ReminderSchedule).
 * Protected route — Yêu cầu xác thực tài khoản.
 */

import React, { useState } from 'react';
import Link from 'next/link';
import { HistoryTimeline } from '@/components/management/HistoryTimeline';
import { ReminderSchedule } from '@/components/management/ReminderSchedule';
import { Clock, History, Activity, ArrowLeft, ShieldCheck } from 'lucide-react';

export default function ManagementHistoryPage() {
  const [activeTab, setActiveTab] = useState<'history' | 'reminders'>('history');

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-[var(--font-inter)] selection:bg-teal-500 selection:text-white pb-16">
      
      {/* ── Top Header Bar ── */}
      <header className="sticky top-0 z-40 bg-slate-900/90 border-b border-slate-800 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/scan"
              className="p-2 rounded-xl bg-slate-950 text-slate-400 hover:text-white border border-slate-800 transition-colors"
              title="Quay lại Tủ thuốc"
            >
              <ArrowLeft size={18} />
            </Link>
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-teal-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-teal-900/40">
                <Activity size={20} className="text-white" />
              </div>
              <div>
                <h1 className="text-base font-black text-white tracking-tight flex items-center gap-1.5">
                  Quản Lý Y Tế
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-teal-950 text-teal-300 border border-teal-800/60 font-semibold uppercase">
                    Stage 10
                  </span>
                </h1>
                <p className="text-[11px] text-slate-400">Lịch sử đánh giá & Nhắc nhở uống thuốc cá nhân</p>
              </div>
            </div>
          </div>

          <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400 font-semibold bg-slate-950/80 px-3 py-1.5 rounded-xl border border-slate-800">
            <ShieldCheck size={14} className="text-emerald-400" />
            <span>Dữ liệu lưu vết an toàn</span>
          </div>
        </div>
      </header>

      {/* ── Main Container ── */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 pt-6 space-y-6">

        {/* ── Tab Switcher Bar ── */}
        <div className="flex bg-slate-900 p-1.5 rounded-2xl border border-slate-800 max-w-md mx-auto shadow-xl">
          <button
            type="button"
            onClick={() => setActiveTab('history')}
            className={`flex-1 py-2.5 px-4 rounded-xl text-xs font-extrabold flex items-center justify-center gap-2 transition-all duration-300 ${
              activeTab === 'history'
                ? 'bg-gradient-to-r from-teal-600 to-emerald-600 text-white shadow-lg shadow-teal-950'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <History size={16} />
            <span>Lịch Sử Quét & Báo Cáo</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('reminders')}
            className={`flex-1 py-2.5 px-4 rounded-xl text-xs font-extrabold flex items-center justify-center gap-2 transition-all duration-300 ${
              activeTab === 'reminders'
                ? 'bg-gradient-to-r from-teal-600 to-emerald-600 text-white shadow-lg shadow-teal-950'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Clock size={16} />
            <span>Nhắc Nhở Uống Thuốc</span>
          </button>
        </div>

        {/* ── Tab Content Views ── */}
        {activeTab === 'history' ? (
          <HistoryTimeline />
        ) : (
          <ReminderSchedule />
        )}

      </main>
    </div>
  );
}
