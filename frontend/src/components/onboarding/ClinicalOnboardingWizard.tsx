'use client';

/**
 * ClinicalOnboardingWizard — Wizard 4 Bước Khai Báo Hồ Sơ Y Tế Cá Nhân Hóa (Stage 9).
 * Clinical Teal Palette (#0F766E), Soft Ice Blue (#F0FDFA), Deep Slate (#0F172A), rounded-2xl.
 * Live BMI Calculator, Condition/Allergy Chips, Medical Privacy Pledge, Keyboard Navigation.
 */

import React, { useState, useEffect, useCallback, useRef, KeyboardEvent } from 'react';
import { useRouter } from 'next/navigation';
import {
  User, Activity, Shield, ShieldCheck, Heart, ChevronRight, ChevronLeft,
  Check, X, AlertCircle, Sparkles, Lock, Scale, Calendar, RefreshCw, Loader2
} from 'lucide-react';
import { useUserProfileStore } from '@/store/userProfileStore';
import { KNOWN_CONDITIONS, KNOWN_ALLERGIES } from '@/constants/conditions';
import { IUserProfile } from '@/types/medication';
import { toast } from '@/components/common/Toast';

// ─── Step Indicator ─────────────────────────────────────────────────────────
const STEPS = [
  { step: 1, label: 'Sinh Trắc Học', icon: User },
  { step: 2, label: 'Bệnh Nền', icon: Activity },
  { step: 3, label: 'Dị Ứng Thuốc', icon: Shield },
  { step: 4, label: 'Cam Kết & Xác Nhận', icon: ShieldCheck },
] as const;

