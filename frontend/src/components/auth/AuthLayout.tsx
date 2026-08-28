'use client';

/**
 * AuthLayout — Split-Screen Layout cho Login / Register (Sky Blue & Borderless Minimalism).
 * Rebranding: MediScan.
 */

import React from 'react';
import Link from 'next/link';
import { Activity, ShieldCheck, Lock, Cpu, CheckCircle2 } from 'lucide-react';

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle: string;
  mode: 'login' | 'register';
}

export function AuthLayout({ children, title, subtitle, mode }: AuthLayoutProps) {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center font-[var(--font-inter)] selection:bg-sky-500 selection:text-white">
      <div className="flex-1 flex overflow-hidden min-h-screen">
        
        {/* ── Left Column: Sky Slate Authority (Desktop Split-Screen) ── */}
        <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-slate-900 via-sky-950 to-slate-900 text-white p-12 flex-col justify-between border-r border-slate-800 relative overflow-hidden">
          
          {/* Subtle background glow */}
          <div className="absolute top-0 right-0 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-0 w-80 h-80 bg-sky-600/10 rounded-full blur-3xl pointer-events-none" />

          {/* Top Brand Identity */}
          <div className="relative z-10">
            <Link href="/login" className="inline-flex items-center gap-2.5">
              <div className="w-9 h-9 bg-sky-500 text-white flex items-center justify-center rounded-xl shadow-lg shadow-sky-500/20 font-black">
                <Activity size={20} />
              </div>
              <div>
                <span className="text-lg font-black tracking-tight text-white block">
                  Medi<span className="text-sky-400">Scan</span>
                </span>
                <span className="text-[11px] text-sky-200/70 tracking-wide">
                  Đánh giá an toàn & Tương tác thuốc
                </span>
              </div>
            </Link>
          </div>

          {/* Center Clinical Manifest */}
          <div className="max-w-md space-y-6 my-auto relative z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-500/10 border border-sky-400/20 text-xs text-sky-300 font-medium">
              <Cpu size={13} className="text-sky-400" />
              <span>Xử lý cục bộ ONNX CPU</span>
            </div>

            <div className="space-y-3">
              <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight leading-snug">
                Kiểm Soát Đơn Thuốc Đa Tầng An Toàn & Chuẩn Xác
              </h1>
              <p className="text-xs text-slate-300 leading-relaxed font-normal">
                Hệ thống tự động phát hiện trùng lặp hoạt chất, tương tác thuốc - thuốc, chống chỉ định bệnh nền và đối chiếu liều dùng khuyến nghị.
              </p>
            </div>

            {/* Protocol Metrics Grid */}
            <div className="grid grid-cols-2 gap-3 pt-2">
              <div className="p-3.5 rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm">
                <div className="flex items-center gap-2 text-sky-300 font-semibold text-xs mb-1">
                  <Lock size={13} className="text-sky-400" />
                  <span>Bảo mật 256-bit</span>
                </div>
                <p className="text-[11px] text-slate-400">Mã hóa an toàn dữ liệu phiên làm việc</p>
              </div>

              <div className="p-3.5 rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm">
                <div className="flex items-center gap-2 text-sky-300 font-semibold text-xs mb-1">
                  <ShieldCheck size={13} className="text-sky-400" />
                  <span>Riêng tư tuyệt đối</span>
                </div>
                <p className="text-[11px] text-slate-400">Dữ liệu cá nhân lưu trữ theo định danh UID</p>
              </div>
            </div>

            {/* Checklist */}
            <div className="space-y-2.5 pt-1 text-xs text-slate-300">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 size={15} className="text-sky-400 shrink-0" />
                <span>Không gửi dữ liệu ảnh qua Cloud AI bên thứ ba</span>
              </div>
              <div className="flex items-center gap-2.5">
                <CheckCircle2 size={15} className="text-sky-400 shrink-0" />
                <span>Đối chiếu từ điển 100+ thuốc Việt Nam & OpenFDA</span>
              </div>
            </div>
          </div>

          {/* Footer note */}
          <div className="text-[11px] text-slate-500 flex items-center justify-between border-t border-slate-800/80 pt-4 relative z-10">
            <span>© 2026 MediScan</span>
            <span>Phiên bản 2.5</span>
          </div>

        </div>

        {/* ── Right Column: Form Container ── */}
        <div className="w-full lg:w-1/2 bg-white flex items-center justify-center p-6 sm:p-12 overflow-y-auto">
          <div className="w-full max-w-md space-y-6">
            
            {/* Mobile Header Logo */}
            <div className="lg:hidden mb-4">
              <div className="inline-flex items-center gap-2.5">
                <div className="w-8 h-8 bg-sky-500 text-white flex items-center justify-center rounded-lg shadow-sm font-black">
                  <Activity size={18} />
                </div>
                <span className="text-lg font-black tracking-tight text-slate-900">
                  Medi<span className="text-sky-600">Scan</span>
                </span>
              </div>
            </div>

            {/* Header Title */}
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-xl font-black text-slate-900 tracking-tight">
                {title}
              </h2>
              <p className="text-xs text-slate-500 mt-1 font-normal">
                {subtitle}
              </p>
            </div>

            {/* Main Form Content */}
            <div className="space-y-4">
              {children}
            </div>

            {/* Mode Switcher */}
            <div className="pt-2 text-center text-xs text-slate-500 border-t border-slate-100">
              {mode === 'login' ? (
                <p>
                  Chưa có tài khoản?{' '}
                  <Link href="/register" className="font-semibold text-sky-600 hover:text-sky-700 underline underline-offset-4">
                    Đăng ký ngay →
                  </Link>
                </p>
              ) : (
                <p>
                  Đã có tài khoản?{' '}
                  <Link href="/login" className="font-semibold text-sky-600 hover:text-sky-700 underline underline-offset-4">
                    Đăng nhập tại đây →
                  </Link>
                </p>
              )}
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
