'use client';

import { useState, useEffect, useCallback } from 'react';
import { ShieldCheck, AlertTriangle, ChevronRight, Heart, Info, Stethoscope } from 'lucide-react';

const DISCLAIMER_KEY = 'mediscan_disclaimer_accepted';

export function isDisclaimerAccepted(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem(DISCLAIMER_KEY) === 'true';
}

export function openMedicalDisclaimerModal() {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent('open-medical-disclaimer'));
}

export function MedicalDisclaimerModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [checked, setChecked] = useState(false);

  const checkInitialStatus = useCallback(() => {
    const accepted = localStorage.getItem(DISCLAIMER_KEY);
    if (!accepted) {
      // Delay 300ms to let layout render first
      const t = setTimeout(() => setIsOpen(true), 300);
      return () => clearTimeout(t);
    }
  }, []);

  useEffect(() => {
    checkInitialStatus();

    const handleOpenEvent = () => {
      setChecked(isDisclaimerAccepted());
      setIsOpen(true);
    };

    window.addEventListener('open-medical-disclaimer', handleOpenEvent);
    return () => {
      window.removeEventListener('open-medical-disclaimer', handleOpenEvent);
    };
  }, [checkInitialStatus]);

  const handleAccept = () => {
    if (!checked) return;
    localStorage.setItem(DISCLAIMER_KEY, 'true');
    setIsOpen(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden animate-in zoom-in-95 duration-300 border border-gray-100 my-8">

        {/* Header */}
        <div className="bg-gradient-to-br from-blue-600 via-indigo-600 to-indigo-800 px-6 pt-8 pb-6 text-white text-center relative overflow-hidden">
          <div className="absolute -top-12 -right-12 w-36 h-36 bg-white/10 rounded-full blur-xl pointer-events-none" />
          <div className="w-16 h-16 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-inner ring-4 ring-white/10">
            <ShieldCheck size={36} className="text-white" />
          </div>
          <h2 className="text-2xl font-extrabold tracking-tight">Tuyên Bố Miễn Trừ Trách Nhiệm Y Tế</h2>
          <p className="text-blue-100 text-sm mt-1 flex items-center justify-center gap-1.5 font-medium">
            <Stethoscope size={15} /> Medical Safety & Legal Terms
          </p>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-3.5 max-h-[60vh] overflow-y-auto">
          {[
            {
              icon: '🔬',
              title: 'Hỗ trợ tra cứu tham khảo',
              text: 'Mediscan AI là công cụ hỗ trợ tra cứu thông tin tương tác thuốc, hoạt động dựa trên mô hình trí tuệ nhân tạo (VLM/LLM) và cơ sở dữ liệu y khoa tổng hợp.'
            },
            {
              icon: '⚕️',
              title: 'Không thay thế chỉ định Bác sĩ',
              text: 'Kết quả phân tích KHÔNG có giá trị thay thế cho chẩn đoán, toa thuốc, đơn thuốc hoặc phác đồ điều trị từ Bác sĩ, Dược sĩ có chứng chỉ hành nghề.'
            },
            {
              icon: '⚠️',
              title: 'Không tự ý thay đổi phác đồ',
              text: 'Người dùng tuyệt đối không tự ý ngừng thuốc, đổi thuốc, tăng hoặc giảm liều lượng chỉ dựa trên kết quả hoặc cảnh báo của ứng dụng này.'
            },
            {
              icon: '💊',
              title: 'Tham vấn chuyên môn khi có nghi ngờ',
              text: 'Trong mọi tình huống nghi ngờ xung đột thuốc hoặc có phản ứng bất lợi, hãy lập tức liên hệ Bác sĩ điều trị hoặc trung tâm y tế gần nhất.'
            },
          ].map((item, i) => (
            <div key={i} className="flex items-start gap-3 bg-gray-50/80 hover:bg-gray-50 border border-gray-100 rounded-xl p-3.5 transition-colors">
              <span className="text-xl shrink-0 mt-0.5">{item.icon}</span>
              <div>
                <h4 className="text-xs font-bold text-gray-800 uppercase tracking-wider mb-0.5">{item.title}</h4>
                <p className="text-xs text-gray-600 leading-relaxed">{item.text}</p>
              </div>
            </div>
          ))}

          {/* Warning notice */}
          <div className="bg-amber-50/90 border border-amber-200 rounded-xl p-3.5 flex items-start gap-2.5">
            <AlertTriangle className="text-amber-600 shrink-0 mt-0.5" size={18} />
            <p className="text-xs text-amber-800 leading-relaxed">
              <strong>Điều khoản pháp lý:</strong> Đội ngũ phát triển Mediscan AI được miễn trừ mọi trách nhiệm pháp lý đối với bất kỳ tổn hại sức khỏe, biến chứng nào phát sinh do việc sử dụng sai mục đích hoặc không tuân thủ chỉ định của nhân viên y tế.
            </p>
          </div>

          {/* Checkbox */}
          <label className="flex items-start gap-3 cursor-pointer group pt-2 select-none">
            <div className="relative shrink-0 mt-0.5">
              <input
                type="checkbox"
                className="sr-only"
                checked={checked}
                onChange={e => setChecked(e.target.checked)}
              />
              <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all ${
                checked
                  ? 'bg-blue-600 border-blue-600 shadow-sm'
                  : 'border-gray-300 bg-white group-hover:border-blue-400'
              }`}>
                {checked && (
                  <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
            </div>
            <span className="text-xs text-gray-700 leading-relaxed font-medium">
              Tôi hiểu rằng <strong className="text-blue-900">Mediscan AI chỉ là công cụ hỗ trợ tra cứu tham khảo</strong> và không thay thế chỉ định từ Bác sĩ/Dược sĩ.
            </span>
          </label>
        </div>

        {/* Footer */}
        <div className="px-6 pb-6 pt-2 bg-gray-50/50 border-t border-gray-100">
          <button
            onClick={handleAccept}
            disabled={!checked}
            className={`w-full py-3.5 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-sm ${
              checked
                ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-blue-200 active:scale-[0.98]'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            <Heart size={16} className={checked ? 'fill-current' : ''} />
            Tôi Hiểu & Đồng Ý Tiếp Tục
            {checked && <ChevronRight size={16} />}
          </button>
          <div className="flex items-center justify-center gap-1 text-[11px] text-gray-400 mt-2.5">
            <Info size={12} />
            <span>Trạng thái chấp thuận được ghi nhớ trên trình duyệt này</span>
          </div>
        </div>

      </div>
    </div>
  );
}
