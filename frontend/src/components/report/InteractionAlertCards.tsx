'use client';

/**
 * InteractionAlertCards — Thẻ Cảnh Báo Tương Tác (Sky Blue & Borderless Minimalism).
 * Rebranding: MediScan.
 */

import React, { useState } from 'react';
import { IInteractionAlert, IEvaluationResponse, IDrugCoverageItem } from '@/types/medication';
import { AlertTriangle, AlertOctagon, CheckCircle2, ChevronDown, ChevronUp, Activity, Info, AlertCircle, ShieldAlert, Database, HelpCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AlertCardProps {
  alert: IInteractionAlert;
}

function AlertCard({ alert }: AlertCardProps) {
  const [expanded, setExpanded] = useState(true);

  const config = {
    HIGH: {
      border: 'border-rose-200',
      bg: 'bg-rose-50/40',
      headerBg: 'bg-rose-50',
      icon: <AlertOctagon className="text-rose-600 shrink-0" size={18} />,
      badge: 'bg-rose-100 text-rose-800 border border-rose-200',
      badgeText: 'Cảnh báo nặng',
      titleColor: 'text-rose-900',
    },
    MEDIUM: {
      border: 'border-amber-200',
      bg: 'bg-amber-50/40',
      headerBg: 'bg-amber-50',
      icon: <AlertTriangle className="text-amber-600 shrink-0" size={18} />,
      badge: 'bg-amber-100 text-amber-800 border border-amber-200',
      badgeText: 'Cần chú ý',
      titleColor: 'text-amber-900',
    },
    LOW: {
      border: 'border-sky-200',
      bg: 'bg-sky-50/30',
      headerBg: 'bg-sky-50/60',
      icon: <Info className="text-sky-600 shrink-0" size={18} />,
      badge: 'bg-sky-100 text-sky-800 border border-sky-200',
      badgeText: 'Thông tin nhẹ',
      titleColor: 'text-slate-900',
    },
  };

  const c = config[alert.severity] ?? config.LOW;

  return (
    <div className={cn('border rounded-xl overflow-hidden transition-all duration-200 bg-white shadow-sm', c.border)}>
      <div
        onClick={() => setExpanded(!expanded)}
        className={cn('p-3.5 flex items-center justify-between cursor-pointer select-none border-b transition-colors', c.headerBg, c.border)}
      >
        <div className="flex items-center gap-2.5 min-w-0 pr-2">
          {c.icon}
          <div className="truncate">
            <h4 className={cn('text-xs font-bold truncate leading-tight', c.titleColor)}>
              {alert.title}
            </h4>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className={cn('px-2 py-0.5 rounded-full font-semibold text-[10px]', c.badge)}>
            {c.badgeText}
          </span>
          <button
            type="button"
            className="text-slate-400 hover:text-slate-600 p-0.5 rounded-md hover:bg-slate-100 transition-colors"
            aria-label={expanded ? "Thu gọn chi tiết" : "Mở rộng chi tiết"}
          >
            {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className={cn('p-4 space-y-3', c.bg)}>
          <div>
            <span className="text-[11px] font-bold text-slate-700 block mb-1">Cơ chế & Tác động:</span>
            <p className="text-slate-700 text-xs leading-relaxed whitespace-pre-line bg-white/70 p-2.5 rounded-lg border border-slate-100">
              {alert.description}
            </p>
          </div>

          {alert.recommendation && (
            <div>
              <span className="text-[11px] font-bold text-sky-900 block mb-1 flex items-center gap-1">
                <Activity size={13} className="text-sky-600" />
                Khuyến nghị xử trí:
              </span>
              <p className="text-sky-950 text-xs leading-relaxed bg-sky-50/80 p-2.5 rounded-lg border border-sky-100 font-medium">
                {alert.recommendation}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface InteractionAlertCardsProps {
  report: IEvaluationResponse;
  onClose?: () => void;
}

export function InteractionAlertCards({ report }: InteractionAlertCardsProps) {
  const alerts = report.alerts || [];

  const hasHigh = alerts.some((a) => a.severity === 'HIGH');
  const hasMedium = alerts.some((a) => a.severity === 'MEDIUM');
  const highestSeverity = hasHigh ? 'Cảnh báo nặng' : hasMedium ? 'Cần chú ý' : alerts.length > 0 ? 'Thông tin nhẹ' : 'Không cảnh báo';

  // [INV-12-01 / INV-12-06] Fail closed: unknown or missing coverageStatus MUST NOT default to 'FULL'!
  const rawStatus = (report.coverageStatus as string | undefined)?.toUpperCase();
  const coverageStatus = (rawStatus === 'FULL' || rawStatus === 'PARTIAL' || rawStatus === 'UNRESOLVED')
    ? rawStatus
    : 'UNAVAILABLE';

  let statusText = 'Trong ngưỡng tham khảo';
  let statusColor = 'text-emerald-600';

  if (hasHigh) {
    statusText = 'Có nguy cơ (Cao)';
    statusColor = 'text-rose-600';
  } else if (hasMedium) {
    statusText = 'Cần chú ý (Vừa)';
    statusColor = 'text-amber-600';
  } else if (alerts.length > 0) {
    statusText = 'Thông tin nhẹ';
    statusColor = 'text-sky-600';
  } else if (coverageStatus === 'UNAVAILABLE') {
    statusText = 'CSDL Không khả dụng';
    statusColor = 'text-rose-600';
  } else if (coverageStatus === 'UNRESOLVED') {
    statusText = 'Cần xác nhận';
    statusColor = 'text-rose-600';
  } else if (coverageStatus === 'PARTIAL') {
    statusText = 'Chưa đủ dữ liệu';
    statusColor = 'text-amber-600';
  }

  return (
    <div className="space-y-4 font-[var(--font-inter)] text-xs">
      
      {/* Final Summary Banner */}
      {report.finalSummary && (
        <div className="p-4 rounded-xl bg-gradient-to-br from-slate-900 to-sky-950 text-white space-y-1 shadow-sm">
          <span className="text-[11px] font-semibold text-sky-300 block">
            Tổng kết đánh giá an toàn lâm sàng
          </span>
          <p className="text-xs leading-relaxed text-slate-100">
            {report.finalSummary}
          </p>
        </div>
      )}

      {/* Overview Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-center">
        <div className="p-3 rounded-xl border border-slate-100 bg-slate-50/70">
          <span className="text-[11px] text-slate-500 block">Tổng thuốc:</span>
          <strong className="text-sm font-bold text-slate-900">{report.totalDrugsAnalyzed}</strong>
        </div>
        <div className="p-3 rounded-xl border border-slate-100 bg-slate-50/70">
          <span className="text-[11px] text-slate-500 block">Số cảnh báo:</span>
          <strong className="text-sm font-bold text-slate-900">{alerts.length}</strong>
        </div>
        <div className="p-3 rounded-xl border border-slate-100 bg-slate-50/70">
          <span className="text-[11px] text-slate-500 block">Mức cao nhất:</span>
          <strong className="text-xs font-bold text-slate-900">{highestSeverity}</strong>
        </div>
        <div className="p-3 rounded-xl border border-slate-100 bg-slate-50/70">
          <span className="text-[11px] text-slate-500 block">Trạng thái:</span>
          <strong className={cn('text-xs font-bold', statusColor)}>
            {statusText}
          </strong>
        </div>
      </div>

      {/* [Stage 12] Drug Coverage Details Matrix */}
      {report.drugCoverageDetails && report.drugCoverageDetails.length > 0 && (
        <div className="border border-slate-100 rounded-xl bg-white p-4 space-y-2.5 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 pb-1.5">
            <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
              <Database size={13} className="text-sky-600" />
              Độ bao phủ CSDL Tương tác (DDInter v2.0)
            </span>
            <span className={cn('px-2 py-0.5 rounded-full font-semibold text-[10px]',
              coverageStatus === 'FULL' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
              coverageStatus === 'PARTIAL' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
              'bg-rose-50 text-rose-700 border border-rose-200'
            )}>
              {coverageStatus === 'FULL' ? 'Bao phủ 100%' : coverageStatus === 'PARTIAL' ? 'Bao phủ một phần' : 'Chưa định danh'}
            </span>
          </div>
          <div className="space-y-1.5">
            {report.drugCoverageDetails.map((item: IDrugCoverageItem, idx: number) => (
              <div key={idx} className="p-2 rounded-lg border border-slate-100 bg-slate-50/60 flex items-center justify-between gap-2 text-xs">
                <div>
                  <span className="font-semibold text-slate-900">{item.drugName}</span>
                  {item.canonicalIngredient && (
                    <span className="text-slate-500 text-[11px] ml-1.5 font-mono">({item.canonicalIngredient})</span>
                  )}
                  {item.note && <div className="text-[10px] text-slate-500 italic mt-0.5">{item.note}</div>}
                </div>
                <span className={cn('px-2 py-0.5 rounded-full font-semibold text-[10px] shrink-0',
                  item.status === 'COVERED' ? 'text-emerald-700 bg-emerald-50 border border-emerald-200' :
                  item.status === 'NOT_COVERED' ? 'text-amber-700 bg-amber-50 border border-amber-200' :
                  'text-rose-700 bg-rose-50 border border-rose-200'
                )}>
                  {item.status === 'COVERED' ? 'Có dữ liệu DDI' : item.status === 'NOT_COVERED' ? 'Chưa có DDI' : 'Cần xác nhận'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Layer 4 Dosage Checks if present */}
      {report.dosageChecks && report.dosageChecks.length > 0 && (
        <div className="border border-slate-100 rounded-xl bg-white p-4 space-y-2.5 shadow-sm">
          <span className="text-xs font-bold text-slate-900 block border-b border-slate-100 pb-1.5">
            Đối chiếu liều dùng khuyến nghị
          </span>
          <div className="space-y-2">
            {report.dosageChecks.map((dc, i) => (
              <div key={i} className="p-2.5 rounded-lg border border-slate-100 bg-slate-50/70 flex items-start justify-between gap-2 text-xs">
                <div>
                  <span className="font-bold text-slate-900">{dc.drugName}</span>
                  <div className="text-slate-600 mt-0.5">
                    Đang dùng: <strong>{dc.prescribedOrInputDosage}</strong> • Chuẩn: {dc.recommendedDosage}
                  </div>
                  {dc.note && <div className="text-[11px] text-slate-500 italic mt-0.5">{dc.note}</div>}
                </div>
                <span className={cn('px-2.5 py-1 rounded-full font-semibold text-[11px] shrink-0 flex items-center gap-1',
                  dc.isAppropriate === true
                    ? 'text-emerald-700 bg-emerald-50 border border-emerald-200'
                    : dc.isAppropriate === false
                    ? 'text-amber-800 bg-amber-50 border border-amber-300'
                    : 'text-slate-700 bg-slate-100 border border-slate-300'
                )}>
                  {dc.isAppropriate === true ? (
                    <>
                      <CheckCircle2 size={12} className="text-emerald-600" />
                      Phù hợp
                    </>
                  ) : dc.isAppropriate === false ? (
                    <>
                      <AlertTriangle size={12} className="text-amber-600" />
                      Chênh lệch
                    </>
                  ) : (
                    <>
                      <HelpCircle size={12} className="text-slate-500" />
                      Chưa đủ DL hàm lượng
                    </>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Alerts Stream & Zero False Reassurance Handling */}
      {alerts.length === 0 ? (
        coverageStatus === 'PARTIAL' ? (
          <div className="p-5 rounded-xl border border-amber-200 bg-amber-50/60 text-center space-y-1.5">
            <AlertTriangle size={24} className="mx-auto text-amber-600" />
            <p className="font-bold text-amber-950 text-xs">
              Phạm vi CSDL chưa bao phủ toàn bộ danh sách thuốc
            </p>
            <p className="text-[11px] text-amber-800 leading-relaxed max-w-md mx-auto">
              Có thuốc chưa có dữ liệu tương tác trong CSDL DDInter v2.0. &quot;Không có cảnh báo&quot; KHÔNG đồng nghĩa với an toàn tuyệt đối — bắt buộc tham vấn bác sĩ hoặc dược sĩ.
            </p>
          </div>
        ) : coverageStatus === 'UNRESOLVED' ? (
          <div className="p-5 rounded-xl border border-rose-200 bg-rose-50/60 text-center space-y-1.5">
            <AlertCircle size={24} className="mx-auto text-rose-600" />
            <p className="font-bold text-rose-950 text-xs">
              Có thuốc chưa được xác định danh tính hoạt chất
            </p>
            <p className="text-[11px] text-rose-800 leading-relaxed max-w-md mx-auto">
              Hệ thống không thể tra cứu tương tác tự động cho các thuốc chưa được nhận diện hoặc chưa được duyệt. Vui lòng kiểm tra lại bước xác nhận thông tin.
            </p>
          </div>
        ) : coverageStatus === 'UNAVAILABLE' ? (
          <div className="p-5 rounded-xl border border-rose-300 bg-rose-50/80 text-center space-y-1.5">
            <ShieldAlert size={24} className="mx-auto text-rose-700" />
            <p className="font-bold text-rose-950 text-xs">
              CSDL Tương tác thuốc không khả dụng
            </p>
            <p className="text-[11px] text-rose-800 leading-relaxed max-w-md mx-auto">
              Tính năng tra cứu tương tác thuốc bị khóa an toàn (Fail-Closed) do lỗi toàn vẹn CSDL. Vui lòng thử lại sau hoặc tham vấn nhân viên y tế.
            </p>
          </div>
        ) : (
          <div className="p-6 rounded-xl border border-emerald-200 bg-emerald-50/60 text-center space-y-1">
            <CheckCircle2 size={24} className="mx-auto text-emerald-600" />
            <p className="font-bold text-emerald-900 text-xs">
              Không ghi nhận bản ghi tương tác trong phạm vi CSDL
            </p>
            <p className="text-[11px] text-emerald-700">
              Đã đối chiếu toàn bộ danh sách thuốc với CSDL DDInter v2.0. Kết quả mang tính tham khảo y khoa.
            </p>
          </div>
        )
      ) : (
        <div className="space-y-2.5">
          {alerts.map((alert, idx) => (
            <AlertCard key={idx} alert={alert} />
          ))}
        </div>
      )}

    </div>
  );
}
