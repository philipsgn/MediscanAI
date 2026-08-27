'use client';

/**
 * PasswordStrengthMeter — Thanh đo độ mạnh mật khẩu theo thời gian thực (Stage 8).
 * Đánh giá dựa trên: độ dài (>=8), chữ hoa/thường, số, và ký tự đặc biệt.
 */

import React from 'react';
import { Check, X } from 'lucide-react';

interface PasswordStrengthMeterProps {
  password: string;
}

export function PasswordStrengthMeter({ password }: PasswordStrengthMeterProps) {
  if (!password) return null;

  const checks = [
    { label: 'Ít nhất 8 ký tự', valid: password.length >= 8 },
    { label: 'Có chữ hoa và chữ thường', valid: /[a-z]/.test(password) && /[A-Z]/.test(password) },
    { label: 'Có chứa chữ số (0-9)', valid: /\d/.test(password) },
    { label: 'Có ký tự đặc biệt (!@#$%...)', valid: /[^a-zA-Z0-9]/.test(password) },
  ];

  const score = checks.filter((c) => c.valid).length;

  const getStrengthLabel = () => {
    if (score <= 1) return { text: 'Yếu', color: 'bg-red-500', textColor: 'text-red-400' };
    if (score <= 3) return { text: 'Trung bình', color: 'bg-amber-500', textColor: 'text-amber-400' };
    return { text: 'Mạnh (Khuyên dùng)', color: 'bg-emerald-500', textColor: 'text-emerald-400' };
  };

  const strength = getStrengthLabel();

  return (
    <div className="space-y-2 mt-2 pt-1 animate-in fade-in duration-200">
      {/* Bar Progress */}
      <div className="flex items-center justify-between text-[11px] font-semibold">
        <span className="text-slate-400">Độ mạnh mật khẩu:</span>
        <span className={strength.textColor}>{strength.text}</span>
      </div>

      <div className="grid grid-cols-4 gap-1.5 h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
        {[1, 2, 3, 4].map((step) => (
          <div
            key={step}
            className={`h-full transition-all duration-300 ${
              step <= score ? strength.color : 'bg-transparent'
            }`}
          />
        ))}
      </div>

      {/* Criteria checklist */}
      <div className="grid grid-cols-2 gap-1.5 pt-1">
        {checks.map((check, idx) => (
          <div key={idx} className="flex items-center gap-1.5 text-[10px]">
            {check.valid ? (
              <Check size={11} className="text-emerald-400 shrink-0" />
            ) : (
              <X size={11} className="text-slate-600 shrink-0" />
            )}
            <span className={check.valid ? 'text-slate-300 font-medium' : 'text-slate-500'}>
              {check.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
