'use client';

/**
 * Login Page — Màn hình Đăng nhập chuẩn Clinical UI (Stage 8).
 */

import React, { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { AuthLayout } from '@/components/auth/AuthLayout';
import { useAuthStore } from '@/store/authStore';
import { toast } from '@/components/common/Toast';
import { User, Lock, Eye, EyeOff, Loader2, ArrowRight, AlertCircle } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get('redirect') || '/scan';

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
      toast.success('Đăng nhập thành công! Đang chuyển hướng...');
      router.push(redirectUrl);
    } catch {
      // Lỗi đã được lưu vào authStore.error
    }
  };

  return (
    <AuthLayout
      title="Đăng Nhập Hàng Ngày"
      subtitle="Đăng nhập để truy cập Tủ thuốc, Lịch sử đánh giá và Nhắc nhở"
      mode="login"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Error Alert Banner */}
        {(error || formError) && (
          <div className="p-3.5 rounded-xl bg-red-950/60 border border-red-800/60 text-red-300 text-xs font-medium flex items-start gap-2.5 animate-in fade-in duration-200">
            <AlertCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
            <span>{formError || error}</span>
          </div>
        )}

        {/* Username or Email Input */}
        <div>
          <label className="block text-xs font-bold text-slate-300 mb-1.5">
            Tên đăng nhập hoặc Email <span className="text-teal-400">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
              <User size={16} />
            </div>
            <input
              type="text"
              value={usernameOrEmail}
              onChange={(e) => {
                setUsernameOrEmail(e.target.value);
                setFormError('');
              }}
              placeholder="VD: doctor.smith hoặc user@example.com"
              className="w-full pl-10 pr-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all font-medium"
            />
          </div>
        </div>

        {/* Password Input */}
        <div>
          <label className="block text-xs font-bold text-slate-300 mb-1.5">
            Mật khẩu <span className="text-teal-400">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
              <Lock size={16} />
            </div>
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setFormError('');
              }}
              placeholder="Nhập mật khẩu của bạn"
              className="w-full pl-10 pr-10 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all font-medium"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-300 transition-colors"
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full mt-2 py-3 px-4 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white font-bold text-xs shadow-lg shadow-teal-900/30 flex items-center justify-center gap-2 transition-all active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              <span>Đang Xác Thực...</span>
            </>
          ) : (
            <>
              <span>ĐĂNG NHẬP HỆ THỐNG</span>
              <ArrowRight size={16} />
            </>
          )}
        </button>
      </form>
    </AuthLayout>
  );
}
