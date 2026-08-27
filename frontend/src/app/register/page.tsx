'use client';

/**
 * Register Page — Màn hình Đăng ký Minimalist Clinical Grade.
 * Form vuông vức (rounded-none), đơn sắc (#0F172A, #334155, #FFFFFF, #E2E8F0).
 * Sau khi đăng ký thành công ➔ Chuyển hướng về /login với thông báo sẵn sàng.
 */

import React, { useState } from 'react';
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
      setFormError('Vui lòng nhập Tên đăng nhập');
      return;
    }
    if (username.length < 3) {
      setFormError('Tên đăng nhập tối thiểu 3 ký tự');
      return;
    }
    if (!email.trim()) {
      setFormError('Vui lòng nhập Địa chỉ Email');
      return;
    }
    if (!password) {
      setFormError('Vui lòng nhập Mật khẩu');
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

      toast.success('Đăng ký tài khoản thành công! Vui lòng đăng nhập để bắt đầu.');
      // Chuyển về /login sau khi đăng ký
      router.replace('/login');
    } catch {
      // Error handled in store
    }
  };

  return (
    <AuthLayout
      title="ĐĂNG KÝ TÀI KHOẢN MỚI"
      subtitle="Khởi tạo định danh tài khoản y tế trên hệ sinh thái Mediscan AI"
      mode="register"
    >
      <form onSubmit={handleSubmit} className="space-y-3.5">
        {/* Error Alert */}
        {(error || formError) && (
          <div className="p-3 border border-rose-300 bg-rose-50 text-rose-800 text-xs font-mono flex items-start gap-2">
            <AlertCircle size={15} className="text-rose-600 shrink-0 mt-0.5" />
            <span>{formError || error}</span>
          </div>
        )}

        {/* Full Name */}
        <div>
          <label className="block text-xs font-mono font-bold text-slate-700 uppercase mb-1">
            Họ và tên (Tùy chọn)
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <User size={14} />
            </div>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="BS. Nguyễn Văn A"
              className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-300 rounded-none text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-slate-900 focus:bg-white transition-colors"
            />
          </div>
        </div>

        {/* Username */}
        <div>
          <label className="block text-xs font-mono font-bold text-slate-700 uppercase mb-1">
            Tên đăng nhập <span className="text-rose-600">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <span className="font-mono text-xs">@</span>
            </div>
            <input
              type="text"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                setFormError('');
              }}
              placeholder="bs_nguyenvana"
              className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-300 rounded-none text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-slate-900 focus:bg-white transition-colors font-mono"
            />
          </div>
        </div>

        {/* Email */}
        <div>
          <label className="block text-xs font-mono font-bold text-slate-700 uppercase mb-1">
            Địa chỉ Email <span className="text-rose-600">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <Mail size={14} />
            </div>
            <input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setFormError('');
              }}
              placeholder="nguyenvana@hospital.vn"
              className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-300 rounded-none text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-slate-900 focus:bg-white transition-colors font-mono"
            />
          </div>
        </div>

        {/* Password */}
        <div>
          <label className="block text-xs font-mono font-bold text-slate-700 uppercase mb-1">
            Mật khẩu bảo mật <span className="text-rose-600">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <Lock size={14} />
            </div>
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setFormError('');
              }}
              placeholder="Tối thiểu 8 ký tự"
              className="w-full pl-9 pr-9 py-2 bg-slate-50 border border-slate-300 rounded-none text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-slate-900 focus:bg-white transition-colors font-mono"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-700"
            >
              {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>

          {/* Minimalist Strength Meter */}
          {password && (
            <div className="mt-1.5 flex items-center gap-1">
              {[1, 2, 3, 4].map((level) => (
                <div
                  key={level}
                  className={`h-1 flex-1 transition-colors ${
                    strength >= level
                      ? strength <= 2
                        ? 'bg-amber-600'
                        : 'bg-emerald-600'
                      : 'bg-slate-200'
                  }`}
                />
              ))}
              <span className="text-[10px] font-mono text-slate-500 ml-1">
                {strength <= 1 ? 'Yếu' : strength <= 3 ? 'Khá' : 'Mạnh'}
              </span>
            </div>
          )}
        </div>

        {/* Confirm Password */}
        <div>
          <label className="block text-xs font-mono font-bold text-slate-700 uppercase mb-1">
            Xác nhận mật khẩu <span className="text-rose-600">*</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <ShieldCheck size={14} />
            </div>
            <input
              type={showPassword ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value);
                setFormError('');
              }}
              placeholder="Nhập lại mật khẩu"
              className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-300 rounded-none text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-slate-900 focus:bg-white transition-colors font-mono"
            />
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full h-10 bg-slate-900 hover:bg-slate-800 text-white font-mono font-bold text-xs uppercase flex items-center justify-center gap-2 rounded-none transition-colors disabled:opacity-50 mt-2"
        >
          {isLoading ? (
            <>
              <Loader2 size={14} className="animate-spin" />
              <span>ĐANG TẠO TÀI KHOẢN...</span>
            </>
          ) : (
            <>
              <span>HOÀN TẤT ĐĂNG KÝ</span>
              <ArrowRight size={14} />
            </>
          )}
        </button>
      </form>
    </AuthLayout>
  );
}
