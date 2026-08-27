'use client';

/**
 * ClinicalHeader — Global Navigation Header chuẩn Lâm Sàng Minimalist (Stage 10+ Harmonization).
 * Height h-14, Border 1px slate-200, Nền trắng, typography tracking-tight.
 * Navigation Index: [01] HỒ SƠ Y TẾ | [02] TỦ THUỐC & QUẢN LÝ | [03] QUÉT & PHÂN TÍCH ĐƠN
 */

import React, { useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { LogOut, User, Activity, Cpu, ShieldCheck } from 'lucide-react';

export function ClinicalHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAuthenticated, isHydrated, logout, hydrateFromStorage } = useAuthStore();

  useEffect(() => {
    hydrateFromStorage();
  }, [hydrateFromStorage]);

  // Ẩn Header trên các trang Auth khách (/login, /register)
  if (pathname === '/login' || pathname === '/register') {
    return null;
  }

  const handleLogout = () => {
    logout();
    router.replace('/login');
  };

  const navItems = [
    { label: '[01] HỒ SƠ Y TẾ', href: '/onboarding', match: '/onboarding' },
    { label: '[02] TỦ THUỐC & QUẢN LÝ', href: '/cabinet', match: '/cabinet' },
    { label: '[03] QUÉT & PHÂN TÍCH ĐƠN', href: '/scan', match: '/scan' },
  ];

  return (
    <header className="sticky top-0 z-40 h-14 bg-white border-b border-slate-200 font-[var(--font-inter)] select-none">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-full flex items-center justify-between gap-4">
        
        {/* ── Left: Identity & Clinical Engine Badge ── */}
        <div className="flex items-center gap-3 shrink-0">
          <Link href="/cabinet" className="flex items-center gap-2 group">
            <div className="w-7 h-7 bg-slate-900 flex items-center justify-center text-white rounded-none border border-slate-900">
              <Activity size={16} />
            </div>
            <span className="text-sm font-black tracking-tight text-slate-900">
              MEDISCAN<span className="text-slate-500 font-semibold">.AI</span>
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-1.5 px-2 py-0.5 border border-slate-200 bg-slate-50 text-[10px] font-mono text-slate-600 font-bold uppercase tracking-wider">
            <Cpu size={11} className="text-slate-500" />
            <span>PURE-ONNX | CPU ENGINE</span>
          </div>
        </div>

        {/* ── Center: Route Navigation Index ── */}
        <nav className="hidden md:flex items-center gap-1">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.match);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`px-3 py-1.5 text-xs font-mono font-bold tracking-tight transition-colors border ${
                  isActive
                    ? 'bg-slate-900 text-white border-slate-900'
                    : 'bg-transparent text-slate-600 border-transparent hover:border-slate-200 hover:text-slate-900'
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* ── Right: Session Context & Actions ── */}
        <div className="flex items-center gap-3 shrink-0">
          {isHydrated && isAuthenticated && user ? (
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex flex-col text-right">
                <span className="text-xs font-bold text-slate-900 leading-none">
                  {user.fullName || user.username}
                </span>
                <span className="text-[10px] font-mono text-slate-500 leading-none mt-1">
                  UID: {user.id.slice(0, 10)}
                </span>
              </div>

              <button
                type="button"
                onClick={handleLogout}
                className="h-8 px-2.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-mono font-bold flex items-center gap-1.5 transition-colors"
                title="Đăng xuất khỏi hệ thống"
              >
                <LogOut size={13} className="text-slate-500" />
                <span className="hidden sm:inline">ĐĂNG XUẤT</span>
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="h-8 px-3 bg-slate-900 hover:bg-slate-800 text-white text-xs font-mono font-bold flex items-center gap-1.5"
            >
              <User size={13} />
              <span>ĐĂNG NHẬP</span>
            </Link>
          )}
        </div>

      </div>
    </header>
  );
}
