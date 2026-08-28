'use client';

/**
 * ClinicalOnboardingWizard — Khai Báo Hồ Sơ Y Tế (Material 3 Clinical Design System).
 * Rebranding: MediScan.
 * 4 Bước: Cơ bản ➔ Bệnh nền ➔ Dị ứng ➔ Hoàn tất (bỏ số thứ tự).
 */

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowRight, ArrowLeft, Check, ShieldCheck,
  Scale, Heart, ShieldAlert, FileCheck, CheckCircle2
} from 'lucide-react';
import { useUserProfileStore } from '@/store/userProfileStore';
import { useAuthStore } from '@/store/authStore';
import { toast } from '@/components/common/Toast';

const KNOWN_CONDITIONS = [
  { id: 'hypertension', label: 'Cao huyết áp', category: 'Tim mạch' },
  { id: 'diabetes_type_2', label: 'Đái tháo đường Type 2', category: 'Nội tiết' },
  { id: 'peptic_ulcer', label: 'Viêm loét dạ dày / GERD', category: 'Tiêu hóa' },
  { id: 'chronic_kidney_disease', label: 'Suy thận mạn', category: 'Thận - Tiết niệu' },
  { id: 'liver_cirrhosis', label: 'Suy gan / Xơ gan', category: 'Gan mật' },
  { id: 'asthma', label: 'Hen suyễn / COPD', category: 'Hô hấp' },
  { id: 'gout', label: 'Bệnh Gout', category: 'Khớp' },
  { id: 'hypothyroidism', label: 'Suy giáp', category: 'Nội tiết' },
];

const KNOWN_ALLERGIES = [
  { id: 'penicillin', label: 'Penicillin / Amoxicillin', category: 'Kháng sinh Beta-lactam' },
  { id: 'cephalosporin', label: 'Cephalosporins (Cefalexin, Cefixime)', category: 'Kháng sinh' },
  { id: 'aspirin', label: 'Aspirin / Salicylates', category: 'Giảm đau NSAID' },
  { id: 'ibuprofen', label: 'Ibuprofen / Naproxen', category: 'Giảm đau NSAID' },
  { id: 'sulfonamides', label: 'Kháng sinh Sulfonamide (Bactrim)', category: 'Kháng sinh' },
  { id: 'paracetamol', label: 'Paracetamol / Acetaminophen', category: 'Hạ sốt - Giảm đau' },
];

