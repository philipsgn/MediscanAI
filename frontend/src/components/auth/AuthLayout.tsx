'use client';

/**
 * AuthLayout — Clinical-Grade Medical Split-Screen Layout cho Login/Register (Stage 8).
 * Tông màu: Clinical Teal (#0F766E), Deep Slate (#0F172A), Soft Ice Blue (#F0FDFA).
 * Hiển thị Security Badges (HIPAA-compliant feel, 256-bit SSL encryption).
 */

import React from 'react';
import Link from 'next/link';
import { ShieldCheck, Lock, Activity, Sparkles, CheckCircle2 } from 'lucide-react';

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle: string;
  mode: 'login' | 'register';
}

export function AuthLayout({ children, title, subtitle, mode }: AuthLayoutProps) {
  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center font-[var(--font-inter)] selection:bg-teal-500 selection:text-white">
      <div className="flex-1 flex overflow-hidden min-h-screen">
        
        {/* ── Left Column: Medical Branding & Trust Metrics (Desktop Split-Screen) ── */}
        <div className="hidden lg:flex lg:w-1/2 relative bg-gradient-to-br from-slate-900 via-teal-950 to-slate-950 p-12 flex-col justify-between overflow-hidden border-r border-teal-900/30">
          {/* Subtle Ambient Glowing Effects */}
          <div className="absolute top-1/4 -left-20 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 right-0 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

          {/* Top Logo */}
          <div className="relative z-10">
            <Link href="/" className="inline-flex items-center gap-3 group">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-teal-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-teal-900/40 group-hover:scale-105 transition-transform duration-300">
                <Activity size={24} className="text-white" />
              </div>
              <div>
                <span className="text-xl font-black tracking-tight text-white flex items-center gap-1">
                  Mediscan<span className="text-teal-400">AI</span>
                </span>
                <span className="block text-[10px] font-semibold text-teal-300/80 uppercase tracking-widest">
                  Clinical Safety Platform
                </span>
              </div>
            </Link>
          </div>

          {/* Center Showcase Content */}
          <div className="relative z-10 my-auto max-w-lg space-y-8 py-8">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-teal-900/40 border border-teal-500/30 text-teal-300 text-xs font-semibold backdrop-blur-md">
              <Sparkles size={14} className="text-teal-400" />
              <span>Hệ Thống Trợ Lý Cảnh Báo Tương Tác Thuốc chuẩn Y Tế</span>
            </div>

            <div className="space-y-4">
              <h1 className="text-3xl sm:text-4xl font-extrabold text-white leading-tight tracking-tight">
                An Toàn Thuốc Tối Đa Cho <br />
                <span className="bg-gradient-to-r from-teal-300 via-emerald-400 to-cyan-300 bg-clip-text text-transparent">
                  Sức Khỏe Bệnh Nhân
                </span>
              </h1>
              <p className="text-slate-400 text-sm leading-relaxed">
                Tự động trích xuất toa thuốc & vỏ hộp bằng thuật toán Pure OCR On-Premise, 
                đánh giá tương tác chéo 4 lớp chuẩn lâm sàng.
              </p>
            </div>

            {/* Security & Clinical Badges Grid */}
            <div className="grid grid-cols-2 gap-3.5 pt-2">
              <div className="p-3.5 rounded-xl bg-slate-800/40 border border-teal-900/40 backdrop-blur-sm flex items-start gap-3">
                <div className="p-2 rounded-lg bg-teal-900/50 text-teal-400 shrink-0">
                  <Lock size={16} />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-200">256-bit SSL Encryption</h4>
                  <p className="text-[11px] text-slate-400 mt-0.5">Bảo mật dữ liệu đường truyền</p>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-800/40 border border-teal-900/40 backdrop-blur-sm flex items-start gap-3">
                <div className="p-2 rounded-lg bg-emerald-900/50 text-emerald-400 shrink-0">
                  <ShieldCheck size={16} />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-200">HIPAA-Compliant Feel</h4>
                  <p className="text-[11px] text-slate-400 mt-0.5">Bảo vệ riêng tư y tế tuyệt đối</p>
                </div>
              </div>
            </div>

            {/* Checklist Trust Metrics */}
            <div className="space-y-2.5 pt-2 text-xs font-medium text-slate-300">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 size={15} className="text-emerald-400 shrink-0" />
                <span>Không phụ thuộc VLM thương mại — OCR vận hành 100% On-Premise</span>
              </div>
              <div className="flex items-center gap-2.5">
                <CheckCircle2 size={15} className="text-emerald-400 shrink-0" />
                <span>Kiểm soát trùng lặp hoạt chất, quá liều và xung đột bệnh nền</span>
              </div>
            </div>
          </div>

          {/* Footer note */}
          <div className="relative z-10 text-[11px] text-slate-500 flex items-center justify-between border-t border-slate-800/80 pt-4">
            <span>© 2026 Mediscan AI. Clinical Safety First.</span>
            <span className="flex items-center gap-1.5 text-teal-400/90 font-mono text-[10px]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              SYSTEM ONLINE
            </span>
          </div>
        </div>

        {/* ── Right Column: Minimalist Form Container (Desktop & Mobile Centered Card) ── */}
        <div className="w-full lg:w-1/2 bg-slate-950 flex items-center justify-center p-4 sm:p-8 lg:p-12 relative overflow-y-auto">
          <div className="w-full max-w-md space-y-6">
            
            {/* Mobile Header Logo */}
            <div className="lg:hidden text-center mb-6">
              <Link href="/" className="inline-flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-teal-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-teal-900/40">
                  <Activity size={22} className="text-white" />
                </div>
                <span className="text-xl font-black tracking-tight text-white">
                  Mediscan<span className="text-teal-400">AI</span>
                </span>
              </Link>
            </div>

            {/* Form Title */}
            <div className="text-center lg:text-left">
              <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                {title}
              </h2>
              <p className="text-xs sm:text-sm text-slate-400 mt-1.5">
                {subtitle}
              </p>
            </div>

            {/* Main Form Content */}
            <div className="bg-slate-900/80 rounded-2xl border border-slate-800 p-6 sm:p-8 shadow-2xl backdrop-blur-xl">
              {children}
            </div>

            {/* Mode Switch Navigation Link */}
            <div className="text-center text-xs text-slate-400">
              {mode === 'login' ? (
                <p>
                  Chưa có tài khoản?{' '}
                  <Link href="/register" className="font-bold text-teal-400 hover:text-teal-300 transition-colors underline underline-offset-4">
                    Đăng ký ngay
                  </Link>
                </p>
              ) : (
                <p>
                  Đã có tài khoản?{' '}
                  <Link href="/login" className="font-bold text-teal-400 hover:text-teal-300 transition-colors underline underline-offset-4">
                    Đăng nhập tại đây
                  </Link>
                </p>
              )}
            </div>

            {/* Security footer badge on form side */}
            <div className="pt-4 flex items-center justify-center gap-2 text-[11px] text-slate-500">
              <Lock size={12} className="text-teal-500" />
              <span>Dữ liệu được bảo vệ bằng mã hóa chuẩn y tế 256-bit</span>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
