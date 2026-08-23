'use client';

import { useState, useRef } from 'react';
import { FileText, Box, Loader2, Sparkles, ShieldCheck, CheckCircle2, AlertCircle, Info } from 'lucide-react';
import { SmartCropModal } from '@/components/scan/SmartCropModal';
import { DrugVerificationForm } from '@/components/scan/DrugVerificationForm';
import { ActiveCabinet } from '@/components/cabinet/ActiveCabinet';
import { InteractionAlertCards } from '@/components/report/InteractionAlertCards';
import { openMedicalDisclaimerModal } from '@/components/common/MedicalDisclaimerModal';
import { toast } from '@/components/common/Toast';
import { useCabinetStore } from '@/store/cabinetStore';
import { IDrugItem, IEvaluationResponse } from '@/types/medication';
import { scanImage, mapFullScanToDrugs } from '@/services/ocrService';
import { isAxiosError } from 'axios';

const MAX_FILE_SIZE_MB = 15;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg', 'image/heic'];

export default function ScanPage() {
  const { addDrug } = useCabinetStore();

  const [sourceType, setSourceType] = useState<'prescription' | 'packaging' | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState<1 | 2 | 3>(1);
  const [rawImageUrl, setRawImageUrl] = useState<string | null>(null);
  const [isCropModalOpen, setIsCropModalOpen] = useState(false);
  const [verificationQueue, setVerificationQueue] = useState<IDrugItem[]>([]);
  const [report, setReport] = useState<IEvaluationResponse | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): boolean => {
    if (!ALLOWED_IMAGE_TYPES.includes(file.type) && !file.type.startsWith('image/')) {
      toast.error('Định dạng tệp không hợp lệ! Vui lòng chọn ảnh JPG, PNG hoặc WEBP.');
      return false;
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      toast.error(`Kích thước ảnh quá lớn (${(file.size / (1024 * 1024)).toFixed(1)}MB)! Tối đa ${MAX_FILE_SIZE_MB}MB.`);
      return false;
    }
    return true;
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !sourceType) return;

    if (!validateFile(file)) {
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    const url = URL.createObjectURL(file);
    setRawImageUrl(url);

    if (sourceType === 'packaging') {
      setIsCropModalOpen(true);
    } else {
      processImage(file, 'prescription');
    }

    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleCropComplete = async (base64Image: string) => {
    setIsCropModalOpen(false);
    try {
      const res = await fetch(base64Image);
      const blob = await res.blob();
      const file = new File([blob], 'cropped.jpg', { type: 'image/jpeg' });
      processImage(file, 'packaging');
    } catch {
      toast.error('Không thể xử lý ảnh cắt. Vui lòng thử lại.');
      setIsProcessing(false);
      setRawImageUrl(null);
    }
  };

  const processImage = async (file: File, type: 'prescription' | 'packaging') => {
    setIsProcessing(true);
    setProcessingStep(1);

    // Dynamic step progression for UX
    const stepTimer1 = setTimeout(() => setProcessingStep(2), 600);
    const stepTimer2 = setTimeout(() => setProcessingStep(3), 1800);

    try {
      // [P0/F4.1+F4.2] Gọi qua services tập trung (services/api.ts + ocrService.ts):
      // hết hardcode URL/path; map mappedDrugs (FullScanResponse thật) thay vì
      // data.items (hợp đồng cũ đã chết từ pivot Stage 2→3).
      const data = await scanImage(file, type);
      const items = mapFullScanToDrugs(data);
      if (items.length > 0) {
        setVerificationQueue(items);
        toast.success(`AI đã nhận diện thành công ${items.length} loại thuốc từ ${type === 'prescription' ? 'toa thuốc' : 'vỏ hộp'}!`);
      } else {
        toast.warning('Không tìm thấy thông tin thuốc rõ ràng trong ảnh. Vui lòng thử lại với ảnh rõ nét hơn.');
      }
    } catch (error: unknown) {
      console.error('Scan Error:', error);
      if (isAxiosError(error)) {
        const errorDetail = error.response?.data?.detail;
        if (errorDetail) {
          toast.error(`Lỗi từ máy chủ: ${errorDetail}`);
        } else if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
          toast.error('Quá thời gian kết nối (Timeout). Vui lòng thử lại với ảnh nhỏ hơn.');
        } else {
          toast.error('Không thể kết nối đến Backend AI (cổng 8000). Hãy đảm bảo Backend đang chạy.');
        }
      } else {
        toast.error('Đã xảy ra lỗi không xác định trong quá trình phân tích ảnh.');
      }
    } finally {
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      setIsProcessing(false);
      setRawImageUrl(null);
    }
  };

  const handleVerificationSave = (verifiedDrug: IDrugItem) => {
    addDrug({ ...verifiedDrug, inputSource: sourceType || 'manual' });
    toast.success(`Đã thêm "${verifiedDrug.brandName}" vào Tủ thuốc!`);
    const remaining = verificationQueue.slice(1);
    setVerificationQueue(remaining);
    if (remaining.length === 0) setSourceType(null);
  };

  const handleVerificationCancel = () => {
    toast.info('Đã bỏ qua loại thuốc này.');
    const remaining = verificationQueue.slice(1);
    setVerificationQueue(remaining);
    if (remaining.length === 0) setSourceType(null);
  };

  const currentVerificationItem = verificationQueue[0];

  // === REPORT SCREEN ===
  if (report) {
    return (
      <div className="min-h-screen bg-gray-50/50 p-6 font-sans">
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="flex items-center justify-between flex-wrap gap-4 border-b pb-4">
            <div>
              <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight flex items-center gap-2.5">
                <span>Báo Cáo Phân Tích An Toàn Thuốc</span>
                <span className="text-xs bg-blue-100 text-blue-800 font-semibold px-2.5 py-0.5 rounded-full">AI 3-Layer</span>
              </h1>
              <p className="text-gray-500 text-sm mt-1">
                Kết quả kiểm tra tương tác thuốc, chống chỉ định và quá liều hoạt chất
              </p>
            </div>
            <button
              onClick={() => openMedicalDisclaimerModal()}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-600 bg-white border border-gray-200 px-3 py-1.5 rounded-lg hover:bg-gray-50 hover:text-blue-600 transition-colors shadow-sm"
            >
              <ShieldCheck size={14} className="text-blue-600" />
              Tuyên bố Miễn trừ Y tế
            </button>
          </div>
          <InteractionAlertCards result={report} onClose={() => setReport(null)} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 via-white to-gray-50 p-6 font-sans">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Top Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-gray-100 pb-6">
          <div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
                <Sparkles size={22} />
              </div>
              <div>
                <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">Mediscan AI</h1>
                <p className="text-gray-500 text-sm font-medium">Trợ lý cảnh báo tương tác & an toàn thuốc thông minh</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => openMedicalDisclaimerModal()}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-600 bg-white border border-gray-200 px-3.5 py-2 rounded-xl hover:bg-gray-50 hover:text-blue-600 transition-colors shadow-sm"
              title="Xem quy định miễn trừ trách nhiệm y tế"
            >
              <ShieldCheck size={15} className="text-blue-600" />
              <span>Điều khoản Miễn trừ Y tế</span>
            </button>
          </div>
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Left Column: Scanner & Verification */}
          <div className="lg:col-span-7 space-y-6">
            {!currentVerificationItem && !isProcessing && (
              <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 flex flex-col gap-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-gray-900 text-lg">Tải lên hình ảnh đơn hoặc thuốc</h3>
                    <p className="text-gray-500 text-xs mt-0.5">Chọn đúng loại tài liệu để AI tối ưu hóa độ chính xác</p>
                  </div>
                  <span className="text-xs bg-blue-50 text-blue-700 font-medium px-2.5 py-1 rounded-md flex items-center gap-1">
                    <Info size={13} /> Max {MAX_FILE_SIZE_MB}MB
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <button
                    onClick={() => { setSourceType('prescription'); fileInputRef.current?.click(); }}
                    className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-emerald-200 bg-emerald-50/20 rounded-2xl hover:bg-emerald-50 hover:border-emerald-400 transition-all duration-200 group text-center"
                  >
                    <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-sm">
                      <FileText className="text-emerald-600" size={32} />
                    </div>
                    <span className="font-bold text-emerald-900 text-base">Quét Toa Thuốc In</span>
                    <span className="text-xs text-emerald-600 mt-1 max-w-[180px]">Đọc tự động danh sách nhiều thuốc và liều dùng</span>
                  </button>

                  <button
                    onClick={() => { setSourceType('packaging'); fileInputRef.current?.click(); }}
                    className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-purple-200 bg-purple-50/20 rounded-2xl hover:bg-purple-50 hover:border-purple-400 transition-all duration-200 group text-center"
                  >
                    <div className="w-16 h-16 bg-purple-100 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-sm">
                      <Box className="text-purple-600" size={32} />
                    </div>
                    <span className="font-bold text-purple-900 text-base">Quét Vỏ Hộp / Lọ</span>
                    <span className="text-xs text-purple-600 mt-1 max-w-[180px]">Smart Crop nhãn tên thuốc & hàm lượng nhanh</span>
                  </button>
                </div>

                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/jpg,image/heic"
                  className="hidden"
                  ref={fileInputRef}
                  onChange={handleFileSelect}
                />
              </div>
            )}

            {/* Processing State with Animated Skeleton */}
            {isProcessing && (
              <div className="bg-white p-8 rounded-2xl shadow-sm border border-blue-100 flex flex-col gap-6 animate-in fade-in duration-300">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
                    <Loader2 className="animate-spin" size={24} />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-gray-900">AI Đang Phân Tích Hình Ảnh</h3>
                    <p className="text-xs text-gray-500 mt-0.5">Hệ thống đang trích xuất dữ liệu y tế và chuẩn hóa hoạt chất gốc</p>
                  </div>
                </div>

                {/* Stepper Progress */}
                <div className="space-y-3 bg-gray-50 rounded-xl p-4 border border-gray-100">
                  <div className="flex items-center gap-3">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                      processingStep >= 1 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'
                    }`}>
                      {processingStep > 1 ? <CheckCircle2 size={14} /> : '1'}
                    </div>
                    <span className={`text-xs font-semibold ${processingStep >= 1 ? 'text-gray-800' : 'text-gray-400'}`}>
                      Tiếp nhận & tiền xử lý hình ảnh y tế
                    </span>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                      processingStep >= 2 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'
                    }`}>
                      {processingStep > 2 ? <CheckCircle2 size={14} /> : processingStep === 2 ? <Loader2 size={14} className="animate-spin" /> : '2'}
                    </div>
                    <span className={`text-xs font-semibold ${processingStep >= 2 ? 'text-gray-800' : 'text-gray-400'}`}>
                      Trích xuất thông tin thuốc bằng mô hình OCR tự huấn luyện on-premise
                    </span>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                      processingStep >= 3 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'
                    }`}>
                      {processingStep === 3 ? <Loader2 size={14} className="animate-spin" /> : '3'}
                    </div>
                    <span className={`text-xs font-semibold ${processingStep >= 3 ? 'text-gray-800' : 'text-gray-400'}`}>
                      Đối soát từ điển Thuốc Việt Nam & chuẩn hóa hoạt chất gốc
                    </span>
                  </div>
                </div>

                {/* Skeleton Preview Cards */}
                <div className="space-y-3 pt-2">
                  <div className="h-4 bg-gray-200 rounded w-1/3 animate-pulse" />
                  <div className="p-4 border border-gray-100 rounded-xl space-y-2 bg-gray-50/50">
                    <div className="h-4 bg-gray-200 rounded w-1/2 animate-pulse" />
                    <div className="h-3 bg-gray-200 rounded w-3/4 animate-pulse" />
                  </div>
                  <div className="p-4 border border-gray-100 rounded-xl space-y-2 bg-gray-50/50">
                    <div className="h-4 bg-gray-200 rounded w-2/5 animate-pulse" />
                    <div className="h-3 bg-gray-200 rounded w-2/3 animate-pulse" />
                  </div>
                </div>
              </div>
            )}

            {/* Human-in-the-loop Verification Form */}
            {currentVerificationItem && !isProcessing && (
              <div className="animate-in fade-in slide-in-from-bottom-4 duration-400">
                <div className="mb-4 flex items-center justify-between">
                  <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-100 text-blue-800 text-xs font-bold rounded-full shadow-sm">
                    <AlertCircle size={14} />
                    Xác nhận thuốc ({verificationQueue.length} mục còn lại)
                  </span>
                  <span className="text-xs text-gray-500">
                    Bước kiểm duyệt Human-in-the-Loop (HITL)
                  </span>
                </div>
                <DrugVerificationForm
                  key={currentVerificationItem.brandName}
                  initialData={currentVerificationItem}
                  onSave={handleVerificationSave}
                  onCancel={handleVerificationCancel}
                  sourceType={sourceType ?? undefined}
                />
              </div>
            )}
          </div>

          {/* Right Column: Active Cabinet */}
          <div className="lg:col-span-5">
            <div className="sticky top-6">
              <ActiveCabinet onReportReady={(r) => setReport(r)} />
            </div>
          </div>
        </div>
      </div>

      {rawImageUrl && (
        <SmartCropModal
          key={rawImageUrl}
          isOpen={isCropModalOpen}
          imageUrl={rawImageUrl}
          onClose={() => { setIsCropModalOpen(false); setRawImageUrl(null); setSourceType(null); }}
          onCropComplete={handleCropComplete}
        />
      )}
    </div>
  );
}
