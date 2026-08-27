'use client';

/**
 * OnboardingWizard — 3-step wizard cho khai báo hồ sơ sức khỏe.
 *
 * Bước 1: Thông tin cơ bản (tuổi bắt buộc, cân nặng/chiều cao/giới tính optional)
 * Bước 2: Bệnh nền (chip select, toggle "không có bệnh nền")
 * Bước 3: Dị ứng thuốc (tag input + quick-select chips)
 *
 * Lưu kết quả vào Zustand userProfileStore + localStorage.
 * Sau hoàn tất → router.push('/scan').
 */

import { useState, useCallback, useRef, KeyboardEvent } from 'react';
import { useRouter } from 'next/navigation';
import {
  Heart, ChevronRight, ChevronLeft, User, Activity, Shield,
  Check, X, AlertCircle, Sparkles,
} from 'lucide-react';
import { useUserProfileStore } from '@/store/userProfileStore';
import { KNOWN_CONDITIONS, KNOWN_ALLERGIES } from '@/constants/conditions';
import { IUserProfile } from '@/types/medication';

// ─── Step indicator ───────────────────────────────────────────────────────────
const STEPS = [
  { label: 'Thông tin cơ bản', icon: User },
  { label: 'Bệnh nền', icon: Activity },
  { label: 'Dị ứng thuốc', icon: Shield },
] as const;

