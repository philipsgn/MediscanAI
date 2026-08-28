'use client';

/**
 * ActiveCabinet — Tủ Thuốc Đang Dùng (Material 3 Clinical Design System).
 * Rebranding: MediScan.
 */

import React, { useState, useEffect } from 'react';
import { useCabinetStore, CabinetDrugItem } from '@/store/cabinetStore';
import { IDrugEvaluationRequest, IEvaluationResponse, IUserProfile } from '@/types/medication';
import {
  Pill, Trash2, Play, Pause, Activity, Loader2,
  Pencil, Plus, Check, X
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

  // State chỉnh sửa & thêm thủ công
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
    <div className="bg-surface rounded-xl shadow-layer-1 border border-surface-container-high/50 relative overflow-hidden min-h-[400px] flex flex-col font-[var(--font-inter)] text-xs">
      
      {/* Ambient Blur Corner Effects */}
      <div className="absolute top-0 right-0 w-64 h-64 rounded-full bg-surface-container-high blur-3xl opacity-30 pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-64 h-64 rounded-full bg-surface-container-high blur-3xl opacity-30 pointer-events-none" />

      {/* ── Header inside Card ── */}
      <div className="p-5 border-b border-outline-variant/30 flex flex-wrap justify-between items-center gap-3 z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-surface-container text-primary flex items-center justify-center shrink-0">
            <Pill size={20} />
          </div>
          <div>
            <h2 className="font-bold text-primary text-sm">
              Danh mục thuốc trong tủ ({activeDrugs.length}/{drugs.length} đang bật)
            </h2>
            <p className="text-xs text-on-surface-variant mt-0.5">
              Bật hoặc tắt từng loại thuốc để đưa vào phiên đánh giá tương tác
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIsManualAddOpen(!isManualAddOpen)}
            className="px-4 py-2 border border-outline-variant text-primary font-semibold text-xs rounded-lg flex items-center gap-1.5 transition-all hover:bg-surface-container-low bg-white shadow-sm"
          >
            <Plus size={14} />
            <span>{isManualAddOpen ? 'Đóng' : 'Thêm thủ công'}</span>
          </button>

          {drugs.length > 0 && (
            <button
              type="button"
              onClick={clearAll}
              className="px-4 py-2 border border-outline-variant text-on-surface-variant hover:text-rose-600 hover:border-rose-300 font-semibold text-xs rounded-lg transition-all bg-white shadow-sm"
            >
              Xóa tất cả
            </button>
          )}
        </div>
      </div>

      {/* ── Manual Add Form ── */}
      {isManualAddOpen && (
        <div className="p-5 border-b border-outline-variant/30 bg-surface-container-low/40 space-y-3 z-10">
          <span className="font-bold text-primary text-xs block">Thêm thuốc thủ công</span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            <input
              value={manualForm.brandName}
              onChange={(e) => setManualForm((p) => ({ ...p, brandName: e.target.value }))}
              placeholder="Tên biệt dược *"
              className="px-3 py-2 bg-white border border-outline-variant rounded-lg outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 text-xs"
            />
            <input
              value={manualForm.strength}
              onChange={(e) => setManualForm((p) => ({ ...p, strength: e.target.value }))}
              placeholder="Hàm lượng (VD: 500mg)"
              className="px-3 py-2 bg-white border border-outline-variant rounded-lg outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 text-xs"
            />
            <input
              value={manualForm.activeIngredient}
              onChange={(e) => setManualForm((p) => ({ ...p, activeIngredient: e.target.value }))}
              placeholder="Hoạt chất gốc (Tùy chọn)"
              className="px-3 py-2 bg-white border border-outline-variant rounded-lg outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 text-xs"
            />
          </div>
          <input
            value={manualForm.dosageInstruction}
            onChange={(e) => setManualForm((p) => ({ ...p, dosageInstruction: e.target.value }))}
            placeholder="Liều dùng (VD: 1 viên sau ăn)"
            className="w-full px-3 py-2 bg-white border border-outline-variant rounded-lg outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 text-xs"
          />
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={submitManual}
              className="px-4 py-2.5 bg-primary hover:bg-primary-container text-on-primary font-semibold rounded-lg shadow-sm text-xs transition-all"
            >
              Lưu vào tủ thuốc
            </button>
          </div>
        </div>
      )}

      {/* ── Drugs List / Empty State ── */}
      {drugs.length === 0 ? (
        <div className="flex-grow flex flex-col items-center justify-center p-6 md:p-12 text-center space-y-4 z-10">
          <div className="w-24 h-24 rounded-full bg-surface-container-low flex items-center justify-center">
            <Pill size={40} className="text-primary/40 animate-pulse" />
          </div>
          <h3 className="text-xl font-semibold text-primary">Tủ thuốc đang trống</h3>
          <p className="text-xs text-on-surface-variant max-w-sm">
            Tải lên ảnh toa thuốc hoặc bấm 'Thêm thủ công' để tạo danh mục thuốc đang sử dụng.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-outline-variant/20 bg-white z-10 flex-grow">
          {drugs.map((drug) => {
            const isEditing = editingId === drug.id;

            return (
              <div
                key={drug.id}
                className={`p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 transition-colors ${
                  drug.isActive ? 'bg-white' : 'bg-surface-container-low/20 opacity-60'
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
                          className="px-3 py-1.5 bg-surface-container-low border border-outline-variant rounded-lg text-xs"
                        />
                        <input
                          value={editForm.strength || ''}
                          onChange={(e) => setEditForm((p) => ({ ...p, strength: e.target.value }))}
                          placeholder="Hàm lượng"
                          className="px-3 py-1.5 bg-surface-container-low border border-outline-variant rounded-lg text-xs"
                        />
                      </div>
                      <input
                        value={editForm.dosageInstruction || ''}
                        onChange={(e) => setEditForm((p) => ({ ...p, dosageInstruction: e.target.value }))}
                        placeholder="Liều dùng"
                        className="w-full px-3 py-1.5 bg-surface-container-low border border-outline-variant rounded-lg text-xs"
                      />
                    </div>
                  ) : (
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-on-surface text-xs">{drug.brandName}</span>
                        {drug.strength && (
                          <span className="px-2.5 py-0.5 rounded-full bg-surface-container text-[11px] text-primary font-bold">
                            {drug.strength}
                          </span>
                        )}
                        <span className="text-[10px] text-on-surface-variant">
                          ({drug.inputSource === 'prescription' ? 'Toa thuốc' : drug.inputSource === 'packaging' ? 'Vỏ hộp' : 'Thủ công'})
                        </span>
                      </div>
                      <div className="text-xs text-on-surface-variant mt-1">
                        Hoạt chất: <strong className="text-on-surface">{drug.activeIngredient || drug.brandName}</strong>
                        {drug.dosageInstruction && (
                          <span> • Liều: <span className="text-on-surface-variant italic">{drug.dosageInstruction}</span></span>
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
                        className="px-3 py-1.5 bg-primary text-on-primary font-semibold rounded-lg flex items-center gap-1 text-xs"
                      >
                        <Check size={13} />
                        <span>Lưu</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingId(null)}
                        className="px-3 py-1.5 border border-outline-variant bg-white text-on-surface font-semibold rounded-lg text-xs"
                      >
                        Hủy
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() => toggleActive(drug.id)}
                        className={`px-3 py-1.5 rounded-lg font-semibold text-xs flex items-center gap-1.5 transition-all ${
                          drug.isActive
                            ? 'bg-surface-container text-primary border border-outline-variant/50 hover:bg-surface-container-high'
                            : 'bg-surface-container-low/40 text-on-surface-variant border border-outline-variant/30'
                        }`}
                      >
                        {drug.isActive ? <Play size={11} className="fill-primary text-primary" /> : <Pause size={11} />}
                        <span>{drug.isActive ? 'Đang bật' : 'Tắt'}</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => startEdit(drug)}
                        className="p-2 border border-outline-variant bg-white hover:bg-surface-container-low rounded-lg text-on-surface-variant hover:text-primary transition-all"
                        title="Chỉnh sửa thông tin thuốc"
                      >
                        <Pencil size={13} />
                      </button>

                      <button
                        type="button"
                        onClick={() => removeDrug(drug.id)}
                        className="p-2 border border-outline-variant bg-white hover:bg-rose-50 hover:border-rose-200 rounded-lg text-on-surface-variant hover:text-rose-600 transition-all"
                        title="Xóa thuốc khỏi tủ"
                      >
                        <Trash2 size={13} />
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
        <div className="p-5 border-t border-outline-variant/30 bg-surface-container-low/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 z-10">
          <div className="text-xs text-on-surface-variant font-medium">
            Sẵn sàng phân tích <strong className="text-primary">{activeDrugs.length}</strong> thuốc đang kích hoạt theo hồ sơ {age} tuổi.
          </div>

          <button
            type="button"
            disabled={isAnalyzing || activeDrugs.length === 0}
            onClick={handleAnalyze}
            className="h-12 px-6 bg-primary hover:bg-primary-container text-on-primary font-semibold rounded-lg flex items-center gap-2 disabled:opacity-40 shadow-layer-1 text-xs transition-all"
          >
            {isAnalyzing ? (
              <>
                <Loader2 size={15} className="animate-spin" />
                <span>Đang đánh giá tương tác...</span>
              </>
            ) : (
              <>
                <Activity size={15} />
                <span>Đánh giá tương tác tủ thuốc</span>
              </>
            )}
          </button>
        </div>
      )}

    </div>
  );
}
