'use client';

/**
 * High-Precision Pure OCR Scanning & 2-Column Clinical Verification — Route /scan.
 * Cột 1: Bảng điều khiển nạp ảnh, OCR Pure-ONNX & HITL Verification Form.
 * Cột 2: Danh mục hoạt chất chuẩn hóa, Đánh giá tương tác 4 lớp & Nút [LƯU VÀO TỦ THUỐC].
 * Minimalist Clinical Design Standard (#0F172A, #334155, #FFFFFF, #E2E8F0, rounded-none / rounded-sm).
 */

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  FileText, Box, Loader2, Sparkles, ShieldCheck, CheckCircle2,
  AlertCircle, ArrowRight, ArrowLeft, Upload, RotateCcw, Pill,
  Activity, Check, Layers, AlertTriangle
} from 'lucide-react';
import { SmartCropModal } from '@/components/scan/SmartCropModal';
import { DrugVerificationForm } from '@/components/scan/DrugVerificationForm';
import { InteractionAlertCards } from '@/components/report/InteractionAlertCards';
import { openMedicalDisclaimerModal, isDisclaimerAccepted } from '@/components/common/MedicalDisclaimerModal';
import { toast } from '@/components/common/Toast';
import { useCabinetStore } from '@/store/cabinetStore';
import { IDrugItem, IEvaluationResponse } from '@/types/medication';
import { scanImage, mapFullScanToDrugs } from '@/services/ocrService';
import { useEvaluation } from '@/services/evaluationService';
import { useUserProfileStore } from '@/store/userProfileStore';
import { isAxiosError } from 'axios';

const MAX_FILE_SIZE_MB = 15;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg', 'image/heic'];

