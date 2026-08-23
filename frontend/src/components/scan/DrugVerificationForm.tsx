'use client';

import { useForm } from 'react-hook-form';
import { IDrugItem, IDrugSearchResult } from '@/types/medication';
import { AlertCircle, CheckCircle2, Sun, Sunset, Moon, Coffee } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useEffect, useRef, useState } from 'react';
import { searchDrugs } from '@/services/drugService';

interface DrugVerificationFormProps {
  initialData: IDrugItem;
  onSave: (data: IDrugItem) => void;
  onCancel: () => void;
  /**
   * [P3/F4.7] Nguồn input pipeline. Dosage Selector (Sáng/Trưa/Chiều/Tối)
   * chỉ hiển thị/bắt buộc cho source_type="packaging" (vỏ hộp — người dùng tự
   * nhập liều, KHÔNG suy đoán). Với prescription, liều đã có từ toa thuốc nên
   * selector ẩn (không cho phép thay đổi tùy ý — AGENTS.md §3.B.1).
   */
  sourceType?: 'prescription' | 'packaging';
}

export function DrugVerificationForm({ initialData, onSave, onCancel, sourceType }: DrugVerificationFormProps) {
  const { register, handleSubmit, setValue, watch } = useForm<IDrugItem>({
    defaultValues: {
      ...initialData,
      dosageInstruction: initialData.dosageInstruction || '',
    }
  });

  /** [P3/F4.6] 3-tier confidence: đỏ <0.5 (rủi ro cao), vàng <0.7 (thấp), xanh ≥0.7. */
  const confidence = initialData.confidenceScore;
  const isHighRisk = confidence < 0.5;
  const isLowConfidence = confidence < 0.7 || !initialData.isVerified;
  const isPackaging = sourceType === 'packaging';

  // ── [S4-Closeout/F4.3] Autocomplete từ điển thuốc ──────────────────────────
  // Debounce ≥300ms qua services/drugService (endpoint GET /drugs/search — DB
  // thật phía backend). KHÔNG dùng danh sách tĩnh phía client dưới mọi hình thức.
  const brandNameValue = watch('brandName');
  const [suggestions, setSuggestions] = useState<IDrugSearchResult[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const term = (brandNameValue ?? '').trim();
    if (term.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }
    const timer = setTimeout(() => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      searchDrugs(term, controller.signal)
        .then((results) => {
          setSuggestions(results);
          setShowSuggestions(results.length > 0);
        })
        .catch(() => {
          // Abort khi user gõ tiếp, hoặc backend vắng mặt — im lặng,
          // KHÔNG bao giờ phá luồng Human-in-the-Loop xác minh.
        });
    }, 300);
    return () => clearTimeout(timer);
  }, [brandNameValue]);

  const applySuggestion = (s: IDrugSearchResult) => {
    setValue('brandName', s.brandName, { shouldValidate: true });
    // Chỉ điền phụ trợ nếu ô đang trống — người dùng vẫn là người quyết định cuối.
    if (s.activeIngredient && !initialData.activeIngredient) {
      setValue('activeIngredient', s.activeIngredient);
    }
    if (s.strength && !initialData.strength) {
      setValue('strength', s.strength);
    }
    setSuggestions([]);
    setShowSuggestions(false);
  };

  // Custom logic for Dosage selector
  const [dosageState, setDosageState] = useState({
    morning: false,
    noon: false,
    evening: false,
    night: false,
    qty: 1
  });

  const generateDosageString = () => {
    const times = [];
    if (dosageState.morning) times.push('Sáng');
    if (dosageState.noon) times.push('Trưa');
    if (dosageState.evening) times.push('Chiều');
    if (dosageState.night) times.push('Tối');
    
    if (times.length === 0) return '';
    return `Uống ${dosageState.qty} viên/lần vào buổi: ${times.join(', ')}`;
  };

  const applyDosage = () => {
    setValue('dosageInstruction', generateDosageString());
  };

  const toggleTime = (key: keyof typeof dosageState) => {
    setDosageState(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden w-full max-w-2xl">
      <div className={cn(
        "px-6 py-4 border-b flex items-center justify-between",
        isHighRisk ? "bg-red-50/50 border-red-100" : isLowConfidence ? "bg-amber-50/50 border-amber-100" : "bg-emerald-50/50 border-emerald-100"
      )}>
        <div className="flex items-center gap-3">
          {isHighRisk ? (
            <AlertCircle className="text-red-500" size={24} />
          ) : isLowConfidence ? (
            <AlertCircle className="text-amber-500" size={24} />
          ) : (
            <CheckCircle2 className="text-emerald-500" size={24} />
          )}
          <div>
            <h3 className={cn("font-semibold text-lg", isHighRisk ? "text-red-700" : isLowConfidence ? "text-amber-700" : "text-emerald-700")}>
              {isHighRisk ? 'Rủi ro cao — phải kiểm tra kỹ' : isLowConfidence ? 'Cần xác nhận lại thông tin' : 'AI Nhận diện mức độ tin cậy cao'}
            </h3>
            <p className={cn("text-sm", isHighRisk ? "text-red-600" : isLowConfidence ? "text-amber-600" : "text-emerald-600")}>
              Độ tin cậy: {Math.round(initialData.confidenceScore * 100)}%
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit((data) => onSave({ ...data, isVerified: true }))} className="p-6 space-y-5">
        
        <div className="grid grid-cols-2 gap-5">
          <div className="space-y-1.5 relative">
            <label className="text-sm font-medium text-gray-700">Tên thương mại <span className="text-red-500">*</span></label>
            <input 
              {...register('brandName', { required: true })}
              className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow outline-none"
              placeholder="VD: Panadol Extra"
              autoComplete="off"
            />
            {/* [S4-Closeout/F4.3] Dropdown gợi ý từ DB thật (GET /drugs/search) */}
            {showSuggestions && (
              <div className="absolute z-20 left-0 right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                {suggestions.map((s) => (
                  <button
                    key={s.drugId}
                    type="button"
                    onClick={() => applySuggestion(s)}
                    className="w-full text-left px-3 py-2 hover:bg-blue-50 focus:bg-blue-50 transition-colors"
                  >
                    <span className="text-sm font-medium text-gray-800">{s.brandName}</span>
                    {s.activeIngredient && (
                      <span className="text-xs text-gray-500"> — {s.activeIngredient}</span>
                    )}
                    {s.strength && <span className="text-xs text-gray-400"> ({s.strength})</span>}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Hàm lượng</label>
            <input 
              {...register('strength')}
              className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow outline-none"
              placeholder="VD: 500mg"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-sm font-medium text-gray-700">Hoạt chất gốc (Chuẩn hóa)</label>
          <input 
            {...register('activeIngredient')}
            className="w-full px-4 py-2.5 rounded-lg border border-gray-300 bg-gray-50 focus:ring-2 focus:ring-blue-500 outline-none"
            placeholder="AI sẽ tự động điền nếu trống"
          />
        </div>

        {/* [P3/F4.7] Cấu hình liều dùng nhanh — CHỈ hiển thị cho pipeline vỏ hộp (packaging). Với toa thuốc (prescription), liều đã có sẵn, cấm người dùng tự suy đoán/sửa tùy ý. */}
        {isPackaging && (
        <div className="bg-blue-50/50 rounded-xl p-4 border border-blue-100">
          <p className="text-sm font-medium text-blue-800 mb-3">Tạo nhanh hướng dẫn liều dùng</p>
          
          <div className="flex items-center gap-3 mb-4">
            <span className="text-sm text-gray-600">Số lượng / lần:</span>
            <input 
              type="number" 
              value={dosageState.qty}
              onChange={(e) => setDosageState(p => ({ ...p, qty: Number(e.target.value) }))}
              className="w-20 px-3 py-1.5 rounded-lg border border-gray-300 text-center outline-none" 
              min={0.5} step={0.5}
            />
          </div>

          <div className="flex gap-2">
            <button type="button" onClick={() => toggleTime('morning')} className={cn("flex-1 py-2 rounded-lg border flex flex-col items-center justify-center gap-1 transition-colors", dosageState.morning ? "bg-blue-500 text-white border-blue-600" : "bg-white text-gray-600 hover:bg-gray-50")}>
              <Coffee size={18} /> <span className="text-xs font-medium">Sáng</span>
            </button>
            <button type="button" onClick={() => toggleTime('noon')} className={cn("flex-1 py-2 rounded-lg border flex flex-col items-center justify-center gap-1 transition-colors", dosageState.noon ? "bg-amber-500 text-white border-amber-600" : "bg-white text-gray-600 hover:bg-gray-50")}>
              <Sun size={18} /> <span className="text-xs font-medium">Trưa</span>
            </button>
            <button type="button" onClick={() => toggleTime('evening')} className={cn("flex-1 py-2 rounded-lg border flex flex-col items-center justify-center gap-1 transition-colors", dosageState.evening ? "bg-orange-500 text-white border-orange-600" : "bg-white text-gray-600 hover:bg-gray-50")}>
              <Sunset size={18} /> <span className="text-xs font-medium">Chiều</span>
            </button>
            <button type="button" onClick={() => toggleTime('night')} className={cn("flex-1 py-2 rounded-lg border flex flex-col items-center justify-center gap-1 transition-colors", dosageState.night ? "bg-indigo-600 text-white border-indigo-700" : "bg-white text-gray-600 hover:bg-gray-50")}>
              <Moon size={18} /> <span className="text-xs font-medium">Tối</span>
            </button>
          </div>
          <button type="button" onClick={applyDosage} className="mt-3 w-full py-2 bg-blue-100 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-200 transition-colors">
            Áp dụng xuống ô Hướng dẫn
          </button>
        </div>
        )}

        <div className="space-y-1.5">
          <label className="text-sm font-medium text-gray-700">Hướng dẫn liều dùng thực tế</label>
          <textarea 
            {...register('dosageInstruction')}
            rows={2}
            className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow outline-none resize-none"
            placeholder="VD: Uống 1 viên sau khi ăn sáng"
          />
        </div>

        <div className="pt-4 flex gap-3 justify-end border-t border-gray-100">
          <button type="button" onClick={onCancel} className="px-6 py-2.5 rounded-lg text-gray-600 font-medium hover:bg-gray-100 transition-colors">
            Hủy bỏ
          </button>
          <button type="submit" className="px-6 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 shadow-sm transition-colors active:scale-95">
            Xác nhận & Thêm
          </button>
        </div>
      </form>
    </div>
  );
}
