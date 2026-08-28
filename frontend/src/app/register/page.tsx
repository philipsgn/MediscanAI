'use client';

/**
 * Register Page — Màn hình Đăng ký (Sky Blue & Borderless Minimalism).
 * Rebranding: MediScan.
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { AuthLayout } from '@/components/auth/AuthLayout';
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

  useEffect(() => {
    clearError();
  }, [clearError]);

  const calculateStrength = (pwd: string) => {
    let score = 0;
    if (pwd.length >= 8) score++;
    if (/[A-Z]/.test(pwd)) score++;
    if (/[0-9]/.test(pwd)) score++;
    if (/[^A-Za-z0-9]/.test(pwd)) score++;
    return score;
  };

  const strength = calculateStrength(password);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setFormError('');

    if (!username.trim()) {
      setFormError('Vui lòng nhập tên đăng nhập');
      return;
    }
    if (username.length < 3) {
      setFormError('Tên đăng nhập tối thiểu 3 ký tự');
      return;
    }
    if (!email.trim()) {
      setFormError('Vui lòng nhập địa chỉ email');
      return;
    }
    if (!password) {
      setFormError('Vui lòng nhập mật khẩu');
      return;
    }
    if (password.length < 8) {
      setFormError('Mật khẩu tối thiểu 8 ký tự');
      return;
    }
    if (password !== confirmPassword) {
      setFormError('Mật khẩu xác nhận không khớp');
      return;
    }

    try {
      await register({
        username: username.trim(),
        email: email.trim(),
        password,
        fullName: fullName.trim() || undefined,
      });

      toast.success('Đăng ký tài khoản thành công! Vui lòng đăng nhập.');
      router.replace('/login?registered=true');
    } catch {
      // Error handled in store
    }
  };

  return (
    <AuthLayout
      title="Tạo tài khoản"
      subtitle="Bắt đầu quản lý đơn thuốc và kiểm tra tương tác an toàn"
      mode="register"
    >
      <form onSubmit={handleSubmit} className="space-y-3.5">
        {/* Error Alert */}
        {(error || formError) && (
          <div className="p-3.5 border border-rose-200 bg-rose-50/80 rounded-xl text-rose-800 text-xs flex items-start gap-2.5">
            <AlertCircle size={16} className="text-rose-600 shrink-0 mt-0.5" />
            <span>{formError || error}</span>
          </div>
        )}

        {/* Full Name */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Họ và tên <span className="text-slate-400 font-normal">(Tùy chọn)</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <User size={15} />
            </div>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Nguyễn Văn A"
              className="w-full pl-10 pr-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-sky-500 focus:bg-white focus:ring-2 focus:ring-sky-100 transition-all"
            />
          </div>
        </div>

        {/* Username */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Tên đăng nhập <span className="text-rose-500">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <span className="font-mono text-xs">@</span>
            </div>
            <input
              type="text"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                setFormError('');
              }}
              placeholder="nguyenvana"
              className="w-full pl-10 pr-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-sky-500 focus:bg-white focus:ring-2 focus:ring-sky-100 transition-all"
            />
          </div>
        </div>

        {/* Email */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Địa chỉ Email <span className="text-rose-500">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <Mail size={15} />
            </div>
            <input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setFormError('');
              }}
              placeholder="nguyenvana@gmail.com"
              className="w-full pl-10 pr-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-sky-500 focus:bg-white focus:ring-2 focus:ring-sky-100 transition-all"
            />
          </div>
        </div>

        {/* Password */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
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
              placeholder="Tối thiểu 8 ký tự"
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

          {/* Strength Meter */}
          {password && (
            <div className="mt-1.5 flex items-center gap-1.5">
              {[1, 2, 3, 4].map((level) => (
                <div
                  key={level}
                  className={`h-1.5 flex-1 rounded-full transition-all ${
                    strength >= level
                      ? strength <= 2
                        ? 'bg-amber-500'
                        : 'bg-sky-500'
                      : 'bg-slate-100'
                  }`}
                />
              ))}
              <span className="text-[11px] text-slate-400 ml-1">
                {strength <= 1 ? 'Yếu' : strength <= 3 ? 'Khá' : 'Mạnh'}
              </span>
            </div>
          )}
        </div>

        {/* Confirm Password */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Xác nhận mật khẩu <span className="text-rose-500">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <ShieldCheck size={15} />
            </div>
            <input
              type={showPassword ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value);
                setFormError('');
              }}
              placeholder="Nhập lại mật khẩu"
              className="w-full pl-10 pr-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-sky-500 focus:bg-white focus:ring-2 focus:ring-sky-100 transition-all"
            />
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full h-10 bg-sky-600 hover:bg-sky-700 text-white font-semibold text-xs rounded-lg flex items-center justify-center gap-2 transition-all shadow-sm disabled:opacity-50 mt-3"
        >
          {isLoading ? (
            <>
              <Loader2 size={15} className="animate-spin" />
              <span>Đang tạo tài khoản...</span>
            </>
          ) : (
            <>
              <span>Hoàn tất đăng ký</span>
              <ArrowRight size={15} />
            </>
          )}
        </button>
      </form>
    </AuthLayout>
  );
}
