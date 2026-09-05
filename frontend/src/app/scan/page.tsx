'use client';

/**
 * High-Precision Pure OCR Scanning & 2-Column Clinical Verification — Route /scan.
 * Rebranding: MediScan.
 * Bento-Grid Layout synced with Material 3 Clinical Design System.
 */

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  FileText, Box, Loader2, ShieldCheck, CheckCircle2,
  AlertCircle, ArrowLeft, UploadCloud, Pill,
  Activity, Check, Layers, Sparkles, Camera, Zap
} from 'lucide-react';
import { SmartCropModal } from '@/components/scan/SmartCropModal';
import { DrugVerificationForm } from '@/components/scan/DrugVerificationForm';
import { AddToCabinetModal } from '@/components/scan/AddToCabinetModal';
import { AICacheMetricsModal } from '@/components/telemetry/AICacheMetricsModal';
import { InteractionAlertCards } from '@/components/report/InteractionAlertCards';
import { openMedicalDisclaimerModal, isDisclaimerAccepted } from '@/components/common/MedicalDisclaimerModal';
import { toast } from '@/components/common/Toast';
import { useCabinetStore } from '@/store/cabinetStore';
import { useHistoryReminderStore } from '@/store/historyReminderStore';
import { IDrugItem, IEvaluationResponse, IExtractedDrugItem } from '@/types/medication';
import { scanImage, mapFullScanToDrugs } from '@/services/ocrService';
import { useEvaluation } from '@/services/evaluationService';
import { useUserProfileStore } from '@/store/userProfileStore';
import { isAxiosError } from 'axios';

const MAX_FILE_SIZE_MB = 15;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg', 'image/heic'];

