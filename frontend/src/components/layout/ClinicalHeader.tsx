'use client';

/**
 * ClinicalHeader — Global Navigation Header (Material 3 Design System).
 * Rebranding: MediScan.
 * Tabs: Hồ sơ y tế | Tủ thuốc | Quét đơn.
 */

import React, { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { LogOut, User, Activity, ChevronDown, Pill, Bell, Settings } from 'lucide-react';

export function ClinicalHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAuthenticated, isHydrated, logout, hydrateFromStorage } = useAuthStore();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    hydrateFromStorage();
  }, [hydrateFromStorage]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Ẩn Header trên các trang Auth khách (/login, /register)
  if (pathname === '/login' || pathname === '/register') {
    return null;
  }

  const handleLogout = () => {
    logout();
    router.replace('/login');
  };

  const navItems = [
    { label: 'Hồ sơ y tế', href: '/onboarding', match: '/onboarding' },
    { label: 'Tủ thuốc', href: '/cabinet', match: '/cabinet' },
    { label: 'Quét đơn', href: '/scan', match: '/scan' },
  ];

  return (
    <header className="sticky top-0 z-50 h-16 bg-surface border-b border-outline-variant/30 font-[var(--font-inter)] select-none shadow-sm">
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 h-full flex items-center justify-between gap-4">
        
        {/* ── Left: Route Navigation Index ── */}
        <nav className="flex items-center gap-6">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.match);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`py-1 text-xs font-semibold tracking-tight transition-all border-b-2 ${
                  isActive
                    ? 'border-primary text-primary font-bold pb-1'
                    : 'border-transparent text-on-surface-variant hover:text-primary hover:border-outline-variant'
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* ── Center: Branding Centered ── */}
        <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2 group">
          <Link href="/cabinet" className="flex items-center gap-2 group">
            <div className="w-8 h-8 bg-surface-container-low text-primary flex items-center justify-center rounded-lg border border-outline-variant/30 group-hover:bg-surface-container transition-colors">
              <Activity size={18} />
            </div>
            <span className="text-xl font-bold tracking-tight text-primary">
              MediScan
            </span>
          </Link>
        </div>

        {/* ── Right: Profile & Toolbar Actions ── */}
        <div className="flex items-center gap-2 shrink-0 relative" ref={dropdownRef}>
          {isHydrated && isAuthenticated && user ? (
            <>
              {/* Notification & Settings Icon Buttons */}
              <button
                type="button"
                className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container transition-all"
                title="Thông báo"
              >
                <Bell size={16} />
              </button>
              <button
                type="button"
                className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container transition-all"
                title="Cài đặt"
              >
                <Settings size={16} />
              </button>

              {/* User Avatar Pill */}
              <div className="relative ml-1">
                <button
                  type="button"
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className="flex items-center gap-2 hover:bg-surface-container-low p-1 rounded-full transition-all border border-outline-variant/30"
                >
                  <div className="w-8 h-8 rounded-full bg-surface-container-high text-primary flex items-center justify-center text-xs font-bold uppercase shrink-0">
                    {(user.fullName || user.username || 'U').charAt(0).toUpperCase()}
                  </div>
                  <span className="hidden sm:inline text-xs font-bold text-on-surface truncate max-w-[120px] pr-1">
                    {user.fullName || user.username}
                  </span>
                  <ChevronDown size={14} className="text-on-surface-variant shrink-0 mr-1.5" />
                </button>

                {/* Dropdown Floating Menu */}
                {isDropdownOpen && (
                  <div className="absolute right-0 mt-2 w-56 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-layer-1 py-1 z-50">
                    <div className="px-4 py-2.5">
                      <p className="text-xs font-bold text-on-surface truncate">
                        {user.fullName || user.username}
                      </p>
                      <p className="text-xs text-on-surface-variant truncate mt-0.5">
                        {user.email || `ID: ${user.id.slice(0, 8)}`}
                      </p>
                    </div>
                    <div className="border-b border-outline-variant/30" />
                    
                    <Link
                      href="/onboarding"
                      onClick={() => setIsDropdownOpen(false)}
                      className="flex items-center gap-2 px-4 py-2 text-xs text-on-surface-variant hover:bg-surface-container transition-colors"
                    >
                      <User size={14} className="text-on-surface-variant" />
                      <span>Hồ sơ sức khỏe</span>
                    </Link>

                    <Link
                      href="/cabinet"
                      onClick={() => setIsDropdownOpen(false)}
                      className="flex items-center gap-2 px-4 py-2 text-xs text-on-surface-variant hover:bg-surface-container transition-colors"
                    >
                      <Pill size={14} className="text-on-surface-variant" />
                      <span>Tủ thuốc của tôi</span>
                    </Link>

                    <div className="border-b border-outline-variant/30" />

                    <button
                      type="button"
                      onClick={() => {
                        setIsDropdownOpen(false);
                        handleLogout();
                      }}
                      className="w-full flex items-center gap-2 px-4 py-2 text-xs text-rose-600 hover:bg-rose-50 transition-colors text-left font-semibold"
                    >
                      <LogOut size={14} />
                      <span>Đăng xuất</span>
                    </button>
                  </div>
                )}
              </div>
            </>
          ) : (
            <Link
              href="/login"
              className="h-8 px-3.5 bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-sm transition-all"
            >
              <User size={13} />
              <span>Đăng nhập</span>
            </Link>
          )}
        </div>

      </div>
    </header>
  );
}