export function ClinicalOnboardingWizard() {
  const router = useRouter();
  const { profile, setProfile } = useUserProfileStore();

  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);

  // Form State
  const [age, setAge] = useState<number | ''>(profile?.age ?? '');
  const [birthYear, setBirthYear] = useState<number | ''>(
    profile?.birthYear ?? (profile?.age ? new Date().getFullYear() - profile.age : '')
  );
  const [gender, setGender] = useState<'male' | 'female' | 'other'>(profile?.gender ?? 'male');
  const [isPregnant, setIsPregnant] = useState<boolean>(profile?.isPregnant ?? false);
  const [isBreastfeeding, setIsBreastfeeding] = useState<boolean>(profile?.isBreastfeeding ?? false);
  const [weightKg, setWeightKg] = useState<number | ''>(profile?.weightKg ?? '');
  const [heightCm, setHeightCm] = useState<number | ''>(profile?.heightCm ?? '');

  const [conditions, setConditions] = useState<string[]>(profile?.conditions ?? []);
  const [allergies, setAllergies] = useState<string[]>(profile?.allergies ?? []);
  const [hasNoConditions, setHasNoConditions] = useState<boolean>(
    profile?.conditions ? profile.conditions.length === 0 : false
  );
  const [hasNoAllergies, setHasNoAllergies] = useState<boolean>(
    profile?.allergies ? profile.allergies.length === 0 : false
  );

  const [isSubmitting, setIsSubmitting] = useState(false);

  // Tính BMI tự động
  const calculateBmi = (): { bmi: number; label: string; color: string } | null => {
    if (typeof weightKg === 'number' && typeof heightCm === 'number' && heightCm > 0 && weightKg > 0) {
      const heightM = heightCm / 100;
      const bmiVal = parseFloat((weightKg / (heightM * heightM)).toFixed(1));
      let label = 'Bình thường';
      let color = 'text-emerald-700 bg-emerald-50 border-emerald-200';
      if (bmiVal < 18.5) {
        label = 'Nhẹ cân';
        color = 'text-sky-700 bg-sky-50 border-sky-200';
      } else if (bmiVal >= 23 && bmiVal < 25) {
        label = 'Thừa cân';
        color = 'text-amber-700 bg-amber-50 border-amber-200';
      } else if (bmiVal >= 25) {
        label = 'Béo phì';
        color = 'text-rose-700 bg-rose-50 border-rose-200';
      }
      return { bmi: bmiVal, label, color };
    }
    return null;
  };

  const bmiInfo = calculateBmi();

  const handleAgeChange = (val: string) => {
    const num = parseInt(val, 10);
    if (!isNaN(num)) {
      setAge(num);
      setBirthYear(new Date().getFullYear() - num);
    } else {
      setAge('');
    }
  };

  const toggleCondition = (id: string) => {
    setHasNoConditions(false);
    setConditions((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  };

  const toggleAllergy = (id: string) => {
    setHasNoAllergies(false);
    setAllergies((prev) =>
      prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id]
    );
  };

  const isBasicDone =
    typeof age === 'number' &&
    age > 0 &&
    (gender === 'male' || gender === 'female' || gender === 'other') &&
    typeof weightKg === 'number' &&
    weightKg > 0 &&
    typeof heightCm === 'number' &&
    heightCm > 0;

  const isConditionsDone = conditions.length > 0 || hasNoConditions === true;
  const isAllergiesDone = allergies.length > 0 || hasNoAllergies === true;
  const isCompleteUnlocked = isBasicDone && isConditionsDone && isAllergiesDone;

  const isStepDone = (num: number) => {
    if (num === 1) return isBasicDone;
    if (num === 2) return isConditionsDone;
    if (num === 3) return isAllergiesDone;
    return false;
  };

  const handleNext = () => {
    if (step === 1) {
      if (!age || age <= 0 || age > 130) {
        toast.error('Vui lòng nhập độ tuổi hợp lệ (1 - 130 tuổi)');
        return;
      }
      setStep(2);
    } else if (step === 2) {
      setStep(3);
    } else if (step === 3) {
      if (isCompleteUnlocked) {
        setStep(4);
      } else {
        toast.error('Vui lòng hoàn thành 3 mục trước để mở khóa bước Hoàn tất');
      }
    }
  };

  const handleComplete = async () => {
    setIsSubmitting(true);
    try {
      const finalAge = typeof age === 'number' ? age : 30;
      const finalBirthYear = typeof birthYear === 'number' ? birthYear : new Date().getFullYear() - finalAge;

      await setProfile({
        age: finalAge,
        birthYear: finalBirthYear,
        gender,
        isPregnant: gender === 'female' ? isPregnant : false,
        isBreastfeeding: gender === 'female' ? isBreastfeeding : false,
        weightKg: typeof weightKg === 'number' ? weightKg : undefined,
        heightCm: typeof heightCm === 'number' ? heightCm : undefined,
        bmi: bmiInfo?.bmi,
        conditions: hasNoConditions ? [] : conditions,
        allergies: hasNoAllergies ? [] : allergies,
      });

      useAuthStore.getState().updateUser({ isProfileCompleted: true });

      toast.success('Hồ sơ y tế đã được thiết lập thành công!');
      router.replace('/cabinet');
    } catch {
      useAuthStore.getState().updateUser({ isProfileCompleted: true });
      toast.success('Đã lưu hồ sơ y tế cục bộ!');
      router.replace('/cabinet');
    } finally {
      setIsSubmitting(false);
    }
  };

  const stepsList = [
    { num: 1, label: 'Cơ bản' },
    { num: 2, label: 'Bệnh nền' },
    { num: 3, label: 'Dị ứng' },
    { num: 4, label: 'Hoàn tất' },
  ];

  return (
    <div className="w-full max-w-3xl mx-auto p-4 sm:p-6 space-y-6">
      
      {/* ── Top Wizard Progress Indicator (Stepper) ── */}
      <div className="bg-surface-container-lowest rounded-xl shadow-ambient p-2 flex gap-2">
        {stepsList.map((s) => {
          const isCurrent = step === s.num;
          const isDone = isStepDone(s.num);
          const isLocked = s.num === 4 && !isCompleteUnlocked;
          
          return (
            <button
              key={s.num}
              type="button"
              onClick={() => {
                if (s.num <= 3) {
                  setStep(s.num as 1 | 2 | 3 | 4);
                } else {
                  if (isCompleteUnlocked) {
                    setStep(4);
                  } else {
                    toast.error('Vui lòng hoàn thành 3 mục trước để mở khóa bước Hoàn tất');
                  }
                }
              }}
              className={`flex-1 py-2 px-4 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                isCurrent
                  ? 'bg-primary text-on-primary shadow-sm'
                  : isLocked
                  ? 'bg-surface-container text-on-surface opacity-40 cursor-not-allowed'
                  : 'bg-surface-container text-on-surface'
              }`}
            >
              <Check
                size={14}
                className={`shrink-0 ${
                  isCurrent
                    ? 'text-on-primary'
                    : isDone
                    ? 'text-primary font-bold'
                    : 'opacity-50'
                }`}
              />
              <span className={isCurrent ? 'truncate' : 'truncate opacity-70'}>
                {s.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* ── Main Step Content Card ── */}
      <div className="bg-surface-container-lowest rounded-xl shadow-ambient p-6 md:p-8 space-y-6">

        {/* ── STEP 1: Sinh trắc học ── */}
        {step === 1 && (
          <div className="space-y-6">
            <div className="border-b border-outline-variant pb-3">
              <h2 className="text-xl md:text-2xl text-primary font-semibold flex items-center gap-2">
                <Scale size={20} className="text-primary" />
                Thông tin cơ bản
              </h2>
              <p className="text-xs text-on-surface-variant mt-1">
                Dùng để tính toán liều dùng an toàn và các cảnh báo y khoa theo độ tuổi.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-on-surface mb-1.5">
                  Tuổi hiện tại <span className="text-error">*</span>
                </label>
                <input
                  type="number"
                  min="1"
                  max="125"
                  value={age}
                  onChange={(e) => handleAgeChange(e.target.value)}
                  placeholder="35"
                  className="w-full border border-outline-variant rounded-lg p-3 bg-white text-xs text-on-surface outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all font-sans"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-on-surface mb-1.5">
                  Giới tính sinh học
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: 'male', label: 'Nam' },
                    { id: 'female', label: 'Nữ' },
                    { id: 'other', label: 'Khác' },
                  ].map((g) => (
                    <button
                      key={g.id}
                      type="button"
                      onClick={() => setGender(g.id as typeof gender)}
                      className={`py-3 text-xs font-semibold rounded-lg transition-all border ${
                        gender === g.id
                          ? 'bg-primary text-on-primary border-primary shadow-sm'
                          : 'bg-white border-outline-variant text-on-surface-variant hover:bg-surface-container'
                      }`}
                    >
                      {g.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-on-surface mb-1.5">
                  Cân nặng (kg)
                </label>
                <input
                  type="number"
                  min="10"
                  max="250"
                  value={weightKg}
                  onChange={(e) => setWeightKg(e.target.value ? parseFloat(e.target.value) : '')}
                  placeholder="65"
                  className="w-full border border-outline-variant rounded-lg p-3 bg-white text-xs text-on-surface outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all font-sans"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-on-surface mb-1.5">
                  Chiều cao (cm)
                </label>
                <input
                  type="number"
                  min="50"
                  max="230"
                  value={heightCm}
                  onChange={(e) => setHeightCm(e.target.value ? parseFloat(e.target.value) : '')}
                  placeholder="170"
                  className="w-full border border-outline-variant rounded-lg p-3 bg-white text-xs text-on-surface outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all font-sans"
                />
              </div>
            </div>

            {/* Live BMI Indicator */}
            {bmiInfo && (
              <div className="bg-error-container/20 border border-error-container/50 rounded-lg p-4 flex justify-between items-center">
                <span className="text-xs font-medium text-on-surface">
                  Chỉ số BMI: <strong className="text-on-surface font-bold ml-1">{bmiInfo.bmi}</strong>
                </span>
                <span className="bg-error-container text-error rounded px-3 py-1 text-xs font-bold">
                  {bmiInfo.label}
                </span>
              </div>
            )}

            {/* Female Specific Questions */}
            {gender === 'female' && (
              <div className="p-4 bg-surface-container border border-outline-variant rounded-lg space-y-2.5">
                <span className="text-xs font-bold text-on-surface block">
                  Tình trạng đặc biệt:
                </span>
                <div className="flex flex-wrap gap-4 text-xs">
                  <label className="flex items-center gap-2 cursor-pointer text-on-surface">
                    <input
                      type="checkbox"
                      checked={isPregnant}
                      onChange={(e) => setIsPregnant(e.target.checked)}
                      className="rounded text-primary focus:ring-primary"
                    />
                    <span>Đang mang thai</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer text-on-surface">
                    <input
                      type="checkbox"
                      checked={isBreastfeeding}
                      onChange={(e) => setIsBreastfeeding(e.target.checked)}
                      className="rounded text-primary focus:ring-primary"
                    />
                    <span>Đang cho con bú</span>
                  </label>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── STEP 2: Tiền sử Bệnh nền ── */}
        {step === 2 && (
          <div className="space-y-6">
            <div className="border-b border-outline-variant pb-3">
              <h2 className="text-xl md:text-2xl text-primary font-semibold flex items-center gap-2">
                <Heart size={20} className="text-primary" />
                Tiền sử bệnh nền
              </h2>
              <p className="text-xs text-on-surface-variant mt-1">
                Giúp phát hiện các thuốc chống chỉ định với tình trạng sức khỏe hiện tại của bạn.
              </p>
            </div>

            {/* None Checkbox */}
            <div className="p-3.5 bg-surface-container border border-outline-variant rounded-lg">
              <label className="flex items-center gap-2.5 cursor-pointer text-xs font-bold text-on-surface">
                <input
                  type="checkbox"
                  checked={hasNoConditions}
                  onChange={(e) => {
                    setHasNoConditions(e.target.checked);
                    if (e.target.checked) setConditions([]);
                  }}
                  className="rounded text-primary focus:ring-primary"
                />
                <span>Tôi không có bệnh nền mãn tính</span>
              </label>
            </div>

            {/* Condition Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {KNOWN_CONDITIONS.map((c) => {
                const isSelected = conditions.includes(c.id);
                return (
                  <button
                    key={c.id}
                    type="button"
                    disabled={hasNoConditions}
                    onClick={() => toggleCondition(c.id)}
                    className={`p-3.5 text-left rounded-lg border transition-all flex items-center justify-between ${
                      isSelected
                        ? 'bg-surface-container border-primary text-primary shadow-sm font-semibold'
                        : 'bg-white text-on-surface border-outline-variant hover:bg-surface-container-lowest disabled:opacity-40'
                    }`}
                  >
                    <div>
                      <span className="text-xs font-semibold block">{c.label}</span>
                      <span className="text-[11px] text-on-surface-variant">
                        {c.category}
                      </span>
                    </div>
                    {isSelected && <Check size={16} className="text-primary shrink-0" />}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* ── STEP 3: Dị ứng Thuốc ── */}
        {step === 3 && (
          <div className="space-y-6">
            <div className="border-b border-outline-variant pb-3">
              <h2 className="text-xl md:text-2xl text-primary font-semibold flex items-center gap-2">
                <ShieldAlert size={20} className="text-primary" />
                Dị ứng thuốc
              </h2>
              <p className="text-xs text-on-surface-variant mt-1">
                Cảnh báo nguy cơ quá mẫn hoặc dị ứng chéo khi phát hiện hoạt chất tương đồng.
              </p>
            </div>

            {/* None Checkbox */}
            <div className="p-3.5 bg-surface-container border border-outline-variant rounded-lg">
              <label className="flex items-center gap-2.5 cursor-pointer text-xs font-bold text-on-surface">
                <input
                  type="checkbox"
                  checked={hasNoAllergies}
                  onChange={(e) => {
                    setHasNoAllergies(e.target.checked);
                    if (e.target.checked) setAllergies([]);
                  }}
                  className="rounded text-primary focus:ring-primary"
                />
                <span>Tôi không có tiền sử dị ứng thuốc</span>
              </label>
            </div>

            {/* Allergy Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {KNOWN_ALLERGIES.map((a) => {
                const isSelected = allergies.includes(a.id);
                return (
                  <button
                    key={a.id}
                    type="button"
                    disabled={hasNoAllergies}
                    onClick={() => toggleAllergy(a.id)}
                    className={`p-3.5 text-left rounded-lg border transition-all flex items-center justify-between ${
                      isSelected
                        ? 'bg-surface-container border-primary text-primary shadow-sm font-semibold'
                        : 'bg-white text-on-surface border-outline-variant hover:bg-surface-container-lowest disabled:opacity-40'
                    }`}
                  >
                    <div>
                      <span className="text-xs font-semibold block">{a.label}</span>
                      <span className="text-[11px] text-on-surface-variant">
                        {a.category}
                      </span>
                    </div>
                    {isSelected && <Check size={16} className="text-primary shrink-0" />}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* ── STEP 4: Tổng kết & Xác nhận ── */}
        {step === 4 && (
          <div className="space-y-6">
            <div className="border-b border-outline-variant pb-3">
              <h2 className="text-xl md:text-2xl text-primary font-semibold flex items-center gap-2">
                <FileCheck size={20} className="text-primary" />
                Xác nhận hồ sơ
              </h2>
              <p className="text-xs text-on-surface-variant mt-1">
                Xem lại thông tin sức khỏe trước khi bắt đầu quản lý đơn thuốc.
              </p>
            </div>

            {/* Profile Summary Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-3.5 border border-outline-variant bg-surface-container/30 rounded-lg">
                <span className="text-[11px] text-on-surface-variant font-medium block">Thông tin cơ bản</span>
                <span className="text-xs font-bold text-on-surface block mt-1">
                  {age} tuổi • {gender === 'male' ? 'Nam' : gender === 'female' ? 'Nữ' : 'Khác'}
                </span>
                {bmiInfo && (
                  <span className="text-[11px] text-on-surface-variant block mt-0.5">
                    BMI: {bmiInfo.bmi} ({bmiInfo.label})
                  </span>
                )}
              </div>

              <div className="p-3.5 border border-outline-variant bg-surface-container/30 rounded-lg">
                <span className="text-[11px] text-on-surface-variant font-medium block">Bệnh nền ({conditions.length})</span>
                <span className="text-xs font-bold text-on-surface block mt-1">
                  {conditions.length > 0
                    ? conditions.map((c) => KNOWN_CONDITIONS.find((k) => k.id === c)?.label || c).join(', ')
                    : 'Không có bệnh nền'}
                </span>
              </div>

              <div className="p-3.5 border border-outline-variant bg-surface-container/30 rounded-lg">
                <span className="text-[11px] text-on-surface-variant font-medium block">Dị ứng thuốc ({allergies.length})</span>
                <span className="text-xs font-bold text-on-surface block mt-1">
                  {allergies.length > 0
                    ? allergies.map((a) => KNOWN_ALLERGIES.find((k) => k.id === a)?.label || a).join(', ')
                    : 'Không có dị ứng'}
                </span>
              </div>
            </div>

            {/* Legal Disclaimer Box */}
            <div className="p-4 border border-outline-variant bg-surface-container/50 rounded-lg text-xs text-on-surface space-y-1.5">
              <div className="flex items-center gap-2 font-semibold text-primary">
                <ShieldCheck size={16} className="text-primary" />
                <span>Tuyên bố miễn trừ trách nhiệm y tế</span>
              </div>
              <p className="text-[11px] text-on-surface-variant leading-relaxed">
                Hệ thống MediScan hỗ trợ phát hiện cảnh báo nguy cơ tương tác thuốc tự động phục vụ mục đích tham khảo. 
                Người bệnh không tự ý thay đổi liều hoặc ngừng thuốc mà không có ý kiến của bác sĩ điều trị.
              </p>
            </div>
          </div>
        )}

        {/* ── Wizard Navigation Buttons ── */}
        <div className="flex items-center justify-between pt-4 border-t border-outline-variant">
          {step > 1 ? (
            <button
              type="button"
              onClick={() => setStep((s) => (s - 1) as typeof step)}
              className="h-12 px-6 border border-outline-variant bg-white hover:bg-surface-container text-on-surface-variant text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all"
            >
              <ArrowLeft size={14} />
              <span>Quay lại</span>
            </button>
          ) : (
            <div />
          )}

          {step < 4 ? (
            <button
              type="button"
              onClick={handleNext}
              className="h-12 px-6 bg-primary hover:bg-primary/90 text-on-primary text-xs font-semibold rounded-lg flex items-center gap-2 transition-all shadow-sm"
            >
              <span>Tiếp theo</span>
              <ArrowRight size={14} />
            </button>
          ) : (
            <button
              type="button"
              disabled={isSubmitting}
              onClick={handleComplete}
              className="h-12 px-6 bg-primary hover:bg-primary/90 text-on-primary text-xs font-semibold rounded-lg flex items-center gap-2 transition-all shadow-sm disabled:opacity-50"
            >
              <CheckCircle2 size={16} />
              <span>Hoàn tất & Vào tủ thuốc</span>
            </button>
          )}
        </div>

      </div>

    </div>
  );
}
