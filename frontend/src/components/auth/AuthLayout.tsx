'use client';

/**
 * AuthLayout — Minimalist Clinical Split-Screen Layout cho Login / Register.
 * Thiết kế chuẩn bệnh viện: Nghiêm trang, Tối giản, Đơn sắc chức năng (#0F172A, #334155, #FFFFFF, #E2E8F0).
 * Bo góc chuẩn rounded-none / rounded-sm, loại bỏ gradient màu mè.
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
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center font-[var(--font-inter)] selection:bg-slate-900 selection:text-white">
      <div className="flex-1 flex overflow-hidden min-h-screen">
        
        {/* ── Left Column: Minimalist Clinical Authority (Desktop Split-Screen) ── */}
        <div className="hidden lg:flex lg:w-1/2 bg-slate-900 text-white p-12 flex-col justify-between border-r border-slate-800">
          
          {/* Top Brand Identity */}
          <div>
            <Link href="/login" className="inline-flex items-center gap-2.5">
              <div className="w-8 h-8 bg-white text-slate-900 flex items-center justify-center font-black">
                <Activity size={18} />
              </div>
              <div>
                <span className="text-base font-black tracking-tight text-white block">
                  MEDISCAN<span className="text-slate-400 font-normal">.AI</span>
                </span>
                <span className="text-[10px] font-mono text-slate-400 tracking-wider uppercase">
                  Clinical Safety & Drug Evaluation
                </span>
              </div>
            </Link>
          </div>

          {/* Center Clinical Manifest */}
          <div className="max-w-md space-y-6 my-auto">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 border border-slate-700 bg-slate-800/50 text-[11px] font-mono text-slate-300 font-bold uppercase tracking-wider">
              <Cpu size={13} className="text-slate-400" />
              <span>PURE-ONNX | LOCAL CPU INFERENCE</span>
            </div>

            <div className="space-y-3">
              <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight leading-snug uppercase">
                Hệ Thống Đánh Giá Tương Tác Thuốc Chuẩn Y Khoa
              </h1>
              <p className="text-xs text-slate-400 leading-relaxed font-medium">
                Nền tảng kiểm soát an toàn đơn thuốc tự động 4 lớp: Trùng lặp hoạt chất, 
                Tương tác thuốc - thuốc, Xung đột bệnh nền, và Đối chiếu liều dùng khuyến cáo.
              </p>
            </div>

            {/* Protocol Metrics Grid */}
            <div className="grid grid-cols-2 gap-3 pt-2">
              <div className="p-3 border border-slate-800 bg-slate-950/60 text-xs">
                <div className="flex items-center gap-2 text-slate-300 font-bold font-mono text-[11px] mb-1">
                  <Lock size={12} className="text-slate-400" />
                  <span>256-BIT ENCRYPTION</span>
                </div>
                <p className="text-[11px] text-slate-400">Bảo mật dữ liệu phiên lâm sàng</p>
              </div>

              <div className="p-3 border border-slate-800 bg-slate-950/60 text-xs">
                <div className="flex items-center gap-2 text-slate-300 font-bold font-mono text-[11px] mb-1">
                  <ShieldCheck size={12} className="text-slate-400" />
                  <span>PRIVACY COMPLIANT</span>
                </div>
                <p className="text-[11px] text-slate-400">Dữ liệu lưu trữ độc lập theo UID</p>
              </div>
            </div>

            {/* Checklist */}
            <div className="space-y-2 pt-1 text-xs font-mono text-slate-400">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={13} className="text-slate-300 shrink-0" />
                <span>Hoàn toàn không gửi dữ liệu ảnh qua Cloud VLM</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 size={13} className="text-slate-300 shrink-0" />
                <span>Đối chiếu từ điển 100+ thuốc chuẩn Việt Nam & OpenFDA</span>
              </div>
            </div>
          </div>

          {/* Footer note */}
          <div className="text-[10px] font-mono text-slate-500 flex items-center justify-between border-t border-slate-800 pt-4">
            <span>© 2026 MEDISCAN AI. ALL RIGHTS RESERVED.</span>
            <span>SYSTEM REVISION 2.4</span>
          </div>

        </div>

        {/* ── Right Column: Minimalist Form Container ── */}
        <div className="w-full lg:w-1/2 bg-white flex items-center justify-center p-6 sm:p-12 overflow-y-auto">
          <div className="w-full max-w-md space-y-6">
            
            {/* Mobile Header Logo */}
            <div className="lg:hidden mb-6">
              <div className="inline-flex items-center gap-2.5">
                <div className="w-8 h-8 bg-slate-900 text-white flex items-center justify-center font-black">
                  <Activity size={18} />
                </div>
                <span className="text-base font-black tracking-tight text-slate-900">
                  MEDISCAN<span className="text-slate-500 font-normal">.AI</span>
                </span>
              </div>
            </div>

            {/* Header Title */}
            <div className="border-b border-slate-200 pb-4">
              <h2 className="text-xl font-black text-slate-900 tracking-tight uppercase">
                {title}
              </h2>
              <p className="text-xs text-slate-600 mt-1 font-medium">
                {subtitle}
              </p>
            </div>

            {/* Main Form Content */}
            <div className="space-y-4">
              {children}
            </div>

            {/* Mode Switcher */}
            <div className="pt-2 text-center text-xs font-mono text-slate-600 border-t border-slate-100">
              {mode === 'login' ? (
                <p>
                  Chưa có tài khoản truy cập?{' '}
                  <Link href="/register" className="font-bold text-slate-900 underline underline-offset-4 hover:text-slate-700">
                    Đăng ký tài khoản mới →
                  </Link>
                </p>
              ) : (
                <p>
                  Đã có tài khoản hệ thống?{' '}
                  <Link href="/login" className="font-bold text-slate-900 underline underline-offset-4 hover:text-slate-700">
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
