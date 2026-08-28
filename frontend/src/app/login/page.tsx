'use client';

/**
 * Login Page — Màn hình Đăng nhập (Sky Blue & Borderless Minimalism).
 * Rebranding: MediScan.
 */

import React, { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { AuthLayout } from '@/components/auth/AuthLayout';
import { useAuthStore } from '@/store/authStore';
import { toast } from '@/components/common/Toast';
import { User, Lock, Eye, EyeOff, Loader2, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react';

function LoginFormContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectParam = searchParams.get('redirect');
  const registeredParam = searchParams.get('registered');

  const { login, isLoading, error, clearError } = useAuthStore();

  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState('');

  useEffect(() => {
    clearError();
  }, [clearError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setFormError('');

    if (!usernameOrEmail.trim()) {
      setFormError('Vui lòng nhập tên đăng nhập hoặc email');
      return;
    }
    if (!password) {
      setFormError('Vui lòng nhập mật khẩu');
      return;
    }

    try {
      const response = await login({ usernameOrEmail: usernameOrEmail.trim(), password });
      toast.success('Đăng nhập thành công!');

      if (response.user.isProfileCompleted) {
        router.replace(redirectParam || '/cabinet');
      } else {
        router.replace('/onboarding');
      }
    } catch {
      // Handled in store
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Registration Success Banner */}
      {registeredParam === 'true' && !error && !formError && (
        <div className="p-3.5 border border-emerald-200 bg-emerald-50/80 rounded-xl text-emerald-800 text-xs flex items-start gap-2.5">
          <CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-0.5" />
          <span>Đăng ký thành công! Hãy đăng nhập để hoàn tất khai báo hồ sơ.</span>
        </div>
      )}

      {/* Error Alert Banner */}
      {(error || formError) && (
        <div className="p-3.5 border border-rose-200 bg-rose-50/80 rounded-xl text-rose-800 text-xs flex items-start gap-2.5">
          <AlertCircle size={16} className="text-rose-600 shrink-0 mt-0.5" />
          <span>{formError || error}</span>
        </div>
      )}

      {/* Username or Email Input */}
      <div>
        <label className="block text-xs font-semibold text-slate-700 mb-1.5">
          Tên đăng nhập hoặc Email <span className="text-rose-500">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
            <User size={15} />
          </div>
          <input
            type="text"
            value={usernameOrEmail}
            onChange={(e) => {
              setUsernameOrEmail(e.target.value);
              setFormError('');
            }}
            placeholder="bacsi.smith hoặc user@gmail.com"
            className="w-full pl-10 pr-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-sky-500 focus:bg-white focus:ring-2 focus:ring-sky-100 transition-all"
          />
        </div>
      </div>

      {/* Password Input */}
      <div>
        <label className="block text-xs font-semibold text-slate-700 mb-1.5">
          Mật khẩu <span className="text-rose-500">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
            <Lock size={15} />
          </div>
          <input
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              setFormError('');
            }}
            placeholder="••••••••••••"
            className="w-full pl-10 pr-10 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-sky-500 focus:bg-white focus:ring-2 focus:ring-sky-100 transition-all"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-700"
          >
            {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full h-10 bg-sky-600 hover:bg-sky-700 text-white font-semibold text-xs rounded-lg flex items-center justify-center gap-2 transition-all shadow-sm disabled:opacity-50 mt-2"
      >
        {isLoading ? (
          <>
            <Loader2 size={15} className="animate-spin" />
            <span>Đang xác thực...</span>
          </>
        ) : (
          <>
            <span>Đăng nhập</span>
            <ArrowRight size={15} />
          </>
        )}
      </button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <AuthLayout
      title="Đăng nhập"
      subtitle="Truy cập hệ thống quản lý thuốc và tương tác y khoa"
      mode="login"
    >
      <Suspense fallback={
        <div className="p-8 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
          <Loader2 size={16} className="animate-spin text-sky-600" />
          <span>Đang tải...</span>
        </div>
      }>
        <LoginFormContent />
      </Suspense>
    </AuthLayout>
  );
}
