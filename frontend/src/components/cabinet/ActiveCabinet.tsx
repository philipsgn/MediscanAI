'use client';

/**
 * ActiveCabinet — Tủ Thuốc Đang Dùng (Minimalist Clinical Grade).
 * Khung lưới 1px sắc nét, bo góc rounded-none / rounded-sm, đơn sắc (#0F172A, #334155, #FFFFFF, #E2E8F0).
 * Bật/tắt phân tích từng thuốc, chỉnh sửa trực tiếp, nhập tay thủ công & nút kích hoạt đánh giá tương tác.
 */

import React, { useState, useEffect } from 'react';
import { useCabinetStore, CabinetDrugItem } from '@/store/cabinetStore';
import { IDrugEvaluationRequest, IEvaluationResponse, IUserProfile } from '@/types/medication';
import {
  Pill, Trash2, Play, Pause, Activity, Loader2, User,
  ChevronDown, ChevronUp, Pencil, Plus, Check, X, ShieldAlert
} from 'lucide-react';
import { useEvaluation } from '@/services/evaluationService';
import { isDisclaimerAccepted, openMedicalDisclaimerModal } from '@/components/common/MedicalDisclaimerModal';
import { toast } from '@/components/common/Toast';
import { useUserProfileStore } from '@/store/userProfileStore';

interface ActiveCabinetProps {
  onReportReady: (report: IEvaluationResponse) => void;
}

