'use client';

import { useCabinetStore, CabinetDrugItem } from '@/store/cabinetStore';
import { IDrugEvaluationRequest, IEvaluationResponse, IUserProfile } from '@/types/medication';
import { Pill, Trash2, Play, Pause, ActivitySquare, FlaskConical, Loader2, User, ChevronDown, ChevronUp, Pencil, Plus, Check, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState, useEffect } from 'react';
import { useEvaluation } from '@/services/evaluationService';
import { isDisclaimerAccepted, openMedicalDisclaimerModal } from '@/components/common/MedicalDisclaimerModal';
import { toast } from '@/components/common/Toast';
import { KNOWN_CONDITIONS, KNOWN_ALLERGIES } from '@/constants/conditions';
import { useUserProfileStore } from '@/store/userProfileStore';

interface ActiveCabinetProps {
  onReportReady: (report: IEvaluationResponse) => void;
}

// COMMON_CONDITIONS / COMMON_ALLERGIES migrated to @/constants/conditions.ts
// (centralized single source of truth — khớp backend DRUG_CONDITION_CONFLICTS)

export function ActiveCabinet({ onReportReady }: ActiveCabinetProps) {
    const { drugs, removeDrug, toggleActive, clearAll, updateDrug, addDrug } = useCabinetStore();
  const [showProfile, setShowProfile] = useState(false);

  // [P1/F4.4] TanStack Query mutation — thay thế axios inline (xóa hardcode URL).
  const { mutate: runEvaluate, isPending: isAnalyzing } = useEvaluation();

  // [Onboarding] Đọc profile từ Zustand store làm giá trị khởi tạo (nếu đã onboard).
  // Giữ local state cho phép override tại đây mà không thay đổi profile gốc.
  const storedProfile = useUserProfileStore((s) => s.profile);
  const [age, setAge] = useState<number>(storedProfile?.age ?? 45);
  const [conditions, setConditions] = useState<string[]>(storedProfile?.conditions ?? []);
  const [allergies, setAllergies] = useState<string[]>(storedProfile?.allergies ?? []);

  // Sync khi storedProfile thay đổi (VD: user vừa hoàn tất onboarding)
  useEffect(() => {
    if (storedProfile) {
      setAge(storedProfile.age);
      setConditions(storedProfile.conditions);
      setAllergies(storedProfile.allergies);
    }
  }, [storedProfile]);

  const activeDrugs = drugs.filter(d => d.isActive);

  const toggleCondition = (cond: string) => {
    setConditions(prev => 
      prev.includes(cond) ? prev.filter(c => c !== cond) : [...prev, cond]
    );
  };

  const toggleAllergy = (allergy: string) => {
    setAllergies(prev => 
      prev.includes(allergy) ? prev.filter(a => a !== allergy) : [...prev, allergy]
    );
  };

  /** [P3/F4.8] Inline-edit state: chỉnh sửa thông tin thuốc trong tủ. */
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<CabinetDrugItem>>({});
  const [isManualAddOpen, setIsManualAddOpen] = useState(false);
  const [manualForm, setManualForm] = useState({ brandName: '', strength: '', activeIngredient: '', dosageInstruction: '' });

  const startEdit = (drug: CabinetDrugItem) => {
    setEditingId(drug.id);
    setEditForm({ brandName: drug.brandName, strength: drug.strength, activeIngredient: drug.activeIngredient, dosageInstruction: drug.dosageInstruction });
  };

  const saveEdit = (id: string) => {
    if (!editForm.brandName?.trim()) {
      toast.warning('Tên thuốc không được để trống.');
      return;
    }
    updateDrug(id, editForm);
    setEditingId(null);
    toast.success('Đã cập nhật thông tin thuốc.');
  };

  const submitManual = () => {
    if (!manualForm.brandName.trim()) {
      toast.warning('Vui lòng nhập tên thuốc.');
      return;
    }
    addDrug({ ...manualForm, brandName: manualForm.brandName.trim(), confidenceScore: 1, isVerified: true, inputSource: 'manual' });
    setManualForm({ brandName: '', strength: '', activeIngredient: '', dosageInstruction: '' });
    setIsManualAddOpen(false);
    toast.success(`Đã thêm "${manualForm.brandName.trim()}" vào Tủ thuốc.`);
  };

  const handleAnalyze = async () => {
    // 1. Enforce Medical Disclaimer Acceptance (Task 6.1 — disclaimer gate)
    if (!isDisclaimerAccepted()) {
      openMedicalDisclaimerModal();
      toast.warning('Vui lòng đọc và chấp thuận Tuyên bố Miễn trừ Trách nhiệm Y tế trước khi phân tích.');
      return;
    }

    if (activeDrugs.length === 0) {
      toast.warning('Tủ thuốc trống! Hãy thêm ít nhất 1 loại thuốc trước khi phân tích.');
      return;
    }

            const userProfile: IUserProfile | undefined = (conditions.length > 0 || allergies.length > 0 || age) ? {
      age: Number(age) || 45,
      conditions,
      allergies
    } : undefined;

    const payload: IDrugEvaluationRequest = {
      userProfile,
      drugs: activeDrugs.map(d => ({
        brandName: d.brandName,
        activeIngredient: d.activeIngredient,
        strength: d.strength,
        dosageInstruction: d.dosageInstruction,
        confidenceScore: d.confidenceScore,
        isVerified: d.isVerified,
        matchMethod: d.matchMethod,
      }))
    };

    runEvaluate(payload, {
      onSuccess: (reportData: IEvaluationResponse) => {
        toast.success(`Đã phân tích thành công ${reportData.totalDrugsAnalyzed} loại thuốc!`);
        onReportReady(reportData);
      },
      onError: (err: Error) => {
        console.error('Evaluation Error:', err);
        toast.error(`Lỗi phân tích: ${err.message || 'Đã xảy ra lỗi trong quá trình đánh giá tương tác thuốc.'}`);
      },
    });
  };

  if (drugs.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 border-dashed p-8 flex flex-col items-center justify-center text-center shadow-sm">
        <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mb-4 shadow-inner">
          <ActivitySquare size={32} />
        </div>
        <h3 className="text-base font-bold text-gray-900">Tủ thuốc đang trống</h3>
        <p className="text-gray-500 mt-1.5 max-w-xs text-xs leading-relaxed">
          Hãy tải lên ảnh toa thuốc hoặc chụp vỏ hộp để AI trích xuất và lưu danh mục vào Tủ thuốc.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 bg-gray-50/80 flex justify-between items-center">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center font-bold">
            <Pill size={18} />
          </div>
          <div>
            <h2 className="font-bold text-gray-900 text-sm">
              Tủ Thuốc Đang Dùng
            </h2>
            <p className="text-[11px] text-gray-500">
              {activeDrugs.length}/{drugs.length} loại thuốc đang kích hoạt
            </p>
          </div>
        </div>

        {drugs.length > 0 && (
          <button
            onClick={clearAll}
            className="text-[11px] font-semibold text-gray-400 hover:text-red-600 transition-colors"
            title="Xóa toàn bộ tủ thuốc"
          >
            Xóa tất cả
          </button>
        )}
      </div>

{/* [P3/F4.8] Entry-point nhập tay — inputSource: 'manual' */}
      <div className="px-5 py-2 border-b border-gray-100 flex items-center gap-2">
        <button
          onClick={() => setIsManualAddOpen(!isManualAddOpen)}
          className="inline-flex items-center gap-1.5 text-[11px] font-bold px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors"
        >
          <Plus size={13} /> {isManualAddOpen ? 'Đóng' : 'Thêm thuốc thủ công'}
        </button>
      </div>

      {isManualAddOpen && (
        <div className="px-5 py-3 border-b border-gray-100 bg-blue-50/40 space-y-2.5">
          <input
            value={manualForm.brandName}
            onChange={(e) => setManualForm(p => ({ ...p, brandName: e.target.value }))}
            placeholder="Tên thuốc *"
            className="w-full px-3 py-1.5 rounded-lg border border-gray-300 outline-none focus:ring-1 focus:ring-blue-500 text-sm"
          />
          <div className="flex gap-2">
            <input
              value={manualForm.strength}
              onChange={(e) => setManualForm(p => ({ ...p, strength: e.target.value }))}
              placeholder="Hàm lượng"
              className="flex-1 px-3 py-1.5 rounded-lg border border-gray-300 outline-none focus:ring-1 focus:ring-blue-500 text-sm"
            />
            <input
              value={manualForm.activeIngredient}
              onChange={(e) => setManualForm(p => ({ ...p, activeIngredient: e.target.value }))}
              placeholder="Hoạt chất"
              className="flex-1 px-3 py-1.5 rounded-lg border border-gray-300 outline-none focus:ring-1 focus:ring-blue-500 text-sm"
            />
          </div>
          <input
            value={manualForm.dosageInstruction}
            onChange={(e) => setManualForm(p => ({ ...p, dosageInstruction: e.target.value }))}
            placeholder="Liều dùng (không bắt buộc — tự nhập, không suy đoán)"
            className="w-full px-3 py-1.5 rounded-lg border border-gray-300 outline-none focus:ring-1 focus:ring-blue-500 text-sm"
          />
          <button onClick={submitManual} className="w-full py-2 rounded-lg bg-blue-600 text-white text-sm font-bold hover:bg-blue-700 transition-colors">
            Thêm vào Tủ thuốc
          </button>
        </div>
      )}

      {/* Drug List */}
      {/* Drug List */}
      <div className="divide-y divide-gray-50 max-h-[38vh] overflow-y-auto">
        {drugs.map(drug => (
          <div
            key={drug.id}
            className={cn(
              'p-3.5 flex items-start gap-3 transition-colors hover:bg-gray-50/80 relative',
              !drug.isActive && 'opacity-40 bg-gray-50/50'
            )}
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap mb-1">
                <h4 className={cn('font-bold text-xs', !drug.isActive ? 'text-gray-400 line-through' : 'text-gray-900')}>
                  {drug.brandName}
                </h4>
                {drug.strength && (
                  <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-bold rounded">
                    {drug.strength}
                  </span>
                )}
                {drug.inputSource === 'packaging' && (
                  <span className="px-1.5 py-0.5 bg-purple-50 text-purple-700 text-[10px] rounded font-medium">Vỏ hộp</span>
                )}
                {drug.inputSource === 'prescription' && (
                  <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-[10px] rounded font-medium">Toa thuốc</span>
                )}
              </div>
              <div className="text-[11px] text-gray-500 space-y-0.5">
                {drug.activeIngredient && (
                  <p className="truncate"><span className="font-semibold text-gray-600">HC:</span> {drug.activeIngredient}</p>
                )}
                {drug.dosageInstruction && (
                  <p className="truncate text-gray-600"><span className="font-semibold">Liều:</span> {drug.dosageInstruction}</p>
                )}
              </div>
            </div>
            
            <div className="flex items-center gap-1 shrink-0">
              <button
                onClick={() => toggleActive(drug.id)}
                className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-all"
                title={drug.isActive ? 'Tạm ngưng phân tích' : 'Kích hoạt lại'}
              >
                {drug.isActive ? <Pause size={14} /> : <Play size={14} />}
              </button>
              <button
                onClick={() => startEdit(drug)}
                className="p-1.5 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 transition-all"
                title="Sửa thông tin thuốc"
              >
                <Pencil size={14} />
              </button>
              {editingId === drug.id && (
                <div className="absolute inset-0 z-10 bg-white/95 backdrop-blur-sm rounded-xl border border-indigo-200 p-3.5 space-y-2 shadow-lg">
                  <p className="text-xs font-bold text-indigo-700">Sửa thông tin thuốc</p>
                  <input
                    value={editForm.brandName ?? ''}
                    onChange={(e) => setEditForm(p => ({ ...p, brandName: e.target.value }))}
                    placeholder="Tên thuốc"
                    className="w-full px-3 py-1.5 rounded-lg border border-gray-300 outline-none focus:ring-1 focus:ring-indigo-500 text-sm"
                  />
                  <input
                    value={editForm.strength ?? ''}
                    onChange={(e) => setEditForm(p => ({ ...p, strength: e.target.value }))}
                    placeholder="Hàm lượng"
                    className="w-full px-3 py-1.5 rounded-lg border border-gray-300 outline-none focus:ring-1 focus:ring-indigo-500 text-sm"
                  />
                  <input
                    value={editForm.activeIngredient ?? ''}
                    onChange={(e) => setEditForm(p => ({ ...p, activeIngredient: e.target.value }))}
                    placeholder="Hoạt chất"
                    className="w-full px-3 py-1.5 rounded-lg border border-gray-300 outline-none focus:ring-1 focus:ring-indigo-500 text-sm"
                  />
                  <textarea
                    value={editForm.dosageInstruction ?? ''}
                    onChange={(e) => setEditForm(p => ({ ...p, dosageInstruction: e.target.value }))}
                    placeholder="Liều dùng"
                    rows={2}
                    className="w-full px-3 py-1.5 rounded-lg border border-gray-300 outline-none focus:ring-1 focus:ring-indigo-500 text-sm resize-none"
                  />
                  <div className="flex gap-2 justify-end">
                    <button
                      onClick={() => setEditingId(null)}
                      className="px-3 py-1.5 rounded-lg text-xs font-bold text-gray-500 hover:bg-gray-100"
                    >
                      <X size={13} className="inline" /> Hủy
                    </button>
                    <button
                      onClick={() => saveEdit(drug.id)}
                      className="px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700"
                    >
                      <Check size={13} className="inline" /> Lưu
                    </button>
                  </div>
                </div>
              )}
              <button
                onClick={() => {
                  removeDrug(drug.id);
                  toast.info(`Đã xóa "${drug.brandName}" khỏi Tủ thuốc.`);
                }}
                className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-all"
                title="Xoá thuốc"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Patient Profile Collapsible Accordion (Layer 3) */}
      <div className="border-t border-gray-100 bg-gray-50/50">
        <button
          onClick={() => setShowProfile(!showProfile)}
          className="w-full px-4 py-2.5 flex items-center justify-between text-left hover:bg-gray-100/60 transition-colors"
        >
          <div className="flex items-center gap-2">
            <User size={14} className="text-indigo-600" />
            <span className="text-xs font-bold text-gray-700">Hồ Sơ Bệnh Nhân (Tùy chọn)</span>
            {(conditions.length > 0 || allergies.length > 0) && (
              <span className="bg-indigo-100 text-indigo-700 text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                {conditions.length + allergies.length}
              </span>
            )}
          </div>
          {showProfile ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
        </button>

        {showProfile && (
          <div className="p-4 space-y-3 bg-white border-t border-gray-100 text-xs animate-in slide-in-from-top-2 duration-200">
            <div>
              <label className="block text-[11px] font-bold text-gray-700 mb-1">Tuổi bệnh nhân:</label>
              <input
                type="number"
                value={age}
                onChange={e => setAge(Number(e.target.value))}
                min={1}
                max={120}
                className="w-24 px-2.5 py-1 border border-gray-200 rounded-md outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-[11px] font-bold text-gray-700 mb-1.5">Tiền sử bệnh nền:</label>
              <div className="flex flex-wrap gap-1.5">
                {KNOWN_CONDITIONS.map(opt => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => toggleCondition(opt.value)}
                    className={cn(
                      'px-2 py-1 rounded-md text-[11px] transition-all font-medium',
                      conditions.includes(opt.value)
                        ? 'bg-red-100 text-red-700 border border-red-200 font-bold'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-gray-700 mb-1.5">Dị ứng thuốc:</label>
              <div className="flex flex-wrap gap-1.5">
                {KNOWN_ALLERGIES.map(opt => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => toggleAllergy(opt.value)}
                    className={cn(
                      'px-2 py-1 rounded-md text-[11px] transition-all font-medium',
                      allergies.includes(opt.value)
                        ? 'bg-amber-100 text-amber-800 border border-amber-200 font-bold'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* CTA: Analyze Button */}
      <div className="p-4 border-t border-gray-100 bg-gray-50/80">
        <button
          onClick={handleAnalyze}
          disabled={isAnalyzing || activeDrugs.length === 0}
          className={cn(
            'w-full py-3.5 rounded-xl text-white font-bold text-xs tracking-wide flex items-center justify-center gap-2 transition-all shadow-sm',
            isAnalyzing || activeDrugs.length === 0
              ? 'bg-gray-300 cursor-not-allowed text-gray-500'
              : 'bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 hover:shadow-md active:scale-[0.98]'
          )}
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="animate-spin" size={16} />
              <span>Đang Phân Tích 3 Lớp...</span>
            </>
          ) : (
            <>
              <FlaskConical size={16} />
              <span>BẮT ĐẦU PHÂN TÍCH TƯƠNG TÁC</span>
            </>
          )}
        </button>
        {activeDrugs.length === 0 && drugs.length > 0 && (
          <p className="text-center text-[11px] text-amber-600 font-medium mt-2">
            Vui lòng bật kích hoạt ít nhất 1 loại thuốc để phân tích
          </p>
        )}
      </div>
    </div>
  );
}
