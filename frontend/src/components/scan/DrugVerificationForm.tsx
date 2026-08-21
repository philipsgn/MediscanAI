'use client';

import { useForm } from 'react-hook-form';
import { IDrugItem } from '@/types/medication';
import { AlertCircle, CheckCircle2, Sun, Sunset, Moon, Coffee } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState } from 'react';

interface DrugVerificationFormProps {
  initialData: IDrugItem;
  onSave: (data: IDrugItem) => void;
  onCancel: () => void;
}

export function DrugVerificationForm({ initialData, onSave, onCancel }: DrugVerificationFormProps) {
  const { register, handleSubmit, setValue } = useForm<IDrugItem>({
    defaultValues: {
      ...initialData,
      dosageInstruction: initialData.dosageInstruction || '',
    }
  });

  const isLowConfidence = initialData.confidenceScore < 0.7 || !initialData.isVerified;

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
        isLowConfidence ? "bg-amber-50/50 border-amber-100" : "bg-emerald-50/50 border-emerald-100"
      )}>
        <div className="flex items-center gap-3">
          {isLowConfidence ? (
            <AlertCircle className="text-amber-500" size={24} />
          ) : (
            <CheckCircle2 className="text-emerald-500" size={24} />
          )}
          <div>
            <h3 className={cn("font-semibold text-lg", isLowConfidence ? "text-amber-700" : "text-emerald-700")}>
              {isLowConfidence ? 'Cần xác nhận lại thông tin' : 'AI Nhận diện mức độ tin cậy cao'}
            </h3>
            <p className={cn("text-sm", isLowConfidence ? "text-amber-600" : "text-emerald-600")}>
              Độ tin cậy: {Math.round(initialData.confidenceScore * 100)}%
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit((data) => onSave({ ...data, isVerified: true }))} className="p-6 space-y-5">
        
        <div className="grid grid-cols-2 gap-5">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">Tên thương mại <span className="text-red-500">*</span></label>
            <input 
              {...register('brandName', { required: true })}
              className="w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow outline-none"
              placeholder="VD: Panadol Extra"
            />
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

        {/* Cấu hình liều dùng nhanh */}
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