export function ActiveCabinet({ onReportReady }: ActiveCabinetProps) {
  const { drugs, removeDrug, toggleActive, clearAll, updateDrug, addDrug } = useCabinetStore();
  const [showProfile, setShowProfile] = useState(false);

  const { mutate: runEvaluate, isPending: isAnalyzing } = useEvaluation();

  const storedProfile = useUserProfileStore((s) => s.profile);
  const [age, setAge] = useState<number>(storedProfile?.age ?? 35);
  const [conditions, setConditions] = useState<string[]>(storedProfile?.conditions ?? []);
  const [allergies, setAllergies] = useState<string[]>(storedProfile?.allergies ?? []);

  useEffect(() => {
    if (storedProfile) {
      setAge(storedProfile.age || 35);
      setConditions(storedProfile.conditions || []);
      setAllergies(storedProfile.allergies || []);
    }
  }, [storedProfile]);

  const activeDrugs = drugs.filter((d) => d.isActive);

  // State chỉnh sửa trực tiếp & nhập tay
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<CabinetDrugItem>>({});
  const [isManualAddOpen, setIsManualAddOpen] = useState(false);
  const [manualForm, setManualForm] = useState({ brandName: '', strength: '', activeIngredient: '', dosageInstruction: '' });

  const startEdit = (drug: CabinetDrugItem) => {
    setEditingId(drug.id);
    setEditForm({
      brandName: drug.brandName,
      strength: drug.strength,
      activeIngredient: drug.activeIngredient,
      dosageInstruction: drug.dosageInstruction,
    });
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
    addDrug({
      ...manualForm,
      brandName: manualForm.brandName.trim(),
      confidenceScore: 1,
      isVerified: true,
      inputSource: 'manual',
    });
    setManualForm({ brandName: '', strength: '', activeIngredient: '', dosageInstruction: '' });
    setIsManualAddOpen(false);
    toast.success(`Đã thêm "${manualForm.brandName.trim()}" vào Tủ thuốc.`);
  };

  const handleAnalyze = async () => {
    if (!isDisclaimerAccepted()) {
      openMedicalDisclaimerModal();
      toast.warning('Vui lòng đọc và chấp thuận Tuyên bố Miễn trừ Trách nhiệm Y tế.');
      return;
    }

    if (activeDrugs.length === 0) {
      toast.warning('Tủ thuốc trống! Hãy thêm ít nhất 1 loại thuốc trước khi phân tích.');
      return;
    }

    const userProfile: IUserProfile = {
      age: Number(age) || 35,
      gender: storedProfile?.gender || 'male',
      conditions,
      allergies,
      isPregnant: storedProfile?.isPregnant || false,
      isBreastfeeding: storedProfile?.isBreastfeeding || false,
      weightKg: storedProfile?.weightKg,
      heightCm: storedProfile?.heightCm,
    };

    const payload: IDrugEvaluationRequest = {
      userProfile,
      drugs: activeDrugs.map((d) => ({
        brandName: d.brandName,
        activeIngredient: d.activeIngredient || d.brandName,
        strength: d.strength || '',
        dosageInstruction: d.dosageInstruction || '',
        confidenceScore: d.confidenceScore,
        isVerified: d.isVerified,
        matchMethod: d.matchMethod,
      })),
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

  return (
    <div className="bg-white border border-slate-200 overflow-hidden flex flex-col font-mono text-xs">
      
      {/* ── Header ── */}
      <div className="p-4 border-b border-slate-200 bg-slate-50 flex flex-wrap justify-between items-center gap-2">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-slate-900 text-white flex items-center justify-center font-bold">
            <Pill size={15} />
          </div>
          <div>
            <h2 className="font-bold text-slate-900 text-xs uppercase">
              DANH MỤC THUỐC TRONG TỦ ({activeDrugs.length}/{drugs.length} ĐANG KÍCH HOẠT)
            </h2>
            <p className="text-[10px] text-slate-500">
              Nhấn nút Bật/Tắt để bao gồm hoặc loại trừ thuốc trong phiên đánh giá
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIsManualAddOpen(!isManualAddOpen)}
            className="px-2.5 py-1 bg-white hover:bg-slate-100 border border-slate-300 text-slate-800 font-bold text-[11px] flex items-center gap-1"
          >
            <Plus size={13} />
            <span>{isManualAddOpen ? 'ĐÓNG FORM' : 'THÊM THỦ CÔNG'}</span>
          </button>

          {drugs.length > 0 && (
            <button
              type="button"
              onClick={clearAll}
              className="px-2.5 py-1 bg-white hover:bg-rose-50 border border-slate-300 hover:border-rose-300 text-slate-600 hover:text-rose-700 font-bold text-[11px] transition-colors"
            >
              XÓA TẤT CẢ
            </button>
          )}
        </div>
      </div>

      {/* ── Manual Add Form ── */}
      {isManualAddOpen && (
        <div className="p-4 border-b border-slate-200 bg-slate-50 space-y-2.5">
          <span className="font-bold text-slate-900 uppercase block">THÊM THUỐC THỦ CÔNG VÀO TỦ</span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <input
              value={manualForm.brandName}
              onChange={(e) => setManualForm((p) => ({ ...p, brandName: e.target.value }))}
              placeholder="Tên biệt dược *"
              className="px-2.5 py-1.5 bg-white border border-slate-300 outline-none focus:border-slate-900"
            />
            <input
              value={manualForm.strength}
              onChange={(e) => setManualForm((p) => ({ ...p, strength: e.target.value }))}
              placeholder="Hàm lượng (VD: 500mg)"
              className="px-2.5 py-1.5 bg-white border border-slate-300 outline-none focus:border-slate-900"
            />
            <input
              value={manualForm.activeIngredient}
              onChange={(e) => setManualForm((p) => ({ ...p, activeIngredient: e.target.value }))}
              placeholder="Hoạt chất gốc (Tùy chọn)"
              className="px-2.5 py-1.5 bg-white border border-slate-300 outline-none focus:border-slate-900"
            />
          </div>
          <input
            value={manualForm.dosageInstruction}
            onChange={(e) => setManualForm((p) => ({ ...p, dosageInstruction: e.target.value }))}
            placeholder="Liều dùng (VD: 1 viên sau ăn)"
            className="w-full px-2.5 py-1.5 bg-white border border-slate-300 outline-none focus:border-slate-900"
          />
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={submitManual}
              className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-bold"
            >
              LƯU VÀO TỦ THUỐC
            </button>
          </div>
        </div>
      )}

      {/* ── Drugs List Table / Items ── */}
      {drugs.length === 0 ? (
        <div className="p-10 text-center text-slate-500 space-y-1.5">
          <p className="font-bold text-slate-800 uppercase">TỦ THUỐC ĐANG TRỐNG</p>
          <p className="text-[11px] text-slate-400 max-w-sm mx-auto">
            Hãy tải lên ảnh toa thuốc ở mục Quét hoặc sử dụng chức năng &quot;Thêm thủ công&quot; ở trên.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-slate-100">
          {drugs.map((drug) => {
            const isEditing = editingId === drug.id;

            return (
              <div
                key={drug.id}
                className={`p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 transition-colors ${
                  drug.isActive ? 'bg-white' : 'bg-slate-50/70 opacity-60'
                }`}
              >
                {/* Left Info / Edit Form */}
                <div className="flex-1 space-y-1">
                  {isEditing ? (
                    <div className="space-y-2">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <input
                          value={editForm.brandName || ''}
                          onChange={(e) => setEditForm((p) => ({ ...p, brandName: e.target.value }))}
                          placeholder="Tên thuốc"
                          className="px-2 py-1 bg-slate-50 border border-slate-300"
                        />
                        <input
                          value={editForm.strength || ''}
                          onChange={(e) => setEditForm((p) => ({ ...p, strength: e.target.value }))}
                          placeholder="Hàm lượng"
                          className="px-2 py-1 bg-slate-50 border border-slate-300"
                        />
                      </div>
                      <input
                        value={editForm.dosageInstruction || ''}
                        onChange={(e) => setEditForm((p) => ({ ...p, dosageInstruction: e.target.value }))}
                        placeholder="Liều dùng"
                        className="w-full px-2 py-1 bg-slate-50 border border-slate-300"
                      />
                    </div>
                  ) : (
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900 text-xs uppercase">{drug.brandName}</span>
                        {drug.strength && (
                          <span className="px-1.5 py-0.2 border border-slate-300 bg-slate-50 text-[10px] text-slate-700 font-bold">
                            {drug.strength}
                          </span>
                        )}
                        <span className="text-[10px] text-slate-400 uppercase">
                          ({drug.inputSource === 'prescription' ? 'Toa' : drug.inputSource === 'packaging' ? 'Vỏ hộp' : 'Thủ công'})
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        Hoạt chất: <strong className="text-slate-700">{drug.activeIngredient || drug.brandName}</strong>
                        {drug.dosageInstruction && (
                          <span> • Liều: <span className="italic">{drug.dosageInstruction}</span></span>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Right Action Controls */}
                <div className="flex items-center gap-1.5 shrink-0">
                  {isEditing ? (
                    <>
                      <button
                        type="button"
                        onClick={() => saveEdit(drug.id)}
                        className="px-2 py-1 bg-slate-900 text-white font-bold flex items-center gap-1"
                      >
                        <Check size={12} />
                        <span>LƯU</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingId(null)}
                        className="px-2 py-1 border border-slate-300 bg-slate-100 text-slate-700 font-bold"
                      >
                        HỦY
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() => toggleActive(drug.id)}
                        className={`px-2 py-1 border font-bold flex items-center gap-1 ${
                          drug.isActive
                            ? 'bg-slate-900 text-white border-slate-900'
                            : 'bg-slate-100 text-slate-400 border-slate-200'
                        }`}
                      >
                        {drug.isActive ? <Play size={11} /> : <Pause size={11} />}
                        <span>{drug.isActive ? 'ĐANG BẬT' : 'TẮT'}</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => startEdit(drug)}
                        className="p-1 border border-slate-200 bg-slate-50 text-slate-500 hover:text-slate-900"
                        title="Chỉnh sửa thông tin thuốc"
                      >
                        <Pencil size={12} />
                      </button>

                      <button
                        type="button"
                        onClick={() => removeDrug(drug.id)}
                        className="p-1 border border-slate-200 bg-slate-50 text-slate-400 hover:text-rose-600 hover:border-rose-300"
                        title="Xóa thuốc khỏi tủ"
                      >
                        <Trash2 size={12} />
                      </button>
                    </>
                  )}
                </div>

              </div>
            );
          })}
        </div>
      )}

      {/* ── Bottom Action Trigger ── */}
      {drugs.length > 0 && (
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="text-[11px] text-slate-500">
            Sẵn sàng phân tích <strong>{activeDrugs.length}</strong> thuốc đang kích hoạt theo hồ sơ y tế ({age} tuổi).
          </div>

          <button
            type="button"
            disabled={isAnalyzing || activeDrugs.length === 0}
            onClick={handleAnalyze}
            className="h-10 px-6 bg-slate-900 hover:bg-slate-800 text-white font-bold flex items-center gap-2 disabled:opacity-40 shadow-sm"
          >
            {isAnalyzing ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                <span>ĐANG ĐỐI CHIẾU LÂM SÀNG...</span>
              </>
            ) : (
              <>
                <Activity size={14} />
                <span>CHẠY ĐÁNH GIÁ TƯƠNG TÁC TỦ THUỐC</span>
              </>
            )}
          </button>
        </div>
      )}

    </div>
  );
}
