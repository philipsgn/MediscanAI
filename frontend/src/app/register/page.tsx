'use client';

/**
 * Register Page — Màn hình Đăng ký tài khoản chuẩn Clinical UI (Stage 8).
 * Tích hợp Live Password Strength Meter & validation trực quan.
 */

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { AuthLayout } from '@/components/auth/AuthLayout';
import { PasswordStrengthMeter } from '@/components/auth/PasswordStrengthMeter';
import { useAuthStore } from '@/store/authStore';
import { toast } from '@/components/common/Toast';
import { User, Mail, Lock, Eye, EyeOff, Loader2, ArrowRight, AlertCircle, ShieldCheck } from 'lucide-react';

export default function RegisterPage() {
  const router = useRouter();
  const { register, isLoading, error, clearError } = useAuthStore();

  const [fullName, setFullName] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setFormError('');

    if (!username.trim() || username.length < 3) {
      setFormError('Tên đăng nhập phải có ít nhất 3 ký tự');
      return;
    }
    if (!email.trim() || !email.includes('@')) {
      setFormError('Email không hợp lệ');
      return;
    }
    if (!password || password.length < 6) {
      setFormError('Mật khẩu phải có ít nhất 6 ký tự');
      return;
    }
    if (password !== confirmPassword) {
      setFormError('Mật khẩu nhập lại không khớp');
      return;
    }

    try {
      await register({
        username: username.trim(),
        email: email.trim(),
        password,
        fullName: fullName.trim() || undefined,
      });
      toast.success('Đăng ký tài khoản thành công!');
      router.push('/onboarding');
    } catch {
      // Lỗi đã lưu ở authStore.error
    }
  };

  return (
    <AuthLayout
      title="Tạo Tài Khoản Mới"
      subtitle="Đăng ký để cá nhân hóa hồ sơ sức khỏe và cảnh báo an toàn thuốc"
      mode="register"
    >
      <form onSubmit={handleSubmit} className="space-y-3.5">
        {/* Error Alert Banner */}
        {(error || formError) && (
          <div className="p-3 rounded-xl bg-red-950/60 border border-red-800/60 text-red-300 text-xs font-medium flex items-start gap-2.5 animate-in fade-in duration-200">
            <AlertCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
            <span>{formError || error}</span>
          </div>
        )}

        {/* Full Name Input (Optional) */}
        <div>
          <label className="block text-xs font-bold text-slate-300 mb-1">
            Họ và Tên <span className="text-slate-500 font-normal">— Tùy chọn</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <User size={15} />
            </div>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="VD: Nguyễn Văn A"
              className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all"
            />
          </div>
        </div>

        {/* Username Input */}
        <div>
          <label className="block text-xs font-bold text-slate-300 mb-1">
            Tên đăng nhập <span className="text-teal-400">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <ShieldCheck size={15} />
            </div>
            <input
              type="text"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                setFormError('');
              }}
              placeholder="VD: doctordev"
              className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all font-medium"
            />
          </div>
        </div>

        {/* Email Input */}
        <div>
          <label className="block text-xs font-bold text-slate-300 mb-1">
            Địa chỉ Email <span className="text-teal-400">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <Mail size={15} />
            </div>
            <input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setFormError('');
              }}
              placeholder="VD: user@example.com"
              className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all font-medium"
            />
          </div>
        </div>

        {/* Password Input */}
        <div>
          <label className="block text-xs font-bold text-slate-300 mb-1">
            Mật khẩu <span className="text-teal-400">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <Lock size={15} />
            </div>
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setFormError('');
              }}
              placeholder="Tạo mật khẩu an toàn"
              className="w-full pl-9 pr-9 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all font-medium"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-300 transition-colors"
            >
              {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>

          {/* Live Password Strength Meter */}
          <PasswordStrengthMeter password={password} />
        </div>

        {/* Confirm Password Input */}
        <div>
          <label className="block text-xs font-bold text-slate-300 mb-1">
            Nhập lại mật khẩu <span className="text-teal-400">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <Lock size={15} />
            </div>
            <input
              type={showPassword ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value);
                setFormError('');
              }}
              placeholder="Xác nhận lại mật khẩu"
              className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all font-medium"
            />
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full mt-3 py-3 px-4 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white font-bold text-xs shadow-lg shadow-teal-900/30 flex items-center justify-center gap-2 transition-all active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              <span>Đang Khởi Tạo...</span>
            </>
          ) : (
            <>
              <span>HOÀN TẤT ĐĂNG KÝ TÀI KHOẢN</span>
              <ArrowRight size={16} />
            </>
          )}
        </button>
      </form>
    </AuthLayout>
  );
}
