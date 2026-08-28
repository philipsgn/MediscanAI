'use client';

import React, { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';

interface UserLifecycleGateProps {
  children: React.ReactNode;
}

export function UserLifecycleGate({ children }: UserLifecycleGateProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isAuthenticated, isHydrated } = useAuthStore();

  useEffect(() => {
    if (!isHydrated) return;

    if (isAuthenticated && user) {
      const isCompleted = user.isProfileCompleted === true;

      // If user profile is not completed and tries to access app dashboards, redirect to /onboarding
      if (!isCompleted && (pathname.startsWith('/cabinet') || pathname.startsWith('/scan') || pathname.startsWith('/history'))) {
        router.replace('/onboarding');
      }
    }
  }, [isAuthenticated, user, isHydrated, pathname, router]);

  return <>{children}</>;
}