export default function ScanPage() {
  const router = useRouter();
  const { addDrugs, drugs: cabinetDrugs } = useCabinetStore();
  const { createReminder } = useHistoryReminderStore();
  const { profile } = useUserProfileStore();
  const { mutate: runEvaluate, isPending: isEvaluating } = useEvaluation();

  const [sourceType, setSourceType] = useState<'prescription' | 'packaging'>('prescription');
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState<1 | 2 | 3>(1);
  const [rawImageUrl, setRawImageUrl] = useState<string | null>(null);
  const [isCropModalOpen, setIsCropModalOpen] = useState(false);
  const [isAddToCabinetModalOpen, setIsAddToCabinetModalOpen] = useState(false);
  const [isTelemetryOpen, setIsTelemetryOpen] = useState(false);

  // Danh sách thuốc trích xuất từ phiên scan hiện tại
  const [extractedDrugs, setExtractedDrugs] = useState<IDrugItem[]>([]);
  const [verificationQueue, setVerificationQueue] = useState<IDrugItem[]>([]);
  const [evaluationResult, setEvaluationResult] = useState<IEvaluationResponse | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const backFileInputRef = useRef<HTMLInputElement>(null);

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

  /**
   * [Task 13.4] Multi-Shot In-Memory Back-Panel Scan (Zero Image Persistence)
   * Quét bảng hàm lượng/thành phần mặt sau vỏ hộp và hợp nhất vào item hiện tại.
   */
  const handleBackPanelSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !validateFile(file)) {
      if (backFileInputRef.current) backFileInputRef.current.value = '';
      return;
    }

    setIsProcessing(true);
    try {
      toast.info('Đang phân tích bảng thành phần mặt sau bao bì...');
      const ocrResult = await scanImage(file, 'packaging');
      const items: IDrugItem[] = mapFullScanToDrugs(ocrResult);

      let foundStrength = '';
      let foundIngredient = '';
      for (const it of items) {
        if (it.strength && !foundStrength) foundStrength = it.strength;
        if (it.activeIngredient && !foundIngredient) foundIngredient = it.activeIngredient;
      }

      // Regex fallback trên toàn bộ OCR raw text lines
      if (!foundStrength && ocrResult.rawOcrItems) {
        for (const raw of ocrResult.rawOcrItems) {
          const match = raw.text.match(/(\d+(?:\.\d+)?\s*(?:mg|g|ml|%|mcg|iu))/i);
          if (match) {
            foundStrength = match[1].replace(/\s+/g, '').toLowerCase();
            break;
          }
        }
      }

      if (foundStrength || foundIngredient) {
        setVerificationQueue((prev) => {
          if (prev.length === 0) return prev;
          const updated = [...prev];
          const current = { ...updated[0] };
          if (foundStrength && !current.strength) current.strength = foundStrength;
          if (foundIngredient && !current.activeIngredient) current.activeIngredient = foundIngredient;
          updated[0] = current;
          return updated;
        });
        toast.success(
          `Đã bổ sung từ mặt sau: ${foundStrength ? `Hàm lượng ${foundStrength}` : ''} ${foundIngredient ? `Hoạt chất ${foundIngredient}` : ''}`.trim()
        );
      } else {
        toast.warning('Chưa tìm thấy thông tin hàm lượng từ ảnh mặt sau. Vui lòng chọn gợi ý hoặc nhập tay.');
      }
    } catch {
      toast.error('Không thể xử lý ảnh mặt sau bao bì. Vui lòng thử lại.');
    } finally {
      setIsProcessing(false);
      if (backFileInputRef.current) backFileInputRef.current.value = '';
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!validateFile(file)) {
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    if (rawImageUrl && rawImageUrl.startsWith('blob:')) {
      URL.revokeObjectURL(rawImageUrl);
    }

    const url = URL.createObjectURL(file);
    setRawImageUrl(url);

    // Dọn sạch hàng đợi xác nhận và kết quả đánh giá cũ khi nạp ảnh mới
    setVerificationQueue([]);
    setEvaluationResult(null);

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
      setVerificationQueue([]);
    }
  };

  const processImage = async (file: File, type: 'prescription' | 'packaging') => {
    setIsProcessing(true);
    setProcessingStep(1);
    // Reset hàng đợi và kết quả cũ trước khi bắt đầu trích xuất ảnh mới
    setVerificationQueue([]);
    setEvaluationResult(null);

    try {
      const stepTimer1 = setTimeout(() => setProcessingStep(2), 600);
      const stepTimer2 = setTimeout(() => setProcessingStep(3), 1200);

      const ocrResult = await scanImage(file, type);

      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);

      const items: IDrugItem[] = mapFullScanToDrugs(ocrResult);

      if (items.length === 0) {
        toast.warning('Không nhận diện được tên thuốc nào từ ảnh. Hãy chụp rõ nét hơn hoặc nhập thủ công.');
        setIsProcessing(false);
        return;
      }

      if (type === 'prescription') {
        // [Toa thuốc - Multi-item Prescription Review]:
        // Tự động nạp toàn bộ danh sách thuốc trích xuất được (1, 2, 3, 4, 5, 6...) vào extractedDrugs
        // để người dùng nhìn thấy đầy đủ các vị trí trong đơn thuốc ngay lập tức mà không bị kẹt ở hàng đợi 1 thuốc.
        setExtractedDrugs(items);
        setVerificationQueue([]);
        toast.success(`Đã trích xuất thành công toàn bộ ${items.length} thuốc từ toa thuốc! Vui lòng đối soát lại.`);
      } else {
        toast.success(`Đã trích xuất ${items.length} mục từ ảnh! Vui lòng kiểm tra và xác nhận.`);
        setVerificationQueue(items);
      }
    } catch (err: unknown) {
      console.error('Lỗi nhận diện ảnh:', err);
      let errorMsg = 'Không thể kết nối đến hệ thống nhận diện. Hãy kiểm tra Backend.';
      if (isAxiosError(err) && err.response?.data?.detail) {
        errorMsg = err.response.data.detail;
      } else if (err instanceof Error) {
        errorMsg = err.message;
      }
      toast.error(errorMsg);
    } finally {
      setIsProcessing(false);
    }
  };

  // HITL Callback: Lưu thuốc sau khi người dùng xác nhận
  const handleVerificationSave = (verifiedDrug: IDrugItem) => {
    setExtractedDrugs((prev) => [...prev, verifiedDrug]);
    setVerificationQueue((prev) => prev.slice(1));
    toast.success(`Đã xác nhận: ${verifiedDrug.brandName}`);
  };

  const handleVerificationCancel = () => {
    setVerificationQueue((prev) => prev.slice(1));
  };

  // Xác nhận nhanh toàn bộ hàng đợi HITL
  const handleVerifyAll = () => {
    setExtractedDrugs((prev) => [...prev, ...verificationQueue]);
    setVerificationQueue([]);
    toast.success(`Đã xác nhận toàn bộ ${verificationQueue.length} thuốc!`);
  };

  // Chạy đánh giá tương tác 4 lớp
  const handleRunClinicalEvaluation = () => {
    if (!isDisclaimerAccepted()) {
      openMedicalDisclaimerModal();
      toast.warning('Vui lòng chấp thuận Tuyên bố Miễn trừ Trách nhiệm Y tế.');
      return;
    }

    const allDrugsToEvaluate = [
      ...cabinetDrugs.filter((d) => d.isActive).map((d) => ({
        brandName: d.brandName,
        activeIngredient: d.activeIngredient || d.brandName,
        strength: d.strength || '',
        dosageInstruction: d.dosageInstruction || '',
        confidenceScore: d.confidenceScore,
        isVerified: d.isVerified,
      })),
      ...extractedDrugs.map((d) => ({
        brandName: d.brandName,
        activeIngredient: d.activeIngredient || d.brandName,
        strength: d.strength || '',
        dosageInstruction: d.dosageInstruction || '',
        confidenceScore: d.confidenceScore || 1.0,
        isVerified: true,
      })),
    ];

    if (allDrugsToEvaluate.length === 0) {
      toast.warning('Chưa có thuốc nào để đánh giá! Hãy quét hoặc thêm thuốc vào tủ.');
      return;
    }

    runEvaluate(
      {
        drugs: allDrugsToEvaluate,
        userProfile: {
          age: profile?.age || 35,
          gender: profile?.gender || 'male',
          conditions: profile?.conditions || [],
          allergies: profile?.allergies || [],
          isPregnant: profile?.isPregnant || false,
          isBreastfeeding: profile?.isBreastfeeding || false,
          weightKg: profile?.weightKg,
          heightCm: profile?.heightCm,
        },
      },
      {
        onSuccess: (res) => {
          setEvaluationResult(res);
          toast.success(`Đã phân tích tương tác thành công (${res.totalDrugsAnalyzed} thuốc)!`);
        },
        onError: (err) => {
          toast.error(`Lỗi phân tích: ${err.message}`);
        },
      }
    );
  };

  // Trigger mở AddToCabinetModal
  const handleOpenCabinetModal = () => {
    if (extractedDrugs.length === 0) {
      toast.warning('Chưa có danh sách thuốc nào được trích xuất.');
      return;
    }
    setIsAddToCabinetModalOpen(true);
  };

  // Handler 1: Lưu Lịch sử phân tích
  const handleOnlySaveHistory = () => {
    toast.success('Phiên quét đã được tự động lưu vào Lịch sử phân tích!');
    setIsAddToCabinetModalOpen(false);
  };

  // Handler 2: Thêm vào Tủ thuốc & tạo Nhắc nhở
  const handleConfirmAddToCabinetAndReminders = async (items: IExtractedDrugItem[]) => {
    try {
      // 1. Sync vào cabinetStore
      const cabinetItems = items.map((item) => ({
        brandName: item.drugName,
        activeIngredient: item.activeIngredient || item.drugName,
        strength: item.strength || '',
        dosageInstruction: item.dosageInstruction || `Dùng ${item.durationDays || 7} ngày`,
        confidenceScore: 1.0,
        isVerified: true,
        inputSource: sourceType,
      }));
      addDrugs(cabinetItems);

      // 2. Tạo Reminders trong historyReminderStore
      for (const item of items) {
        for (const slotKey of item.timeSlots) {
          const timeVal = item.slotTimes[slotKey] || '08:00';
          try {
            await createReminder({
              drugName: item.drugName,
              dosageInstruction: item.dosageInstruction || `Uống ${item.strength || ''}`,
              timeOfDay: slotKey as 'morning' | 'noon' | 'afternoon' | 'evening',
              reminderTime: timeVal,
              isActive: true,
            });
          } catch (e) {
            console.warn('Lỗi tạo nhắc nhở:', e);
          }
        }
      }


      toast.success(`Đã lưu ${items.length} thuốc vào Tủ thuốc và bật lịch nhắc nhở thành công!`);
      setIsAddToCabinetModalOpen(false);
      router.push('/cabinet');
    } catch (err) {
      console.error('Lỗi lưu tủ thuốc & lịch uống:', err);
      toast.error('Đã xảy ra lỗi khi tạo lịch uống. Hãy kiểm tra lại.');
    }
  };

  const currentVerificationItem = verificationQueue[0];

  return (
    <div className="min-h-screen bg-background font-[var(--font-inter)] text-on-background pb-16">
      
      {/* ── Top Bar ── */}
      <div className="bg-surface border-b border-outline-variant/30 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link
              href="/cabinet"
              className="h-9 px-3 border border-outline-variant bg-white hover:bg-surface-container text-on-surface-variant text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all shadow-sm"
            >
              <ArrowLeft size={14} className="hover:text-primary transition-colors" />
              <span>Trở về</span>
            </Link>
            <div>
              <h1 className="text-xl font-bold text-primary">
                Quét & Đánh giá đơn thuốc
              </h1>
              <p className="text-xs text-on-surface-variant mt-0.5">
                Trích xuất hoạt chất và phân tích tương tác tự động
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsTelemetryOpen(true)}
              className="h-9 px-3 border border-indigo-200 bg-indigo-50/70 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all shadow-sm"
              title="Xem thống kê tối ưu chi phí & Telemetry AI"
            >
              <Zap size={14} className="text-indigo-600 fill-indigo-500" />
              <span>AI Telemetry</span>
            </button>

            <button
              type="button"
              onClick={() => openMedicalDisclaimerModal()}
              className="h-9 px-3 border border-outline-variant bg-white hover:bg-surface-container text-on-surface-variant text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all shadow-sm"
            >
              <ShieldCheck size={14} className="text-primary" />
              <span>Miễn trừ y tế</span>
            </button>

            {extractedDrugs.length > 0 && (
              <button
                type="button"
                onClick={handleOpenCabinetModal}
                className="h-9 px-4 bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-layer-1 transition-all"
              >
                <Check size={14} />
                <span>Lưu vào tủ thuốc</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── Main 2-Column Bento Grid Workspace ── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 pt-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* ════════ COLUMN 1: EXTRACTION & INPUT STREAM (5/12 COLS) ════════ */}
          <div className="lg:col-span-5 space-y-6">
            
            {/* Thẻ 1: Chọn nguồn ảnh tài liệu */}
            <div className="bg-surface rounded-xl border border-outline-variant/30 p-5 space-y-3 shadow-layer-1">
              <span className="text-xs font-bold text-on-surface block">
                Chọn nguồn ảnh tài liệu
              </span>

              <div className="grid grid-cols-2 gap-2.5">
                <button
                  type="button"
                  onClick={() => setSourceType('prescription')}
                  className={`p-3.5 text-left rounded-lg border text-xs transition-all flex flex-col ${
                    sourceType === 'prescription'
                      ? 'border-primary bg-surface-container-low text-primary shadow-sm'
                      : 'bg-white text-on-surface-variant border-outline-variant hover:bg-surface-container-low'
                  }`}
                >
                  <FileText size={18} className={`mb-1.5 ${sourceType === 'prescription' ? 'text-primary' : 'text-on-surface-variant'}`} />
                  <span className="font-bold block">Toa thuốc</span>
                  <span className="text-[11px] opacity-80 block mt-0.5">
                    Đọc tên, hàm lượng & liều
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setSourceType('packaging')}
                  className={`p-3.5 text-left rounded-lg border text-xs transition-all flex flex-col ${
                    sourceType === 'packaging'
                      ? 'border-primary bg-surface-container-low text-primary shadow-sm'
                      : 'bg-white text-on-surface-variant border-outline-variant hover:bg-surface-container-low'
                  }`}
                >
                  <Box size={18} className={`mb-1.5 ${sourceType === 'packaging' ? 'text-primary' : 'text-on-surface-variant'}`} />
                  <span className="font-bold block">Vỏ hộp thuốc</span>
                  <span className="text-[11px] opacity-80 block mt-0.5">
                    Cắt nhãn & nhập liều tay
                  </span>
                </button>
              </div>
            </div>

            {/* Thẻ 2: Khu vực nạp ảnh */}
            <div className="bg-surface rounded-xl border border-outline-variant/30 p-5 space-y-3 shadow-layer-1">
              <span className="text-xs font-bold text-on-surface block">
                Nạp ảnh chụp
              </span>

              <input
                ref={fileInputRef}
                type="file"
                accept={ALLOWED_IMAGE_TYPES.join(',')}
                onChange={handleFileSelect}
                className="hidden"
                id="ocr-file-upload"
              />

              {rawImageUrl ? (
                <div className="relative rounded-xl overflow-hidden border border-outline-variant bg-background p-2 group">
                  {/* eslint-disable-next-html-element-suppress */}
                  <img
                    src={rawImageUrl}
                    alt="Xem trước ảnh đơn thuốc"
                    className="w-full h-44 object-contain rounded-lg bg-slate-900/5"
                  />
                  <div className="absolute top-4 right-4 flex items-center gap-2">
                    <label
                      htmlFor="ocr-file-upload"
                      className="px-2.5 py-1 bg-white/90 hover:bg-white text-slate-800 rounded-lg text-[11px] font-bold shadow cursor-pointer transition-all"
                    >
                      Đổi ảnh khác
                    </label>
                  </div>
                </div>
              ) : (
                <label
                  htmlFor="ocr-file-upload"
                  className="border-2 border-dashed border-outline-variant hover:border-primary bg-background rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all block"
                >
                  <UploadCloud size={30} className="text-primary mb-2" />
                  <span className="text-xs font-bold text-on-surface block">
                    Nhấn để chọn ảnh hoặc kéo thả tệp vào đây
                  </span>
                  <span className="text-[11px] text-on-surface-variant mt-1 block">
                    Hỗ trợ JPG, PNG, WEBP tối đa 15MB
                  </span>
                </label>
              )}

              {/* Inference Processing State */}
              {isProcessing && (
                <div className="p-4 rounded-lg bg-primary text-on-primary text-xs space-y-1.5 shadow-sm">
                  <div className="flex items-center gap-2 font-bold">
                    <Loader2 size={15} className="animate-spin text-on-primary" />
                    <span>ONNX Engine đang xử lý...</span>
                  </div>
                  <div className="text-[11px] text-on-primary/80">
                    {processingStep === 1 && 'Bước 1/3: Chuẩn hóa nhị phân ảnh & nhận diện dòng'}
                    {processingStep === 2 && 'Bước 2/3: Chạy suy luận ký tự cục bộ qua ONNX'}
                    {processingStep === 3 && 'Bước 3/3: Đối chiếu từ điển hoạt chất Bộ Y Tế'}
                  </div>
                </div>
              )}
            </div>

            {/* Verification Queue (HITL Step) */}
            {currentVerificationItem && (
              <div className="bg-surface rounded-xl border-2 border-primary p-5 space-y-3 shadow-layer-1">
                <div className="flex items-center justify-between border-b border-outline-variant/30 pb-2">
                  <span className="text-xs font-bold text-primary flex items-center gap-1.5">
                    <AlertCircle size={15} className="text-primary" />
                    Xác nhận kết quả nhận diện (HITL)
                  </span>
                  <div className="flex items-center gap-2">
                    {verificationQueue.length > 1 && (
                      <button
                        type="button"
                        onClick={handleVerifyAll}
                        className="px-2.5 py-1 text-[11px] font-bold text-white bg-primary hover:bg-primary/90 rounded-md transition-colors shadow-sm"
                      >
                        Xác nhận tất cả ({verificationQueue.length})
                      </button>
                    )}
                    {sourceType === 'packaging' && (
                      <>
                        <input
                          ref={backFileInputRef}
                          type="file"
                          accept={ALLOWED_IMAGE_TYPES.join(',')}
                          onChange={handleBackPanelSelect}
                          className="hidden"
                          id="ocr-back-file-upload"
                        />
                        <button
                          type="button"
                          onClick={() => backFileInputRef.current?.click()}
                          className="px-2.5 py-1 text-[11px] font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-md border border-blue-200 transition-colors flex items-center gap-1"
                          title="Chụp thêm mặt sau vỏ hộp để quét bảng hàm lượng / thành phần (100% in-memory)"
                        >
                          <Camera size={13} />
                          Quét thêm mặt sau vỏ hộp
                        </button>
                      </>
                    )}
                    <span className="text-xs text-on-surface-variant font-bold">
                      Còn lại: {verificationQueue.length} thuốc
                    </span>
                  </div>
                </div>

                <DrugVerificationForm
                  key={`${currentVerificationItem.brandName}-${currentVerificationItem.strength || ''}-${currentVerificationItem.activeIngredient || ''}-${verificationQueue.length}`}
                  initialData={currentVerificationItem}
                  onSave={handleVerificationSave}
                  onCancel={handleVerificationCancel}
                  sourceType={sourceType}
                />
              </div>
            )}

            {/* Thẻ 3: Danh sách thuốc đã nhận diện */}
            <div className="bg-surface rounded-xl border border-outline-variant/30 p-5 space-y-3 shadow-layer-1">
              <div className="flex items-center justify-between border-b border-outline-variant/30 pb-2">
                <span className="text-xs font-bold text-on-surface flex items-center gap-1.5">
                  <FileText size={15} className="text-primary" />
                  Danh mục thuốc đã trích xuất ({extractedDrugs.length})
                </span>
                {extractedDrugs.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setExtractedDrugs([])}
                    className="text-[11px] text-on-surface-variant hover:text-error transition-colors font-bold"
                  >
                    Xóa tất cả
                  </button>
                )}
              </div>

              {extractedDrugs.length === 0 ? (
                <div className="p-6 text-center text-on-surface-variant text-xs italic rounded-lg border border-dashed border-outline-variant bg-background">
                  Chưa có thuốc nào được trích xuất từ ảnh. Hãy nạp ảnh đơn thuốc hoặc vỏ hộp.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {extractedDrugs.map((drug, idx) => (
                    <div key={idx} className="p-3 rounded-lg border border-outline-variant/40 bg-background text-xs space-y-2 relative group shadow-sm hover:border-primary/50 transition-colors">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-extrabold text-primary bg-primary/10 px-2 py-0.5 rounded text-[11px] shrink-0">
                          #{idx + 1}
                        </span>
                        <input
                          type="text"
                          value={drug.brandName}
                          onChange={(e) => {
                            const updated = [...extractedDrugs];
                            updated[idx].brandName = e.target.value;
                            setExtractedDrugs(updated);
                          }}
                          className="font-bold text-primary bg-white border border-outline-variant/40 rounded px-2 py-0.5 text-xs outline-none focus:border-primary flex-1"
                        />
                        <input
                          type="text"
                          value={drug.strength || ''}
                          placeholder="Hàm lượng"
                          onChange={(e) => {
                            const updated = [...extractedDrugs];
                            updated[idx].strength = e.target.value;
                            setExtractedDrugs(updated);
                          }}
                          className="text-[11px] font-bold text-slate-700 bg-white border border-outline-variant/40 rounded px-2 py-0.5 text-right w-24 outline-none focus:border-primary"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            setExtractedDrugs((prev) => prev.filter((_, i) => i !== idx));
                            toast.info(`Đã xóa thuốc ${drug.brandName}`);
                          }}
                          className="text-slate-400 hover:text-error transition-colors p-1"
                          title="Xóa thuốc khỏi danh sách"
                        >
                          ✕
                        </button>
                      </div>

                      <div className="space-y-1.5 text-[11px]">
                        <div>
                          <label className="block text-[10px] text-on-surface-variant font-semibold">Hoạt chất gốc (Chuẩn hóa)</label>
                          <input
                            type="text"
                            value={drug.activeIngredient || ''}
                            onChange={(e) => {
                              const updated = [...extractedDrugs];
                              updated[idx].activeIngredient = e.target.value;
                              setExtractedDrugs(updated);
                            }}
                            className="w-full bg-white border border-outline-variant/30 rounded px-2 py-1 text-[11px] outline-none font-medium text-slate-800"
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] text-on-surface-variant font-semibold">Hướng dẫn liều dùng thực tế</label>
                          <input
                            type="text"
                            value={drug.dosageInstruction || ''}
                            onChange={(e) => {
                              const updated = [...extractedDrugs];
                              updated[idx].dosageInstruction = e.target.value;
                              setExtractedDrugs(updated);
                            }}
                            className="w-full bg-white border border-outline-variant/30 rounded px-2 py-1 text-[11px] outline-none text-slate-700 font-medium"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>

          {/* ════════ COLUMN 2: CLINICAL EVALUATION & ALERTS (7/12 COLS) ════════ */}
          <div className="lg:col-span-7 space-y-6">
            
            {/* Thẻ 1: Action Header Card */}
            <div className="bg-surface rounded-xl border border-outline-variant/30 p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-layer-1">
              <div>
                <span className="text-xs font-bold text-primary block">
                  Đánh giá tương tác y khoa
                </span>
                <p className="text-xs text-on-surface-variant mt-0.5">
                  Kiểm tra trùng lặp hoạt chất, tương tác thuốc - thuốc, bệnh nền & liều dùng
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={isEvaluating || (extractedDrugs.length === 0 && cabinetDrugs.length === 0)}
                  onClick={handleRunClinicalEvaluation}
                  className="h-11 px-5 bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold rounded-lg flex items-center gap-2 disabled:opacity-40 transition-all shadow-layer-1"
                >
                  {isEvaluating ? (
                    <>
                      <Loader2 size={14} className="animate-spin text-on-primary" />
                      <span>Đang phân tích...</span>
                    </>
                  ) : (
                    <>
                      <Activity size={14} />
                      <span>Đánh giá tương tác</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Thẻ 2: Khu vực hiển thị kết quả phân tích */}
            {evaluationResult ? (
              <div className="rounded-xl border border-outline-variant/30 bg-surface p-6 space-y-4 shadow-layer-1">
                <div className="border-b border-outline-variant/30 pb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm font-bold text-primary">
                    <CheckCircle2 size={18} className="text-primary" />
                    <span>Báo cáo đánh giá tương tác</span>
                  </div>

                  <button
                    type="button"
                    onClick={handleOpenCabinetModal}
                    className="h-8 px-3.5 bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-sm transition-all"
                  >
                    <Check size={14} />
                    <span>Lưu vào tủ thuốc</span>
                  </button>
                </div>

                <InteractionAlertCards report={evaluationResult} />
              </div>
            ) : (
              <div className="bg-surface rounded-xl border border-outline-variant/30 p-10 text-center space-y-3 shadow-layer-1">
                <div className="w-16 h-16 rounded-full bg-surface-container-low flex items-center justify-center mx-auto">
                  <Layers size={28} className="text-primary/60" />
                </div>
                <h3 className="text-sm font-bold text-primary">
                  Không gian hiển thị kết quả phân tích
                </h3>
                <p className="text-xs text-on-surface-variant max-w-md mx-auto leading-relaxed">
                  Sau khi nạp ảnh và xác nhận danh mục thuốc ở cột bên trái, bấm <strong>&quot;Đánh giá tương tác&quot;</strong> để hệ thống tiến hành kiểm tra xung đột hoạt chất 4 tầng an toàn.
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

      {/* ── Add To Cabinet & Reminder Scheduler Modal ── */}
      {isAddToCabinetModalOpen && (
        <AddToCabinetModal
          isOpen={isAddToCabinetModalOpen}
          rawDrugs={extractedDrugs}
          sourceStream={sourceType}
          onClose={() => setIsAddToCabinetModalOpen(false)}
          onOnlySaveHistory={handleOnlySaveHistory}
          onConfirmAddToCabinetAndReminders={handleConfirmAddToCabinetAndReminders}
        />
      )}

      {/* ── AI Telemetry & Observability Modal (Stage 18) ── */}
      <AICacheMetricsModal
        isOpen={isTelemetryOpen}
        onClose={() => setIsTelemetryOpen(false)}
      />

    </div>
  );
}
