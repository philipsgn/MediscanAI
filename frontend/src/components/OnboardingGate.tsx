'use client';

/**
 * OnboardingGate — Client Component bọc {children} trong root layout.
 *
 * Logic:
 * - useEffect đọc localStorage key `mediscan_user_profile`
 * - Nếu thiếu/invalid VÀ pathname !== '/onboarding' → router.replace('/onboarding')
 * - Nếu profile hợp lệ HOẶC đang ở /onboarding → render children bình thường
 *
 * ⚠️ [F4.10 lesson]: Đây là 'use client' Component RIÊNG, KHÔNG đặt hook
 * trực tiếp vào layout.tsx (Server Component) — tránh crash runtime khi next build.
 *
 * Pattern tương tự QueryProvider và MedicalDisclaimerModal.
 */

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useUserProfileStore, isOnboardingComplete } from '@/store/userProfileStore';

export function OnboardingGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const hydrateFromStorage = useUserProfileStore((s) => s.hydrateFromStorage);

  // 'checking' = đang kiểm tra localStorage, 'ready' = đã quyết định
  const [status, setStatus] = useState<'checking' | 'ready'>('checking');

  useEffect(() => {
    // Hydrate store từ localStorage
    hydrateFromStorage();

    // Nếu đang ở /onboarding rồi → cho qua luôn
    if (pathname === '/onboarding') {
      setStatus('ready');
      return;
    }

    // Kiểm tra profile hợp lệ
    if (!isOnboardingComplete()) {
      router.replace('/onboarding');
      // Không setStatus('ready') — sẽ giữ skeleton cho đến khi navigate xong
      return;
    }

    setStatus('ready');
  }, [pathname, router, hydrateFromStorage]);

  // Trong lúc check: hiển thị skeleton nhẹ (không chặn hoàn toàn — chỉ flash nhẹ)
  if (status === 'checking') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
      </div>
    );
  }

  return <>{children}</>;
}