export function ClinicalOnboardingWizard() {
  const router = useRouter();
  const { setProfile, fetchProfile, profile: existingProfile, isLoading } = useUserProfileStore();

  const [step, setStep] = useState(1);

  // ─── Step 1 State: Biometrics ──────────────────────────────────────────────
  const [age, setAge] = useState<string>('30');
  const [birthYear, setBirthYear] = useState<string>('');
  const [gender, setGender] = useState<'male' | 'female' | 'other' | ''>('male');
  const [weightKg, setWeightKg] = useState<string>('');
  const [heightCm, setHeightCm] = useState<string>('');
  const [ageError, setAgeError] = useState('');

  // ─── Step 2 State: Medical Conditions ──────────────────────────────────────
  const [selectedConditions, setSelectedConditions] = useState<string[]>([]);
  const [customConditionInput, setCustomConditionInput] = useState('');
  const [noConditions, setNoConditions] = useState(false);

  // ─── Step 3 State: Drug Allergies ───────────────────────────────────────────
  const [selectedAllergies, setSelectedAllergies] = useState<string[]>([]);
  const [customAllergyInput, setCustomAllergyInput] = useState('');
  const [noAllergies, setNoAllergies] = useState(false);

  // ─── Load Existing Profile ──────────────────────────────────────────────────
  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  useEffect(() => {
    if (existingProfile) {
      if (existingProfile.age) setAge(String(existingProfile.age));
      if (existingProfile.birthYear) setBirthYear(String(existingProfile.birthYear));
      if (existingProfile.gender) setGender(existingProfile.gender);
      if (existingProfile.weightKg) setWeightKg(String(existingProfile.weightKg));
      if (existingProfile.heightCm) setHeightCm(String(existingProfile.heightCm));
      if (existingProfile.conditions) setSelectedConditions(existingProfile.conditions);
      if (existingProfile.allergies) setSelectedAllergies(existingProfile.allergies);
    }
  }, [existingProfile]);

  // ─── Live BMI Calculation ──────────────────────────────────────────────────
  const calculateBmi = useCallback((): { bmi: number | null; label: string; color: string } => {
    const w = parseFloat(weightKg);
    const h = parseFloat(heightCm);
    if (!w || !h || h <= 0 || w <= 0) {
      return { bmi: null, label: 'Chưa đủ thông tin', color: 'text-slate-400' };
    }
    const heightM = h / 100.0;
    const bmiVal = Math.round((w / (heightM * heightM)) * 10) / 10;

    // Chuẩn BMI Châu Á (IDI/WPRO)
    if (bmiVal < 18.5) {
      return { bmi: bmiVal, label: 'Nhẹ cân (< 18.5)', color: 'text-sky-400 bg-sky-950/40 border-sky-800' };
    } else if (bmiVal <= 22.9) {
      return { bmi: bmiVal, label: 'Bình thường (18.5 - 22.9)', color: 'text-emerald-400 bg-emerald-950/40 border-emerald-800' };
    } else if (bmiVal <= 24.9) {
      return { bmi: bmiVal, label: 'Thừa cân (23.0 - 24.9)', color: 'text-amber-400 bg-amber-950/40 border-amber-800' };
    } else {
      return { bmi: bmiVal, label: 'Béo phì (≥ 25.0)', color: 'text-rose-400 bg-rose-950/40 border-rose-800' };
    }
  }, [weightKg, heightCm]);

  const bmiInfo = calculateBmi();

  // ─── Birth Year Sync ────────────────────────────────────────────────────────
  const handleBirthYearChange = (yearStr: string) => {
    setBirthYear(yearStr);
    const yr = parseInt(yearStr, 10);
    const currentYear = new Date().getFullYear();
    if (yr >= 1900 && yr <= currentYear) {
      const computedAge = currentYear - yr;
      setAge(String(computedAge));
      setAgeError('');
    }
  };

  // ─── Validation ─────────────────────────────────────────────────────────────
  const validateStep1 = (): boolean => {
    const ageNum = parseInt(age, 10);
    if (!age.trim() || isNaN(ageNum) || ageNum <= 0 || ageNum > 120) {
      setAgeError('Vui lòng nhập tuổi hợp lệ (1 - 120)');
      return false;
    }
    setAgeError('');
    return true;
  };

  // ─── Handlers ───────────────────────────────────────────────────────────────
  const toggleCondition = (value: string) => {
    setNoConditions(false);
    setSelectedConditions((prev) =>
      prev.includes(value) ? prev.filter((c) => c !== value) : [...prev, value]
    );
  };

  const addCustomCondition = () => {
    const trimmed = customConditionInput.trim();
    if (trimmed && !selectedConditions.includes(trimmed)) {
      setNoConditions(false);
      setSelectedConditions((prev) => [...prev, trimmed]);
    }
    setCustomConditionInput('');
  };

  const toggleAllergy = (value: string) => {
    setNoAllergies(false);
    setSelectedAllergies((prev) =>
      prev.includes(value) ? prev.filter((a) => a !== value) : [...prev, value]
    );
  };

  const addCustomAllergy = () => {
    const trimmed = customAllergyInput.trim();
    if (trimmed && !selectedAllergies.includes(trimmed)) {
      setNoAllergies(false);
      setSelectedAllergies((prev) => [...prev, trimmed]);
    }
    setCustomAllergyInput('');
  };

  const goNext = () => {
    if (step === 1 && !validateStep1()) return;
    setStep((s) => Math.min(s + 1, 4));
  };

  const goBack = () => {
    setStep((s) => Math.max(s - 1, 1));
  };

  const handleGlobalKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' && e.target instanceof HTMLInputElement === false) {
      e.preventDefault();
      if (step < 4) goNext();
      else handleFinish();
    }
  };

  const handleFinish = async () => {
    if (!validateStep1()) {
      setStep(1);
      return;
    }

    const profileData: IUserProfile = {
      age: parseInt(age, 10),
      birthYear: birthYear ? parseInt(birthYear, 10) : null,
      gender: gender || null,
      weightKg: weightKg ? parseFloat(weightKg) : null,
      heightCm: heightCm ? parseFloat(heightCm) : null,
      bmi: bmiInfo.bmi,
      conditions: noConditions ? [] : selectedConditions,
      allergies: noAllergies ? [] : selectedAllergies,
    };

    try {
      await setProfile(profileData);
      toast.success('Hồ sơ Y tế đã được cập nhật thành công!');
      router.push('/scan');
    } catch {
      toast.error('Có lỗi khi lưu hồ sơ. Đã lưu bản ghi tạm thời.');
      router.push('/scan');
    }
  };

  return (
    <div
      onKeyDown={handleGlobalKeyDown}
      className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center py-10 px-4 font-[var(--font-inter)] selection:bg-teal-500 selection:text-white"
    >
      <div className="w-full max-w-2xl mx-auto space-y-6">

        {/* ── Header Branding & Skip ── */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-teal-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-teal-900/40">
              <Activity size={22} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-black text-white tracking-tight flex items-center gap-1.5">
                Mediscan<span className="text-teal-400">AI</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-teal-950 text-teal-300 border border-teal-800/60 font-semibold uppercase tracking-wider">
                  Clinical Profile
                </span>
              </h1>
              <p className="text-xs text-slate-400">Cá nhân hóa hồ sơ sức khỏe & an toàn thuốc</p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => router.push('/scan')}
            className="text-xs text-slate-400 hover:text-teal-300 font-semibold underline underline-offset-4 transition-colors"
          >
            Bỏ qua lúc này →
          </button>
        </div>

        {/* ── Step Indicator Bar ── */}
        <div className="grid grid-cols-4 gap-2 bg-slate-900/90 p-2 rounded-2xl border border-slate-800 shadow-xl backdrop-blur-md">
          {STEPS.map((s) => {
            const Icon = s.icon;
            const isActive = s.step === step;
            const isDone = s.step < step;
            return (
              <button
                key={s.step}
                type="button"
                onClick={() => {
                  if (isDone || s.step === step) setStep(s.step);
                }}
                className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-xs font-bold transition-all duration-300 ${
                  isActive
                    ? 'bg-gradient-to-r from-teal-600 to-emerald-600 text-white shadow-lg shadow-teal-900/30'
                    : isDone
                      ? 'bg-teal-950/60 text-teal-300 border border-teal-900/40'
                      : 'bg-transparent text-slate-500 cursor-not-allowed'
                }`}
              >
                {isDone ? <Check size={14} className="text-teal-300" /> : <Icon size={14} />}
                <span className="hidden sm:inline">{s.label}</span>
                <span className="sm:hidden">{s.step}</span>
              </button>
            );
          })}
        </div>

        {/* ── Main Step Card Container ── */}
        <div className="bg-slate-900/90 rounded-2xl border border-slate-800/90 p-6 sm:p-8 shadow-2xl backdrop-blur-xl space-y-6">

          {/* ════════════════════════════════════════════════════════════════════
              STEP 1: Sinh Trắc Học Cơ Bản
              ════════════════════════════════════════════════════════════════════ */}
          {step === 1 && (
            <div className="space-y-6 animate-in fade-in duration-300">
              <div className="border-b border-slate-800 pb-4">
                <h2 className="text-xl font-extrabold text-white flex items-center gap-2">
                  <User size={22} className="text-teal-400" />
                  Bước 1: Sinh Trắc Học Cơ Bản
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Thông tin tuổi và thể trạng giúp đối chiếu chuẩn xác liều dùng khuyến cáo (Layer 4 Dosage Check).
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Age Input */}
                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-1.5">
                    Tuổi hiện tại <span className="text-teal-400">*</span>
                  </label>
                  <input
                    type="number"
                    value={age}
                    onChange={(e) => {
                      setAge(e.target.value);
                      setAgeError('');
                    }}
                    placeholder="VD: 30"
                    min={1}
                    max={120}
                    className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm font-semibold text-white outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all"
                  />
                  {ageError && <p className="text-[11px] text-rose-400 mt-1 font-medium">{ageError}</p>}
                </div>

                {/* Birth Year Input */}
                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-1.5">
                    Năm sinh <span className="text-slate-500 font-normal">— Tự động tính tuổi</span>
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      value={birthYear}
                      onChange={(e) => handleBirthYearChange(e.target.value)}
                      placeholder="VD: 1995"
                      min={1900}
                      max={2026}
                      className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm font-semibold text-white outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all"
                    />
                    <Calendar size={16} className="absolute right-3.5 top-3 text-slate-500" />
                  </div>
                </div>
              </div>

              {/* Gender Selection */}
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-2">Giới tính sinh học</label>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { val: 'male', label: 'Nam' },
                    { val: 'female', label: 'Nữ' },
                    { val: 'other', label: 'Khác' },
                  ].map((item) => (
                    <button
                      key={item.val}
                      type="button"
                      onClick={() => setGender(item.val as typeof gender)}
                      className={`py-2.5 px-3 rounded-xl text-xs font-bold border transition-all ${
                        gender === item.val
                          ? 'bg-teal-950 text-teal-300 border-teal-500 shadow-md shadow-teal-950'
                          : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Height & Weight Inputs */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-1.5">Cân nặng (kg)</label>
                  <input
                    type="number"
                    value={weightKg}
                    onChange={(e) => setWeightKg(e.target.value)}
                    placeholder="VD: 65.5"
                    step="0.5"
                    min={1}
                    max={300}
                    className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm font-semibold text-white outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-300 mb-1.5">Chiều cao (cm)</label>
                  <input
                    type="number"
                    value={heightCm}
                    onChange={(e) => setHeightCm(e.target.value)}
                    placeholder="VD: 170"
                    min={40}
                    max={250}
                    className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm font-semibold text-white outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all"
                  />
                </div>
              </div>

              {/* Live BMI Calculator Card */}
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-teal-950 text-teal-400 border border-teal-800/60">
                    <Scale size={20} />
                  </div>
                  <div>
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                      Chỉ số BMI (Tự động tính)
                    </span>
                    <span className="text-lg font-black text-white">
                      {bmiInfo.bmi ? `${bmiInfo.bmi} kg/m²` : '--'}
                    </span>
                  </div>
                </div>

                <div className={`px-3 py-1.5 rounded-lg border text-xs font-extrabold ${bmiInfo.color}`}>
                  {bmiInfo.label}
                </div>
              </div>
            </div>
          )}

          {/* ════════════════════════════════════════════════════════════════════
              STEP 2: Tiền Sử Bệnh Nền
              ════════════════════════════════════════════════════════════════════ */}
          {step === 2 && (
            <div className="space-y-6 animate-in fade-in duration-300">
              <div className="border-b border-slate-800 pb-4">
                <h2 className="text-xl font-extrabold text-white flex items-center gap-2">
                  <Activity size={22} className="text-teal-400" />
                  Bước 2: Tiền Sử Bệnh Nền
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Các bệnh lý mạn tính giúp phát hiện xung đột Thuốc - Bệnh nền (Layer 3 Drug-Condition).
                </p>
              </div>

              {/* Quick Select Chips */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                {KNOWN_CONDITIONS.map((opt) => {
                  const isSelected = selectedConditions.includes(opt.value);
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => toggleCondition(opt.value)}
                      disabled={noConditions}
                      className={`p-3 rounded-xl text-xs font-bold border text-left transition-all flex flex-col justify-between h-20 ${
                        isSelected
                          ? 'bg-teal-950 text-teal-200 border-teal-500 shadow-md shadow-teal-950'
                          : noConditions
                            ? 'bg-slate-950/40 text-slate-600 border-slate-900 cursor-not-allowed'
                            : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex justify-between items-center w-full">
                        <Activity size={14} className={isSelected ? 'text-teal-400' : 'text-slate-600'} />
                        {isSelected && <Check size={14} className="text-teal-400" />}
                      </div>
                      <span className="truncate font-semibold">{opt.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* Custom Condition Input */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-slate-300">Thêm bệnh nền khác</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={customConditionInput}
                    onChange={(e) => setCustomConditionInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addCustomCondition();
                      }
                    }}
                    placeholder="VD: Rối loạn mỡ máu..."
                    disabled={noConditions}
                    className="flex-1 px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 outline-none focus:border-teal-500 transition-all"
                  />
                  <button
                    type="button"
                    onClick={addCustomCondition}
                    disabled={noConditions || !customConditionInput.trim()}
                    className="px-4 py-2.5 rounded-xl bg-teal-800/80 hover:bg-teal-700 text-white font-bold text-xs disabled:opacity-40"
                  >
                    Thêm
                  </button>
                </div>
              </div>

              {/* Selected List Chips */}
              {selectedConditions.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-1">
                  {selectedConditions.map((c) => (
                    <span
                      key={c}
                      className="px-3 py-1 rounded-lg bg-teal-950 text-teal-300 border border-teal-800 text-xs font-bold flex items-center gap-1.5"
                    >
                      {c}
                      <button
                        type="button"
                        onClick={() => setSelectedConditions((prev) => prev.filter((x) => x !== c))}
                        className="hover:text-rose-400"
                      >
                        <X size={13} />
                      </button>
                    </span>
                  ))}
                </div>
              )}

              {/* Toggle No Conditions */}
              <button
                type="button"
                onClick={() => {
                  setNoConditions(!noConditions);
                  if (!noConditions) setSelectedConditions([]);
                }}
                className={`w-full py-3 px-4 rounded-xl border text-xs font-bold flex items-center justify-center gap-2 transition-all ${
                  noConditions
                    ? 'bg-emerald-950/60 text-emerald-300 border-emerald-700'
                    : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                }`}
              >
                {noConditions && <Check size={15} />}
                <span>Tôi không có bệnh nền nào được chẩn đoán</span>
              </button>
            </div>
          )}

          {/* ════════════════════════════════════════════════════════════════════
              STEP 3: Dị Ứng Thuốc
              ════════════════════════════════════════════════════════════════════ */}
          {step === 3 && (
            <div className="space-y-6 animate-in fade-in duration-300">
              <div className="border-b border-slate-800 pb-4">
                <h2 className="text-xl font-extrabold text-white flex items-center gap-2">
                  <Shield size={22} className="text-teal-400" />
                  Bước 3: Dị Ứng Thuốc & Hoạt Chất
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Cảnh báo tức thì nếu phát hiện hoạt chất gây dị ứng có trong đơn thuốc.
                </p>
              </div>

              {/* Quick Select Allergy Chips */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                {KNOWN_ALLERGIES.map((opt) => {
                  const isSelected = selectedAllergies.includes(opt.value);
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => toggleAllergy(opt.value)}
                      disabled={noAllergies}
                      className={`p-3 rounded-xl text-xs font-bold border text-left transition-all flex items-center justify-between ${
                        isSelected
                          ? 'bg-amber-950 text-amber-200 border-amber-600 shadow-md shadow-amber-950'
                          : noAllergies
                            ? 'bg-slate-950/40 text-slate-600 border-slate-900 cursor-not-allowed'
                            : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <span>{opt.label}</span>
                      {isSelected && <Check size={14} className="text-amber-400 shrink-0" />}
                    </button>
                  );
                })}
              </div>

              {/* Custom Allergy Input */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-slate-300">Thêm dị ứng hoạt chất khác</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={customAllergyInput}
                    onChange={(e) => setCustomAllergyInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addCustomAllergy();
                      }
                    }}
                    placeholder="VD: Ciprofloxacin, Paracetamol..."
                    disabled={noAllergies}
                    className="flex-1 px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 outline-none focus:border-teal-500 transition-all"
                  />
                  <button
                    type="button"
                    onClick={addCustomAllergy}
                    disabled={noAllergies || !customAllergyInput.trim()}
                    className="px-4 py-2.5 rounded-xl bg-amber-800/80 hover:bg-amber-700 text-white font-bold text-xs disabled:opacity-40"
                  >
                    Thêm
                  </button>
                </div>
              </div>

              {/* Selected List Chips */}
              {selectedAllergies.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-1">
                  {selectedAllergies.map((a) => (
                    <span
                      key={a}
                      className="px-3 py-1 rounded-lg bg-amber-950 text-amber-300 border border-amber-800 text-xs font-bold flex items-center gap-1.5"
                    >
                      {a}
                      <button
                        type="button"
                        onClick={() => setSelectedAllergies((prev) => prev.filter((x) => x !== a))}
                        className="hover:text-rose-400"
                      >
                        <X size={13} />
                      </button>
                    </span>
                  ))}
                </div>
              )}

              {/* Toggle No Allergies */}
              <button
                type="button"
                onClick={() => {
                  setNoAllergies(!noAllergies);
                  if (!noAllergies) setSelectedAllergies([]);
                }}
                className={`w-full py-3 px-4 rounded-xl border text-xs font-bold flex items-center justify-center gap-2 transition-all ${
                  noAllergies
                    ? 'bg-emerald-950/60 text-emerald-300 border-emerald-700'
                    : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                }`}
              >
                {noAllergies && <Check size={15} />}
                <span>Tôi không có dị ứng thuốc nào được biết</span>
              </button>
            </div>
          )}

          {/* ════════════════════════════════════════════════════════════════════
              STEP 4: Cam Kết Bảo Mật & Xác Nhận
              ════════════════════════════════════════════════════════════════════ */}
          {step === 4 && (
            <div className="space-y-6 animate-in fade-in duration-300">
              <div className="border-b border-slate-800 pb-4">
                <h2 className="text-xl font-extrabold text-white flex items-center gap-2">
                  <ShieldCheck size={22} className="text-teal-400" />
                  Bước 4: Tổng Kết Hồ Sơ & Cam Kết Bảo Mật
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Kiểm tra lại toàn bộ thông tin đã khai báo trước khi hoàn tất.
                </p>
              </div>

              {/* Profile Summary Card */}
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 text-xs">
                <div className="grid grid-cols-2 gap-2 border-b border-slate-800/80 pb-3">
                  <div>
                    <span className="text-slate-500 font-medium block">Tuổi & Thể trạng:</span>
                    <span className="font-bold text-white">
                      {age} tuổi ({gender === 'male' ? 'Nam' : gender === 'female' ? 'Nữ' : 'Khác'}) — {weightKg || '--'}kg, {heightCm || '--'}cm
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 font-medium block">Chỉ số BMI:</span>
                    <span className="font-bold text-teal-400">
                      {bmiInfo.bmi ? `${bmiInfo.bmi} (${bmiInfo.label})` : 'Chưa tính'}
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-slate-500 font-medium block mb-1">Tiền sử bệnh nền:</span>
                  {selectedConditions.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {selectedConditions.map((c) => (
                        <span key={c} className="px-2.5 py-0.5 rounded bg-teal-950 text-teal-300 border border-teal-800 font-semibold">
                          {c}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-slate-400 font-semibold">Không có bệnh nền được khai báo</span>
                  )}
                </div>

                <div>
                  <span className="text-slate-500 font-medium block mb-1">Dị ứng thuốc:</span>
                  {selectedAllergies.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {selectedAllergies.map((a) => (
                        <span key={a} className="px-2.5 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 font-semibold">
                          {a}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-slate-400 font-semibold">Không có dị ứng thuốc được khai báo</span>
                  )}
                </div>
              </div>

              {/* Medical Privacy Pledge Banner */}
              <div className="p-4 rounded-xl bg-gradient-to-r from-teal-950/80 to-slate-950 border border-teal-800/60 space-y-2">
                <div className="flex items-center gap-2 text-teal-300 font-bold text-xs">
                  <Lock size={15} />
                  <span>CAM KẾT BẢO MẬT DỮ LIỆU Y TẾ (Medical Privacy Pledge)</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Thông tin sức khỏe cá nhân của bạn được mã hóa an toàn 256-bit SSL và chỉ sử dụng cho mục đích 
                  đối chiếu tương tác thuốc. Mediscan AI tuyệt đối không chia sẻ dữ liệu y tế cho bên thứ ba.
                </p>
              </div>
            </div>
          )}

          {/* ════════════════════════════════════════════════════════════════════
              Card Navigation Buttons
              ════════════════════════════════════════════════════════════════════ */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-800">
            {step > 1 ? (
              <button
                type="button"
                onClick={goBack}
                className="px-4 py-2.5 rounded-xl border border-slate-800 bg-slate-950 hover:bg-slate-900 text-slate-300 font-bold text-xs flex items-center gap-1.5 transition-all"
              >
                <ChevronLeft size={16} />
                Quay lại
              </button>
            ) : (
              <div />
            )}

            {step < 4 ? (
              <button
                type="button"
                onClick={goNext}
                className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-teal-950 transition-all active:scale-[0.99]"
              >
                <span>Tiếp tục (Nhấn Enter)</span>
                <ChevronRight size={16} />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleFinish}
                disabled={isLoading}
                className="px-6 py-3 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white font-extrabold text-sm flex items-center gap-2 shadow-xl shadow-teal-900/40 transition-all active:scale-[0.99] disabled:opacity-50"
              >
                {isLoading ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    <span>Đang Lưu Hồ Sơ...</span>
                  </>
                ) : (
                  <>
                    <Heart size={18} className="fill-current text-rose-300" />
                    <span>HOÀN TẤT & VÀO MEDISCAN AI</span>
                    <ChevronRight size={16} />
                  </>
                )}
              </button>
            )}
          </div>

        </div>

      </div>
    </div>
  );
}
