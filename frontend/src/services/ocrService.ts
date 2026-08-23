/**
 * [P0/F4.1+F4.2] OCR Scan Service — duy nhất cổng giao tiếp với POST /ocr/scan.
 * Component KHÔNG được tự gọi axios hay ghép URL.
 */
import { apiClient, API_ENDPOINTS } from './api';
import { IDrugItem, IFullScanResponse } from '@/types/medication';

export type ScanSourceType = 'prescription' | 'packaging';

/** Gửi ảnh (đã crop với packaging) tới pipeline OCR + Normalization + Clinical. */
export async function scanImage(
  file: File,
  sourceType: ScanSourceType
): Promise<IFullScanResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('source_type', sourceType);

  const response = await apiClient.post<IFullScanResponse>(
    API_ENDPOINTS.ocrScan,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      // OCR CPU SLA ~15s nhưng có thể vượt nhẹ trên máy yếu → 45s an toàn
      timeout: 45_000,
    }
  );
  return response.data;
}

/**
 * [P0/F4.2] Map DUY NHẤT từ FullScanResponse → hàng đợi HITL.
 * Nếu backend đổi shape trong tương lai: chỉ sửa HÀM NÀY (+ fixture contract
 * script), không rải thay đổi khắp component.
 */
export function mapFullScanToDrugs(data: IFullScanResponse): IDrugItem[] {
  return data.mappedDrugs ?? [];
}
