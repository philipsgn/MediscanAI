'use client';

/**
 * Login Page — Màn hình Đăng nhập Minimalist Clinical Grade.
 * Form vuông vức (rounded-none), đơn sắc (#0F172A, #334155, #FFFFFF, #E2E8F0).
 * Bọc trong Suspense boundary để tương thích hoàn hảo với Next.js SSG useSearchParams().
 */

import React, { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { AuthLayout } from '@/components/auth/AuthLayout';
import { useAuthStore } from '@/store/authStore';
import { profileService } from '@/services/profileService';
import { toast } from '@/components/common/Toast';
import { User, Lock, Eye, EyeOff, Loader2, ArrowRight, AlertCircle } from 'lucide-react';

function LoginFormContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectParam = searchParams.get('redirect');

  const { login, isLoading, error, clearError } = useAuthStore();

  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setFormError('');

    if (!usernameOrEmail.trim()) {
      setFormError('Vui lòng nhập Tên đăng nhập hoặc Email');
      return;
    }
    if (!password) {
      setFormError('Vui lòng nhập Mật khẩu');
      return;
    }

    try {
      await login({ usernameOrEmail: usernameOrEmail.trim(), password });
      toast.success('Xác thực thành công!');

      // Kiểm tra hồ sơ y tế từ Backend API
      try {
        const profile = await profileService.getProfile();
        if (profile && profile.age) {
          router.replace(redirectParam || '/cabinet');
        } else {
          router.replace('/onboarding');
        }
      } catch {
        // Chưa có profile trên server
        router.replace('/onboarding');
      }
    } catch {
      // Error is set in authStore.error
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Error Alert Banner */}
      {(error || formError) && (
        <div className="p-3 border border-rose-300 bg-rose-50 text-rose-800 text-xs font-mono flex items-start gap-2">
          <AlertCircle size={15} className="text-rose-600 shrink-0 mt-0.5" />
          <span>{formError || error}</span>
        </div>
      )}

      {/* Username or Email Input */}
      <div>
        <label className="block text-xs font-mono font-bold text-slate-700 uppercase mb-1.5">
          Tên đăng nhập / Email <span className="text-rose-600">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <User size={15} />
          </div>
          <input
            type="text"
            value={usernameOrEmail}
            onChange={(e) => {
              setUsernameOrEmail(e.target.value);
              setFormError('');
            }}
            placeholder="doctor.smith hoặc user@mediscan.ai"
            className="w-full pl-9 pr-3 py-2.5 bg-slate-50 border border-slate-300 rounded-none text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-slate-900 focus:bg-white transition-colors font-mono"
          />
        </div>
      </div>

      {/* Password Input */}
      <div>
        <label className="block text-xs font-mono font-bold text-slate-700 uppercase mb-1.5">
          Mật khẩu bảo mật <span className="text-rose-600">*</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
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
            className="w-full pl-9 pr-9 py-2.5 bg-slate-50 border border-slate-300 rounded-none text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-slate-900 focus:bg-white transition-colors font-mono"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-700"
          >
            {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full h-11 bg-slate-900 hover:bg-slate-800 text-white font-mono font-bold text-xs uppercase flex items-center justify-center gap-2 rounded-none transition-colors disabled:opacity-50"
      >
        {isLoading ? (
          <>
            <Loader2 size={15} className="animate-spin" />
            <span>ĐANG XÁC THỰC...</span>
          </>
        ) : (
          <>
            <span>TIẾP TỤC VÀO PHIÊN LÀM VIỆC</span>
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
      title="ĐĂNG NHẬP HỆ THỐNG"
      subtitle="Nhập thông tin chứng chỉ truy cập phiên làm việc lâm sàng"
      mode="login"
    >
      <Suspense fallback={
        <div className="p-8 text-center font-mono text-xs text-slate-400 flex items-center justify-center gap-2">
          <Loader2 size={16} className="animate-spin text-slate-600" />
          <span>LOADING AUTHENTICATION MODULE...</span>
        </div>
      }>
        <LoginFormContent />
      </Suspense>
    </AuthLayout>
  );
}
