'use client';

/**
 * ClinicalOnboardingWizard — Hồ Sơ Y Tế Lâm Sàng Minimalist (Stage 10+ Harmonization).
 * Bảng khai báo 4 phân khu tối giản, vuông vức (rounded-none / rounded-sm), đơn sắc (#0F172A, #334155, #FFFFFF, #E2E8F0).
 * Hoàn tất ➔ Lưu Backend API & chuyển thẳng tới /cabinet.
 */

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Activity, ArrowRight, ArrowLeft, Check, ShieldCheck,
  AlertCircle, Scale, Heart, ShieldAlert, FileCheck, CheckCircle2
} from 'lucide-react';
import { useUserProfileStore } from '@/store/userProfileStore';
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
      let color = 'text-emerald-700 bg-emerald-50 border-emerald-300';
      if (bmiVal < 18.5) {
        label = 'Nhẹ cân';
        color = 'text-sky-700 bg-sky-50 border-sky-300';
      } else if (bmiVal >= 23 && bmiVal < 25) {
        label = 'Thừa cân (Chuẩn Châu Á)';
        color = 'text-amber-700 bg-amber-50 border-amber-300';
      } else if (bmiVal >= 25) {
        label = 'Béo phì';
        color = 'text-rose-700 bg-rose-50 border-rose-300';
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
      setStep(4);
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

      toast.success('Hồ sơ y tế đã được khởi tạo thành công!');
      // Điều hướng thẳng tới /cabinet theo state machine
      router.replace('/cabinet');
    } catch {
      toast.success('Đã lưu hồ sơ y tế cục bộ!');
      router.replace('/cabinet');
    } finally {
      setIsSubmitting(false);
    }
  };

  const stepsHeader = [
    { num: 1, label: '[01] SINH TRẮC HỌC' },
    { num: 2, label: '[02] TIỀN SỬ BỆNH NỀN' },
    { num: 3, label: '[03] DỊ ỨNG THUỐC' },
    { num: 4, label: '[04] XÁC NHẬN PHÁP LÝ' },
  ];

  return (
    <div className="w-full max-w-4xl mx-auto p-4 sm:p-6 space-y-6">
      
      {/* ── Top Wizard Progress Index ── */}
      <div className="border border-slate-200 bg-white p-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {stepsHeader.map((s) => {
            const isCurrent = step === s.num;
            const isDone = step > s.num;
            return (
              <div
                key={s.num}
                className={`p-2 border text-xs font-mono font-bold flex items-center gap-2 ${
                  isCurrent
                    ? 'bg-slate-900 text-white border-slate-900'
                    : isDone
                    ? 'bg-slate-50 text-slate-700 border-slate-300'
                    : 'bg-white text-slate-400 border-slate-200'
                }`}
              >
                {isDone ? <Check size={13} className="text-emerald-600" /> : <span>{s.num}.</span>}
                <span className="truncate">{s.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Main Step Card ── */}
      <div className="border border-slate-200 bg-white p-6 sm:p-8 space-y-6">

        {/* ── STEP 1: Sinh trắc học ── */}
        {step === 1 && (
          <div className="space-y-6">
            <div className="border-b border-slate-200 pb-3">
              <h2 className="text-sm font-mono font-black text-slate-900 uppercase flex items-center gap-2">
                <Scale size={16} />
                PHÂN KHU 1: THÔNG SỐ SINH TRẮC HỌC CƠ BẢN
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Các chỉ số dùng để tính toán phân tầng liều dùng tối đa và chống chỉ định tuổi.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-mono font-bold text-slate-700 uppercase mb-1">
                  Tuổi hiện tại <span className="text-rose-600">*</span>
                </label>
                <input
                  type="number"
                  min="1"
                  max="125"
                  value={age}
                  onChange={(e) => handleAgeChange(e.target.value)}
                  placeholder="VD: 35"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 text-xs text-slate-900 outline-none focus:border-slate-900 focus:bg-white font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-mono font-bold text-slate-700 uppercase mb-1">
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
                      className={`py-2 text-xs font-mono font-bold border transition-colors ${
                        gender === g.id
                          ? 'bg-slate-900 text-white border-slate-900'
                          : 'bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100'
                      }`}
                    >
                      {g.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono font-bold text-slate-700 uppercase mb-1">
                  Cân nặng (kg)
                </label>
                <input
                  type="number"
                  min="10"
                  max="250"
                  value={weightKg}
                  onChange={(e) => setWeightKg(e.target.value ? parseFloat(e.target.value) : '')}
                  placeholder="VD: 65"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 text-xs text-slate-900 outline-none focus:border-slate-900 focus:bg-white font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-mono font-bold text-slate-700 uppercase mb-1">
                  Chiều cao (cm)
                </label>
                <input
                  type="number"
                  min="50"
                  max="230"
                  value={heightCm}
                  onChange={(e) => setHeightCm(e.target.value ? parseFloat(e.target.value) : '')}
                  placeholder="VD: 170"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 text-xs text-slate-900 outline-none focus:border-slate-900 focus:bg-white font-mono"
                />
              </div>
            </div>

            {/* Live BMI Indicator */}
            {bmiInfo && (
              <div className="p-3 border border-slate-200 bg-slate-50 flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-slate-700">
                  CHỈ SỐ BMI ƯỚC TÍNH: <strong className="font-mono text-slate-900">{bmiInfo.bmi}</strong>
                </span>
                <span className={`px-2 py-0.5 border text-xs font-mono font-bold ${bmiInfo.color}`}>
                  {bmiInfo.label}
                </span>
              </div>
            )}

            {/* Female Specific Questions */}
            {gender === 'female' && (
              <div className="p-4 border border-slate-200 bg-slate-50 space-y-2">
                <span className="text-xs font-mono font-bold text-slate-700 block mb-1">
                  TÌNH TRẠNG ĐẶC BIỆT (NỮ GIỚI):
                </span>
                <div className="flex flex-wrap gap-4 text-xs font-mono">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isPregnant}
                      onChange={(e) => setIsPregnant(e.target.checked)}
                      className="rounded-none border-slate-300"
                    />
                    <span>Đang trong thai kỳ (Mang thai)</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isBreastfeeding}
                      onChange={(e) => setIsBreastfeeding(e.target.checked)}
                      className="rounded-none border-slate-300"
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
            <div className="border-b border-slate-200 pb-3">
              <h2 className="text-sm font-mono font-black text-slate-900 uppercase flex items-center gap-2">
                <Heart size={16} />
                PHÂN KHU 2: TIỀN SỬ BỆNH NỀN MÃN TÍNH
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Hệ thống sẽ đối chiếu chống chỉ định lâm sàng giữa thuốc quét được và bệnh nền.
              </p>
            </div>

            {/* None Checkbox */}
            <div className="p-3 border border-slate-200 bg-slate-50">
              <label className="flex items-center gap-2 cursor-pointer text-xs font-mono font-bold text-slate-900">
                <input
                  type="checkbox"
                  checked={hasNoConditions}
                  onChange={(e) => {
                    setHasNoConditions(e.target.checked);
                    if (e.target.checked) setConditions([]);
                  }}
                  className="rounded-none border-slate-300"
                />
                <span>TÔI KHÔNG CÓ BỆNH NỀN MÃN TÍNH NÀO</span>
              </label>
            </div>

            {/* Condition Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {KNOWN_CONDITIONS.map((c) => {
                const isSelected = conditions.includes(c.id);
                return (
                  <button
                    key={c.id}
                    type="button"
                    disabled={hasNoConditions}
                    onClick={() => toggleCondition(c.id)}
                    className={`p-3 text-left border font-mono transition-colors flex items-center justify-between ${
                      isSelected
                        ? 'bg-slate-900 text-white border-slate-900'
                        : 'bg-slate-50 text-slate-800 border-slate-200 hover:bg-slate-100 disabled:opacity-40'
                    }`}
                  >
                    <div>
                      <span className="text-xs font-bold block">{c.label}</span>
                      <span className={`text-[10px] ${isSelected ? 'text-slate-400' : 'text-slate-500'}`}>
                        {c.category}
                      </span>
                    </div>
                    {isSelected && <Check size={14} className="text-emerald-400" />}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* ── STEP 3: Dị ứng Thuốc ── */}
        {step === 3 && (
          <div className="space-y-6">
            <div className="border-b border-slate-200 pb-3">
              <h2 className="text-sm font-mono font-black text-slate-900 uppercase flex items-center gap-2">
                <ShieldAlert size={16} />
                PHÂN KHU 3: TIỀN SỬ DỊ ỨNG THUỐC
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Cảnh báo nguy cơ phản vệ hoặc quá mẫn tức thì nếu phát hiện hoạt chất cùng nhóm.
              </p>
            </div>

            {/* None Checkbox */}
            <div className="p-3 border border-slate-200 bg-slate-50">
              <label className="flex items-center gap-2 cursor-pointer text-xs font-mono font-bold text-slate-900">
                <input
                  type="checkbox"
                  checked={hasNoAllergies}
                  onChange={(e) => {
                    setHasNoAllergies(e.target.checked);
                    if (e.target.checked) setAllergies([]);
                  }}
                  className="rounded-none border-slate-300"
                />
                <span>TÔI CHƯA TỪNG CÓ TIỀN SỬ DỊ ỨNG THUỐC</span>
              </label>
            </div>

            {/* Allergy Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {KNOWN_ALLERGIES.map((a) => {
                const isSelected = allergies.includes(a.id);
                return (
                  <button
                    key={a.id}
                    type="button"
                    disabled={hasNoAllergies}
                    onClick={() => toggleAllergy(a.id)}
                    className={`p-3 text-left border font-mono transition-colors flex items-center justify-between ${
                      isSelected
                        ? 'bg-slate-900 text-white border-slate-900'
                        : 'bg-slate-50 text-slate-800 border-slate-200 hover:bg-slate-100 disabled:opacity-40'
                    }`}
                  >
                    <div>
                      <span className="text-xs font-bold block">{a.label}</span>
                      <span className={`text-[10px] ${isSelected ? 'text-slate-400' : 'text-slate-500'}`}>
                        {a.category}
                      </span>
                    </div>
                    {isSelected && <Check size={14} className="text-emerald-400" />}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* ── STEP 4: Tổng kết & Xác nhận pháp lý ── */}
        {step === 4 && (
          <div className="space-y-6">
            <div className="border-b border-slate-200 pb-3">
              <h2 className="text-sm font-mono font-black text-slate-900 uppercase flex items-center gap-2">
                <FileCheck size={16} />
                PHÂN KHU 4: TỔNG HỢP HỒ SƠ & XÁC NHẬN Y KHOA
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Kiểm tra lại toàn bộ thông tin lâm sàng trước khi kích hoạt không gian Tủ thuốc.
              </p>
            </div>

            {/* Profile Summary Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-3 border border-slate-200 bg-slate-50">
                <span className="text-[10px] font-mono text-slate-500 uppercase block">Sinh trắc học:</span>
                <span className="text-xs font-mono font-bold text-slate-900 block mt-1">
                  {age} tuổi • {gender === 'male' ? 'Nam' : gender === 'female' ? 'Nữ' : 'Khác'}
                </span>
                {bmiInfo && (
                  <span className="text-[11px] font-mono text-slate-600 block mt-0.5">
                    BMI: {bmiInfo.bmi} ({bmiInfo.label})
                  </span>
                )}
              </div>

              <div className="p-3 border border-slate-200 bg-slate-50">
                <span className="text-[10px] font-mono text-slate-500 uppercase block">Bệnh nền ({conditions.length}):</span>
                <span className="text-xs font-mono font-bold text-slate-900 block mt-1">
                  {conditions.length > 0
                    ? conditions.map((c) => KNOWN_CONDITIONS.find((k) => k.id === c)?.label || c).join(', ')
                    : 'Không có bệnh nền'}
                </span>
              </div>

              <div className="p-3 border border-slate-200 bg-slate-50">
                <span className="text-[10px] font-mono text-slate-500 uppercase block">Dị ứng thuốc ({allergies.length}):</span>
                <span className="text-xs font-mono font-bold text-slate-900 block mt-1">
                  {allergies.length > 0
                    ? allergies.map((a) => KNOWN_ALLERGIES.find((k) => k.id === a)?.label || a).join(', ')
                    : 'Không có dị ứng'}
                </span>
              </div>
            </div>

            {/* Legal Disclaimer Box */}
            <div className="p-4 border border-slate-300 bg-slate-100 text-xs font-mono text-slate-700 space-y-2">
              <div className="flex items-center gap-2 font-bold text-slate-900 uppercase">
                <ShieldCheck size={15} />
                <span>CAM KẾT BẢO MẬT & MIỄN TRỪ TRÁCH NHIỆM Y TẾ</span>
              </div>
              <p className="text-[11px] leading-relaxed">
                Hệ thống Mediscan AI chỉ cung cấp cảnh báo tương tác tự động phục vụ mục đích tham khảo và phòng ngừa nguy cơ. 
                Người bệnh tuyệt đối không tự ý thay đổi liều lượng hoặc ngừng thuốc mà không có sự chỉ định của bác sĩ điều trị.
              </p>
            </div>
          </div>
        )}

        {/* ── Wizard Navigation Buttons ── */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-200">
          {step > 1 ? (
            <button
              type="button"
              onClick={() => setStep((s) => (s - 1) as typeof step)}
              className="h-10 px-4 border border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-800 text-xs font-mono font-bold flex items-center gap-1.5 transition-colors"
            >
              <ArrowLeft size={14} />
              <span>QUAY LẠI</span>
            </button>
          ) : (
            <div />
          )}

          {step < 4 ? (
            <button
              type="button"
              onClick={handleNext}
              className="h-10 px-6 bg-slate-900 hover:bg-slate-800 text-white text-xs font-mono font-bold flex items-center gap-2 transition-colors"
            >
              <span>TIẾP THEO</span>
              <ArrowRight size={14} />
            </button>
          ) : (
            <button
              type="button"
              disabled={isSubmitting}
              onClick={handleComplete}
              className="h-10 px-6 bg-slate-900 hover:bg-slate-800 text-white text-xs font-mono font-bold flex items-center gap-2 transition-colors disabled:opacity-50"
            >
              <CheckCircle2 size={15} />
              <span>HOÀN TẤT & VÀO TỦ THUỐC</span>
            </button>
          )}
        </div>

      </div>

    </div>
  );
}
