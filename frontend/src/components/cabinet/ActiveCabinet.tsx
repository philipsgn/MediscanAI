'use client';

import { useCabinetStore } from '@/store/cabinetStore';
import { IDrugEvaluationRequest, IEvaluationResponse, IUserProfile } from '@/types/medication';
import { Pill, Trash2, Play, Pause, ActivitySquare, FlaskConical, Loader2, User, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import axios from 'axios';
import { isDisclaimerAccepted, openMedicalDisclaimerModal } from '@/components/common/MedicalDisclaimerModal';
import { toast } from '@/components/common/Toast';

interface ActiveCabinetProps {
  onReportReady: (report: IEvaluationResponse) => void;
}

const COMMON_CONDITIONS = [
  'Cao huyết áp',
  'Viêm loét dạ dày',
  'Suy thận',
  'Bệnh gan',
  'Hen suyễn',
  'Mang thai'
];

const COMMON_ALLERGIES = [
  'Dị ứng Penicillin',
  'Dị ứng Aspirin/NSAID'
];

export function ActiveCabinet({ onReportReady }: ActiveCabinetProps) {
  const { drugs, removeDrug, toggleActive, clearAll } = useCabinetStore();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  
  // User Profile State for Layer 3 Evaluation
  const [age, setAge] = useState<number>(45);
  const [conditions, setConditions] = useState<string[]>([]);
  const [allergies, setAllergies] = useState<string[]>([]);

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

  const handleAnalyze = async () => {
    // 1. Enforce Medical Disclaimer Acceptance (Task 5.1)
    if (!isDisclaimerAccepted()) {
      openMedicalDisclaimerModal();
      toast.warning('Vui lòng đọc và chấp thuận Tuyên bố Miễn trừ Trách nhiệm Y tế trước khi phân tích.');
      return;
    }

    if (activeDrugs.length === 0) {
      toast.warning('Tủ thuốc trống! Hãy thêm ít nhất 1 loại thuốc trước khi phân tích.');
      return;
    }

    setIsAnalyzing(true);
    try {
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
        }))
      };

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
      const endpoint = `${apiUrl}/evaluate`;

      const res = await axios.post(endpoint, payload, { timeout: 30000 });
      const reportData = res.data as IEvaluationResponse;
      
      toast.success(`Đã phân tích thành công ${reportData.totalDrugsAnalyzed} loại thuốc!`);
      onReportReady(reportData);
    } catch (err: unknown) {
      console.error('Evaluation Error:', err);
      if (axios.isAxiosError(err)) {
        const errorDetail = err.response?.data?.detail;
        if (errorDetail) {
          toast.error(`Lỗi phân tích: ${errorDetail}`);
        } else {
          toast.error('Lỗi kết nối Backend. Hãy chắc chắn Backend đang chạy trên cổng 8000.');
        }
      } else {
        toast.error('Đã xảy ra lỗi trong quá trình đánh giá tương tác thuốc.');
      }
    } finally {
      setIsAnalyzing(false);
    }
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

      {/* Drug List */}
      <div className="divide-y divide-gray-50 max-h-[38vh] overflow-y-auto">
        {drugs.map(drug => (
          <div
            key={drug.id}
            className={cn(
              'p-3.5 flex items-start gap-3 transition-colors hover:bg-gray-50/80',
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
                {COMMON_CONDITIONS.map(cond => (
                  <button
                    key={cond}
                    type="button"
                    onClick={() => toggleCondition(cond)}
                    className={cn(
                      'px-2 py-1 rounded-md text-[11px] transition-all font-medium',
                      conditions.includes(cond)
                        ? 'bg-red-100 text-red-700 border border-red-200 font-bold'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    )}
                  >
                    {cond}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-gray-700 mb-1.5">Dị ứng thuốc:</label>
              <div className="flex flex-wrap gap-1.5">
                {COMMON_ALLERGIES.map(all => (
                  <button
                    key={all}
                    type="button"
                    onClick={() => toggleAllergy(all)}
                    className={cn(
                      'px-2 py-1 rounded-md text-[11px] transition-all font-medium',
                      allergies.includes(all)
                        ? 'bg-amber-100 text-amber-800 border border-amber-200 font-bold'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    )}
                  >
                    {all}
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