export default function ScanPage() {
  const router = useRouter();
  const { addDrug, addDrugs, drugs: cabinetDrugs } = useCabinetStore();
  const { profile } = useUserProfileStore();
  const { mutate: runEvaluate, isPending: isEvaluating } = useEvaluation();

  const [sourceType, setSourceType] = useState<'prescription' | 'packaging'>('prescription');
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState<1 | 2 | 3>(1);
  const [rawImageUrl, setRawImageUrl] = useState<string | null>(null);
  const [isCropModalOpen, setIsCropModalOpen] = useState(false);

  // Danh sách thuốc trích xuất từ phiên scan hiện tại
  const [extractedDrugs, setExtractedDrugs] = useState<IDrugItem[]>([]);
  const [verificationQueue, setVerificationQueue] = useState<IDrugItem[]>([]);
  const [evaluationResult, setEvaluationResult] = useState<IEvaluationResponse | null>(null);

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
    if (!file) return;

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

    const stepTimer1 = setTimeout(() => setProcessingStep(2), 600);
    const stepTimer2 = setTimeout(() => setProcessingStep(3), 1800);

    try {
      const data = await scanImage(file, type);
      const items = mapFullScanToDrugs(data);
      if (items.length > 0) {
        setVerificationQueue(items);
        setExtractedDrugs((prev) => [...prev, ...items]);
        toast.success(`AI Pure-ONNX đã nhận diện thành công ${items.length} thuốc!`);
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
        toast.error('Đã xảy ra lỗi trong quá trình phân tích ảnh OCR.');
      }
    } finally {
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      setIsProcessing(false);
    }
  };

  const handleVerificationSave = (verifiedDrug: IDrugItem) => {
    addDrug({ ...verifiedDrug, inputSource: sourceType });
    toast.success(`Đã xác thực "${verifiedDrug.brandName}"!`);
    const remaining = verificationQueue.slice(1);
    setVerificationQueue(remaining);
  };

  const handleVerificationCancel = () => {
    toast.info('Đã bỏ qua loại thuốc này.');
    const remaining = verificationQueue.slice(1);
    setVerificationQueue(remaining);
  };

  // Kích hoạt đánh giá tương tác lâm sàng
  const handleRunClinicalEvaluation = () => {
    if (!isDisclaimerAccepted()) {
      openMedicalDisclaimerModal();
      toast.warning('Vui lòng đọc và chấp thuận Tuyên bố Miễn trừ Trách nhiệm Y tế.');
      return;
    }

    const allItemsToEvaluate = extractedDrugs.length > 0 ? extractedDrugs : cabinetDrugs;

    if (allItemsToEvaluate.length === 0) {
      toast.warning('Chưa có thuốc nào để đánh giá! Hãy quét hoặc thêm thuốc.');
      return;
    }

    runEvaluate(
      {
        drugs: allItemsToEvaluate.map((d) => ({
          brandName: d.brandName,
          strength: d.strength || '',
          activeIngredient: d.activeIngredient || d.brandName,
          dosageInstruction: d.dosageInstruction || '',
          confidenceScore: d.confidenceScore || 1.0,
          isVerified: d.isVerified ?? true,
        })),
        userProfile: {
          age: profile?.age ?? 35,
          gender: profile?.gender ?? 'male',
          conditions: profile?.conditions ?? [],
          allergies: profile?.allergies ?? [],
          isPregnant: profile?.isPregnant ?? false,
          isBreastfeeding: profile?.isBreastfeeding ?? false,
          weightKg: profile?.weightKg,
          heightCm: profile?.heightCm,
        },
      },
      {
        onSuccess: (data) => {
          setEvaluationResult(data);
          toast.success('Đã hoàn tất đánh giá tương tác lâm sàng 4 lớp!');
        },
        onError: (err) => {
          toast.error('Lỗi khi đánh giá tương tác lâm sàng.');
          console.error(err);
        },
      }
    );
  };

  // Nút [LƯU VÀO TỦ THUỐC]: Chuyển toàn bộ thuốc đã scan vào cabinetStore & về /cabinet
  const handleSaveAllToCabinet = () => {
    if (extractedDrugs.length === 0) {
      toast.warning('Chưa có danh sách thuốc nào được trích xuất.');
      return;
    }

    const itemsToSave = extractedDrugs.map((d) => ({
      ...d,
      inputSource: sourceType,
      confidenceScore: d.confidenceScore || 1.0,
      isVerified: true,
    }));

    addDrugs(itemsToSave);
    toast.success(`Đã lưu ${itemsToSave.length} thuốc vào Tủ thuốc thành công!`);
    router.push('/cabinet');
  };

  const currentVerificationItem = verificationQueue[0];

  return (
    <div className="min-h-full bg-slate-50 font-[var(--font-inter)] text-slate-900 pb-16">
      
      {/* ── Top Bar ── */}
      <div className="bg-white border-b border-slate-200 py-3.5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link
              href="/cabinet"
              className="h-8 px-2.5 border border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-mono font-bold flex items-center gap-1.5 transition-colors"
            >
              <ArrowLeft size={13} />
              <span>TỦ THUỐC</span>
            </Link>
            <div>
              <span className="text-[10px] font-mono font-bold text-slate-500 uppercase block">
                PHÂN KHU QUÉT [03]
              </span>
              <h1 className="text-base font-black tracking-tight text-slate-900 uppercase">
                Trích Xuất Pure-ONNX & Đối Chiếu Lâm Sàng
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => openMedicalDisclaimerModal()}
              className="h-8 px-3 border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-mono font-bold flex items-center gap-1.5"
            >
              <ShieldCheck size={13} className="text-slate-500" />
              <span>MIỄN TRỪ Y TẾ</span>
            </button>

            {extractedDrugs.length > 0 && (
              <button
                type="button"
                onClick={handleSaveAllToCabinet}
                className="h-8 px-4 bg-slate-900 hover:bg-slate-800 text-white text-xs font-mono font-bold flex items-center gap-1.5 shadow-sm"
              >
                <Check size={13} />
                <span>[LƯU VÀO TỦ THUỐC]</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── Main 2-Column Grid Workspace ── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 pt-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* ════════ COLUMN 1: EXTRACTION & INPUT STREAM (5 COLS) ════════ */}
          <div className="lg:col-span-5 space-y-4">
            
            {/* Stream Selector */}
            <div className="bg-white border border-slate-200 p-3.5 space-y-3">
              <span className="text-xs font-mono font-bold text-slate-700 uppercase block">
                1. CHỌN LUỒNG ĐẦU VÀO (INPUT STREAM)
              </span>

              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setSourceType('prescription')}
                  className={`p-2.5 text-left border font-mono text-xs transition-colors ${
                    sourceType === 'prescription'
                      ? 'bg-slate-900 text-white border-slate-900'
                      : 'bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100'
                  }`}
                >
                  <FileText size={15} className="mb-1" />
                  <span className="font-bold block">TOA THUỐC TOÀN TRANG</span>
                  <span className={`text-[10px] ${sourceType === 'prescription' ? 'text-slate-400' : 'text-slate-500'}`}>
                    Đọc tên, hàm lượng & liều
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setSourceType('packaging')}
                  className={`p-2.5 text-left border font-mono text-xs transition-colors ${
                    sourceType === 'packaging'
                      ? 'bg-slate-900 text-white border-slate-900'
                      : 'bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100'
                  }`}
                >
                  <Box size={15} className="mb-1" />
                  <span className="font-bold block">VỎ HỘP (SMART CROP)</span>
                  <span className={`text-[10px] ${sourceType === 'packaging' ? 'text-slate-400' : 'text-slate-500'}`}>
                    Cắt nhãn & nhập liều tay
                  </span>
                </button>
              </div>
            </div>

            {/* Upload Drag & Drop Dropzone */}
            <div className="bg-white border border-slate-200 p-4 space-y-3">
              <span className="text-xs font-mono font-bold text-slate-700 uppercase block">
                2. NẠP ẢNH TÀI LIỆU Y TẾ
              </span>

              <input
                ref={fileInputRef}
                type="file"
                accept={ALLOWED_IMAGE_TYPES.join(',')}
                onChange={handleFileSelect}
                className="hidden"
                id="ocr-file-upload"
              />

              <label
                htmlFor="ocr-file-upload"
                className="border-2 border-dashed border-slate-300 bg-slate-50 hover:bg-slate-100 hover:border-slate-400 p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-colors block"
              >
                <Upload size={24} className="text-slate-500 mb-2" />
                <span className="text-xs font-mono font-bold text-slate-900 block">
                  NHẤN ĐỂ CHỌN ẢNH HOẶC KÉO THẢ TỆP VÀO ĐÂY
                </span>
                <span className="text-[11px] font-mono text-slate-500 mt-1 block">
                  Hỗ trợ JPG, PNG, WEBP (Tối đa 15MB)
                </span>
              </label>

              {/* Inference Processing State */}
              {isProcessing && (
                <div className="p-3 border border-slate-300 bg-slate-900 text-white font-mono text-xs space-y-1.5">
                  <div className="flex items-center gap-2 font-bold">
                    <Loader2 size={14} className="animate-spin text-teal-400" />
                    <span>PURE-ONNX CPU ENGINE ĐANG XỬ LÝ...</span>
                  </div>
                  <div className="text-[11px] text-slate-400">
                    {processingStep === 1 && 'Bước 1/3: Chuẩn hóa nhị phân ảnh & phát hiện đường dòng'}
                    {processingStep === 2 && 'Bước 2/3: Chạy suy luận ký tự cục bộ qua ONNX Runtime'}
                    {processingStep === 3 && 'Bước 3/3: Fuzzy Matching từ điển 100+ hoạt chất Bộ Y Tế'}
                  </div>
                </div>
              )}
            </div>

            {/* Verification Queue (HITL Step) */}
            {currentVerificationItem && (
              <div className="bg-white border-2 border-slate-900 p-4 space-y-3 shadow-md">
                <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                  <span className="text-xs font-mono font-bold text-slate-900 uppercase flex items-center gap-1.5">
                    <AlertCircle size={14} className="text-amber-600" />
                    XÁC NHẬN KẾT QUẢ AI (HITL GATE)
                  </span>
                  <span className="text-[11px] font-mono text-slate-500">
                    Còn lại: {verificationQueue.length} thuốc
                  </span>
                </div>

                <DrugVerificationForm
                  initialData={currentVerificationItem}
                  onSave={handleVerificationSave}
                  onCancel={handleVerificationCancel}
                  sourceType={sourceType}
                />
              </div>
            )}

            {/* Extracted Drugs Stream List */}
            <div className="bg-white border border-slate-200 p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <span className="text-xs font-mono font-bold text-slate-900 uppercase">
                  DANH SÁCH THUỐC ĐÃ NHẬN DIỆN ({extractedDrugs.length})
                </span>
                {extractedDrugs.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setExtractedDrugs([])}
                    className="text-[11px] font-mono text-slate-500 hover:text-rose-600"
                  >
                    XÓA TẤT CẢ
                  </button>
                )}
              </div>

              {extractedDrugs.length === 0 ? (
                <div className="p-6 text-center text-slate-400 font-mono text-xs border border-dashed border-slate-200">
                  Chưa có thuốc nào được trích xuất từ ảnh
                </div>
              ) : (
                <div className="space-y-2">
                  {extractedDrugs.map((drug, idx) => (
                    <div key={idx} className="p-2.5 border border-slate-200 bg-slate-50 font-mono text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900">{drug.brandName}</span>
                        <span className="text-[10px] px-1.5 py-0.2 border border-slate-300 bg-white text-slate-700">
                          {drug.strength || 'N/A'}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-600">
                        Hoạt chất: <strong className="text-slate-800">{drug.activeIngredient || drug.brandName}</strong>
                      </div>
                      {drug.dosageInstruction && (
                        <div className="text-[10px] text-slate-500 italic">
                          Liều: {drug.dosageInstruction}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>

          {/* ════════ COLUMN 2: CLINICAL EVALUATION & ALERTS (7 COLS) ════════ */}
          <div className="lg:col-span-7 space-y-4">
            
            {/* Top Action Bar for Evaluation */}
            <div className="bg-white border border-slate-200 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div>
                <span className="text-xs font-mono font-bold text-slate-700 uppercase block">
                  ĐỐI CHIẾU LÂM SÀNG TỰ ĐỘNG (4 LAYERS)
                </span>
                <p className="text-[11px] text-slate-500 font-mono">
                  Phân tích Trùng lặp, Tương tác thuốc, Bệnh nền & Phù hợp liều dùng
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={isEvaluating || (extractedDrugs.length === 0 && cabinetDrugs.length === 0)}
                  onClick={handleRunClinicalEvaluation}
                  className="h-9 px-4 bg-slate-900 hover:bg-slate-800 text-white text-xs font-mono font-bold flex items-center gap-2 disabled:opacity-40 transition-colors"
                >
                  {isEvaluating ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      <span>ĐANG PHÂN TÍCH...</span>
                    </>
                  ) : (
                    <>
                      <Activity size={14} />
                      <span>CHẠY ĐÁNH GIÁ TƯƠNG TÁC</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Evaluation Results Container */}
            {evaluationResult ? (
              <div className="border border-slate-300 bg-white p-6 space-y-4">
                <div className="border-b border-slate-200 pb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-mono font-bold text-slate-900 uppercase">
                    <CheckCircle2 size={16} className="text-slate-900" />
                    <span>BÁO CÁO TƯƠNG TÁC LÂM SÀNG HOÀN TẤT</span>
                  </div>

                  <button
                    type="button"
                    onClick={handleSaveAllToCabinet}
                    className="h-8 px-3 bg-slate-900 hover:bg-slate-800 text-white text-xs font-mono font-bold flex items-center gap-1.5"
                  >
                    <Check size={13} />
                    <span>[LƯU VÀO TỦ THUỐC]</span>
                  </button>
                </div>

                <InteractionAlertCards report={evaluationResult} />
              </div>
            ) : (
              <div className="bg-white border border-slate-200 p-8 text-center space-y-3 font-mono">
                <Layers size={32} className="mx-auto text-slate-400" />
                <h3 className="text-xs font-bold text-slate-800 uppercase">
                  KHÔNG GIAN KẾT QUẢ ĐỐI CHIẾU LÂM SÀNG
                </h3>
                <p className="text-[11px] text-slate-500 max-w-md mx-auto leading-relaxed">
                  Sau khi bạn tải ảnh và xác thực danh mục thuốc ở Cột 1, nhấn nút <strong>&quot;CHẠY ĐÁNH GIÁ TƯƠNG TÁC&quot;</strong> để hệ thống tiến hành kiểm tra xung đột hoạt chất 4 lớp.
                </p>
              </div>
            )}

          </div>

        </div>
      </main>

      {/* ── Smart Crop Modal ── */}
      {isCropModalOpen && rawImageUrl && (
        <SmartCropModal
          isOpen={isCropModalOpen}
          imageUrl={rawImageUrl}
          onCropComplete={handleCropComplete}
          onClose={() => {
            setIsCropModalOpen(false);
            setRawImageUrl(null);
          }}
        />
      )}

    </div>
  );
}