export function OnboardingWizard() {
  const router = useRouter();
  const setProfile = useUserProfileStore((s) => s.setProfile);

  const [step, setStep] = useState(0);

  // ─── Step 1 state ───────────────────────────────────────────────────────────
  const [age, setAge] = useState<string>('');
  const [weightKg, setWeightKg] = useState<string>('');
  const [heightCm, setHeightCm] = useState<string>('');
  const [gender, setGender] = useState<'male' | 'female' | 'other' | ''>('');
  const [ageError, setAgeError] = useState('');

  // ─── Step 2 state ───────────────────────────────────────────────────────────
  const [selectedConditions, setSelectedConditions] = useState<string[]>([]);
  const [noConditions, setNoConditions] = useState(false);

  // ─── Step 3 state ───────────────────────────────────────────────────────────
  const [selectedAllergies, setSelectedAllergies] = useState<string[]>([]);
  const [allergyInput, setAllergyInput] = useState('');
  const [noAllergies, setNoAllergies] = useState(false);
  const allergyInputRef = useRef<HTMLInputElement>(null);

  // ─── Step 1 validation ──────────────────────────────────────────────────────
  const validateStep1 = useCallback((): boolean => {
    const ageNum = parseInt(age, 10);
    if (!age.trim() || isNaN(ageNum) || ageNum <= 0) {
      setAgeError('Vui lòng nhập tuổi hợp lệ (số nguyên > 0)');
      return false;
    }
    if (ageNum > 120) {
      setAgeError('Tuổi không được vượt quá 120');
      return false;
    }
    setAgeError('');
    return true;
  }, [age]);

  // ─── Step 2 handlers ───────────────────────────────────────────────────────
  const toggleCondition = (value: string) => {
    setNoConditions(false);
    setSelectedConditions((prev) =>
      prev.includes(value) ? prev.filter((c) => c !== value) : [...prev, value]
    );
  };

  const handleNoConditions = () => {
    setNoConditions(true);
    setSelectedConditions([]);
  };

  // ─── Step 3 handlers ───────────────────────────────────────────────────────
  const toggleAllergyChip = (value: string) => {
    setNoAllergies(false);
    setSelectedAllergies((prev) =>
      prev.includes(value) ? prev.filter((a) => a !== value) : [...prev, value]
    );
  };

  const addAllergyTag = () => {
    const trimmed = allergyInput.trim();
    if (trimmed && !selectedAllergies.includes(trimmed)) {
      setNoAllergies(false);
      setSelectedAllergies((prev) => [...prev, trimmed]);
    }
    setAllergyInput('');
  };

  const removeAllergyTag = (tag: string) => {
    setSelectedAllergies((prev) => prev.filter((a) => a !== tag));
  };

  const handleAllergyKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addAllergyTag();
    }
  };

  const handleNoAllergies = () => {
    setNoAllergies(true);
    setSelectedAllergies([]);
    setAllergyInput('');
  };

  // ─── Navigation ─────────────────────────────────────────────────────────────
  const goNext = () => {
    if (step === 0 && !validateStep1()) return;
    setStep((s) => Math.min(s + 1, 2));
  };

  const goBack = () => {
    setStep((s) => Math.max(s - 1, 0));
  };

  // ─── Final submit ──────────────────────────────────────────────────────────
  const handleFinish = () => {
    // Re-validate step 1
    const ageNum = parseInt(age, 10);
    if (!age.trim() || isNaN(ageNum) || ageNum <= 0 || ageNum > 120) {
      setStep(0);
      setAgeError('Vui lòng nhập tuổi hợp lệ');
      return;
    }

    const profile: IUserProfile = {
      age: ageNum,
      weightKg: weightKg ? parseFloat(weightKg) || null : null,
      heightCm: heightCm ? parseFloat(heightCm) || null : null,
      gender: gender || null,
      conditions: noConditions ? [] : selectedConditions,
      allergies: noAllergies ? [] : selectedAllergies,
    };

    setProfile(profile);
    router.push('/scan');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/50 flex items-center justify-center p-4 font-[var(--font-inter)]">
      <div className="w-full max-w-xl">

        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 shadow-lg shadow-blue-500/25 mb-4">
            <Sparkles className="text-white" size={32} />
          </div>
          <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">
            Chào Mừng Đến Mediscan AI
          </h1>
          <p className="text-gray-500 text-sm mt-2 max-w-md mx-auto">
            Hãy cho chúng tôi biết một vài thông tin sức khỏe cơ bản để cá nhân hóa cảnh báo tương tác thuốc chính xác nhất.
          </p>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center justify-center gap-2 mb-6">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            const isActive = i === step;
            const isDone = i < step;
            return (
              <div key={i} className="flex items-center gap-2">
                {i > 0 && (
                  <div className={`w-8 h-0.5 rounded-full transition-colors duration-300 ${isDone ? 'bg-blue-500' : 'bg-gray-200'}`} />
                )}
                <div
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold transition-all duration-300 ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                      : isDone
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-gray-100 text-gray-400'
                  }`}
                >
                  {isDone ? <Check size={13} /> : <Icon size={13} />}
                  <span className="hidden sm:inline">{s.label}</span>
                  <span className="sm:hidden">{i + 1}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Card Container */}
        <div className="bg-white rounded-2xl shadow-xl shadow-gray-200/50 border border-gray-100 overflow-hidden">

          {/* ════════════════════════════════════════════════════════════════════
              STEP 1: Thông tin cơ bản
              ════════════════════════════════════════════════════════════════════ */}
          {step === 0 && (
            <div className="p-6 sm:p-8 space-y-5">
              <div>
                <h2 className="text-lg font-extrabold text-gray-900 flex items-center gap-2">
                  <User size={20} className="text-blue-600" />
                  Thông Tin Cơ Bản
                </h2>
                <p className="text-xs text-gray-500 mt-1">
                  Thông tin này giúp hệ thống đối chiếu liều dùng phù hợp với từng độ tuổi.
                </p>
              </div>

              {/* Age - Required */}
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1.5">
                  Tuổi <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  value={age}
                  onChange={(e) => { setAge(e.target.value); setAgeError(''); }}
                  placeholder="Nhập tuổi"
                  min={1}
                  max={120}
                  className={`w-full px-4 py-3 rounded-xl border-2 outline-none text-sm font-medium transition-all ${
                    ageError
                      ? 'border-red-300 bg-red-50/50 focus:border-red-500 focus:ring-2 focus:ring-red-200'
                      : 'border-gray-200 bg-gray-50/50 focus:border-blue-500 focus:ring-2 focus:ring-blue-200'
                  }`}
                />
                {ageError && (
                  <p className="mt-1.5 text-xs text-red-600 font-medium flex items-center gap-1">
                    <AlertCircle size={12} />
                    {ageError}
                  </p>
                )}
              </div>

              {/* Weight & Height - Optional */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1.5">
                    Cân nặng (kg) <span className="text-gray-400 font-normal">— tùy chọn</span>
                  </label>
                  <input
                    type="number"
                    value={weightKg}
                    onChange={(e) => setWeightKg(e.target.value)}
                    placeholder="VD: 65"
                    min={0}
                    max={300}
                    className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 bg-gray-50/50 outline-none text-sm font-medium focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1.5">
                    Chiều cao (cm) <span className="text-gray-400 font-normal">— tùy chọn</span>
                  </label>
                  <input
                    type="number"
                    value={heightCm}
                    onChange={(e) => setHeightCm(e.target.value)}
                    placeholder="VD: 170"
                    min={0}
                    max={250}
                    className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 bg-gray-50/50 outline-none text-sm font-medium focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                  />
                </div>
              </div>

              {/* Gender - Optional */}
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1.5">
                  Giới tính <span className="text-gray-400 font-normal">— tùy chọn</span>
                </label>
                <select
                  value={gender}
                  onChange={(e) => setGender(e.target.value as typeof gender)}
                  className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 bg-gray-50/50 outline-none text-sm font-medium focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all appearance-none"
                >
                  <option value="">Chưa chọn</option>
                  <option value="male">Nam</option>
                  <option value="female">Nữ</option>
                  <option value="other">Khác</option>
                </select>
              </div>
            </div>
          )}

          {/* ════════════════════════════════════════════════════════════════════
              STEP 2: Bệnh nền
              ════════════════════════════════════════════════════════════════════ */}
          {step === 1 && (
            <div className="p-6 sm:p-8 space-y-5">
              <div>
                <h2 className="text-lg font-extrabold text-gray-900 flex items-center gap-2">
                  <Activity size={20} className="text-blue-600" />
                  Tiền Sử Bệnh Nền
                </h2>
                <p className="text-xs text-gray-500 mt-1">
                  Chọn các bệnh lý mà bạn đang mắc hoặc có tiền sử. Thông tin này giúp phát hiện xung đột thuốc — bệnh (Layer 3).
                </p>
              </div>

              {/* Condition Chips */}
              <div className="flex flex-wrap gap-2">
                {KNOWN_CONDITIONS.map((opt) => {
                  const isSelected = selectedConditions.includes(opt.value);
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => toggleCondition(opt.value)}
                      disabled={noConditions}
                      className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all duration-200 border-2 ${
                        isSelected
                          ? opt.hasBackendRule
                            ? 'bg-red-50 text-red-700 border-red-300 shadow-sm shadow-red-100'
                            : 'bg-amber-50 text-amber-700 border-amber-300 shadow-sm shadow-amber-100'
                          : noConditions
                            ? 'bg-gray-50 text-gray-300 border-gray-100 cursor-not-allowed'
                            : 'bg-gray-50 text-gray-600 border-gray-200 hover:border-blue-300 hover:bg-blue-50/50'
                      }`}
                    >
                      {isSelected && <Check size={12} className="inline mr-1 -mt-0.5" />}
                      {opt.label}
                    </button>
                  );
                })}
              </div>

              {/* "No conditions" toggle */}
              <button
                type="button"
                onClick={noConditions ? () => setNoConditions(false) : handleNoConditions}
                className={`w-full py-3 rounded-xl text-xs font-bold transition-all duration-200 border-2 flex items-center justify-center gap-2 ${
                  noConditions
                    ? 'bg-green-50 text-green-700 border-green-300 shadow-sm shadow-green-100'
                    : 'bg-gray-50 text-gray-500 border-gray-200 hover:border-green-300 hover:bg-green-50/30'
                }`}
              >
                {noConditions && <Check size={14} />}
                Tôi không có bệnh nền nào
              </button>
            </div>
          )}

          {/* ════════════════════════════════════════════════════════════════════
              STEP 3: Dị ứng thuốc
              ════════════════════════════════════════════════════════════════════ */}
          {step === 2 && (
            <div className="p-6 sm:p-8 space-y-5">
              <div>
                <h2 className="text-lg font-extrabold text-gray-900 flex items-center gap-2">
                  <Shield size={20} className="text-blue-600" />
                  Dị Ứng Thuốc
                </h2>
                <p className="text-xs text-gray-500 mt-1">
                  Khai báo các loại thuốc/hoạt chất bạn bị dị ứng. Hệ thống sẽ cảnh báo khi phát hiện thuốc liên quan trong tủ thuốc.
                </p>
              </div>

              {/* Quick-select allergy chips */}
              <div>
                <label className="block text-[11px] font-bold text-gray-500 mb-2 uppercase tracking-wider">
                  Dị ứng phổ biến
                </label>
                <div className="flex flex-wrap gap-2">
                  {KNOWN_ALLERGIES.map((opt) => {
                    const isSelected = selectedAllergies.includes(opt.value);
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => toggleAllergyChip(opt.value)}
                        disabled={noAllergies}
                        className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all duration-200 border-2 ${
                          isSelected
                            ? 'bg-amber-50 text-amber-700 border-amber-300 shadow-sm shadow-amber-100'
                            : noAllergies
                              ? 'bg-gray-50 text-gray-300 border-gray-100 cursor-not-allowed'
                              : 'bg-gray-50 text-gray-600 border-gray-200 hover:border-amber-300 hover:bg-amber-50/50'
                        }`}
                      >
                        {isSelected && <Check size={12} className="inline mr-1 -mt-0.5" />}
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Free-form tag input */}
              <div>
                <label className="block text-[11px] font-bold text-gray-500 mb-2 uppercase tracking-wider">
                  Thêm dị ứng khác (nhập tên → nhấn Enter)
                </label>
                <div className={`flex flex-wrap gap-1.5 p-3 rounded-xl border-2 min-h-[48px] transition-all ${
                  noAllergies
                    ? 'bg-gray-50 border-gray-100'
                    : 'bg-white border-gray-200 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-200'
                }`}>
                  {selectedAllergies
                    .filter((a) => !KNOWN_ALLERGIES.some((ka) => ka.value === a))
                    .map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-100 text-amber-800 text-xs font-bold rounded-lg"
                      >
                        {tag}
                        <button
                          type="button"
                          onClick={() => removeAllergyTag(tag)}
                          className="hover:text-red-600 transition-colors"
                        >
                          <X size={12} />
                        </button>
                      </span>
                    ))}
                  <input
                    ref={allergyInputRef}
                    type="text"
                    value={allergyInput}
                    onChange={(e) => setAllergyInput(e.target.value)}
                    onKeyDown={handleAllergyKeyDown}
                    placeholder={noAllergies ? '' : 'VD: Sulfonamide...'}
                    disabled={noAllergies}
                    className="flex-1 min-w-[120px] outline-none text-xs bg-transparent placeholder:text-gray-400 disabled:cursor-not-allowed"
                  />
                </div>
              </div>

              {/* "No allergies" toggle */}
              <button
                type="button"
                onClick={noAllergies ? () => setNoAllergies(false) : handleNoAllergies}
                className={`w-full py-3 rounded-xl text-xs font-bold transition-all duration-200 border-2 flex items-center justify-center gap-2 ${
                  noAllergies
                    ? 'bg-green-50 text-green-700 border-green-300 shadow-sm shadow-green-100'
                    : 'bg-gray-50 text-gray-500 border-gray-200 hover:border-green-300 hover:bg-green-50/30'
                }`}
              >
                {noAllergies && <Check size={14} />}
                Tôi không có dị ứng thuốc nào được biết
              </button>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════════════════
              Footer Navigation
              ═══════════════════════════════════════════════════════════════════ */}
          <div className="px-6 sm:px-8 py-5 bg-gray-50/80 border-t border-gray-100 flex items-center justify-between gap-3">
            {step > 0 ? (
              <button
                type="button"
                onClick={goBack}
                className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-xs font-bold text-gray-600 bg-white border border-gray-200 hover:bg-gray-50 hover:border-gray-300 transition-all"
              >
                <ChevronLeft size={14} />
                Quay lại
              </button>
            ) : (
              <div />
            )}

            {step < 2 ? (
              <button
                type="button"
                onClick={goNext}
                className="inline-flex items-center gap-1.5 px-6 py-2.5 rounded-xl text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-sm shadow-blue-500/20 transition-all active:scale-[0.98]"
              >
                Tiếp theo
                <ChevronRight size={14} />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleFinish}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-extrabold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-md shadow-blue-500/25 transition-all active:scale-[0.98]"
              >
                <Heart size={16} className="fill-current" />
                Hoàn tất, vào Mediscan AI
                <ChevronRight size={14} />
              </button>
            )}
          </div>
        </div>

        {/* Disclaimer notice */}
        <p className="text-center text-[11px] text-gray-400 mt-4 px-4">
          Thông tin sức khỏe của bạn được lưu trữ cục bộ trên trình duyệt này và không bao giờ được gửi đến máy chủ bên ngoài.
        </p>
      </div>
    </div>
  );
}
