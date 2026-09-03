'use client';

/**
 * OnboardingGate — Client Component bọc {children} trong root layout (Stage 10+ Harmonization).
 *
 * State Machine Logic:
 * - Bỏ qua kiểm tra nếu đang ở các trang công khai /login hoặc /register.
 * - Kiểm tra session xác thực (token trong localStorage/cookies).
 * - Nếu đã xác thực nhưng chưa hoàn tất hồ sơ y tế (/onboarding) ➔ Bắt buộc điều hướng về /onboarding.
 * - Nếu đã có hồ sơ y tế ➔ Cho phép truy cập /cabinet, /scan, /history.
 */

import React, { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useUserProfileStore, isOnboardingComplete } from '@/store/userProfileStore';
import { useAuthStore } from '@/store/authStore';

const PUBLIC_PAGES = ['/login', '/register'];

export function OnboardingGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { fetchProfile } = useUserProfileStore();
  const { hydrateFromStorage: hydrateAuth, isAuthenticated } = useAuthStore();

  const [status, setStatus] = useState<'checking' | 'ready'>('checking');

  useEffect(() => {
    // 1. Nếu đang ở các trang Auth công khai -> render ngay lập tức
    if (PUBLIC_PAGES.includes(pathname)) {
      setStatus('ready');
      return;
    }

    // 2. Hydrate auth & profile state
    hydrateAuth();
    fetchProfile();

    const token = typeof window !== 'undefined' ? localStorage.getItem('mediscan_access_token') : null;

    // 3. Nếu chưa có token -> chuyển về /login
    if (!token) {
      router.replace('/login');
      return;
    }

    // 4. Nếu đang ở /onboarding -> cho phép truy cập
    if (pathname === '/onboarding') {
      setStatus('ready');
      return;
    }

    // 5. Kiểm tra trạng thái hoàn thành onboarding
    if (!isOnboardingComplete()) {
      router.replace('/onboarding');
      return;
    }

    setStatus('ready');
  }, [pathname, router, hydrateAuth, fetchProfile]);

  if (status === 'checking' && !PUBLIC_PAGES.includes(pathname)) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center font-mono text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-slate-900 animate-ping" />
          <span>INITIALIZING CLINICAL SESSION...</span>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
