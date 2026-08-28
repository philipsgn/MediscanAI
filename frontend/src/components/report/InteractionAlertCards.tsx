'use client';

/**
 * InteractionAlertCards — Thẻ Cảnh Báo Tương Tác (Sky Blue & Borderless Minimalism).
 * Rebranding: MediScan.
 */

import React, { useState } from 'react';
import { IInteractionAlert, IEvaluationResponse } from '@/types/medication';
import { AlertTriangle, AlertOctagon, CheckCircle2, ChevronDown, ChevronUp, Activity, Info } from 'lucide-react';
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
    <div className={cn('rounded-xl border overflow-hidden font-[var(--font-inter)] text-xs transition-all shadow-sm', c.border, c.bg)}>
      {/* Header */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className={cn('w-full flex items-center gap-3 p-3.5 text-left transition-colors', c.headerBg)}
      >
        {c.icon}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={cn('text-[11px] font-semibold px-2 py-0.5 rounded-full', c.badge)}>{c.badgeText}</span>
          </div>
          <p className={cn('font-bold text-xs mt-1 truncate', c.titleColor)}>
            {alert.title}
          </p>
        </div>
        <div className="text-slate-400">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>

      {/* Expanded Body */}
      {expanded && (
        <div className="p-4 space-y-3 border-t border-slate-100">
          <div>
            <span className="text-[11px] font-semibold text-slate-500 block mb-1">
              Cơ chế & Mô tả:
            </span>
            <p className="text-slate-800 leading-relaxed text-xs">
              {alert.description}
            </p>
          </div>

          {alert.recommendation && (
            <div className="p-3 bg-white/80 rounded-lg border border-slate-100 space-y-1">
              <span className="text-[11px] font-semibold text-slate-700 block">
                Khuyến cáo xử trí:
              </span>
              <p className="text-slate-900 text-xs leading-relaxed font-medium">
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
  const highestSeverity = hasHigh ? 'Cảnh báo nặng' : hasMedium ? 'Cần chú ý' : alerts.length > 0 ? 'Thông tin nhẹ' : 'Đạt an toàn';
  const isSafe = !hasHigh;

  return (
    <div className="space-y-4 font-[var(--font-inter)] text-xs">
      
      {/* Final Summary Banner */}
      {report.finalSummary && (
        <div className="p-4 rounded-xl bg-gradient-to-br from-slate-900 to-sky-950 text-white space-y-1 shadow-sm">
          <span className="text-[11px] font-semibold text-sky-300 block">
            Tổng kết đánh giá an toàn
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
          <strong className={`text-xs font-bold ${isSafe ? 'text-emerald-600' : 'text-rose-600'}`}>
            {isSafe ? 'Đạt an toàn' : 'Có nguy cơ'}
          </strong>
        </div>
      </div>

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
                <span className={`px-2 py-0.5 rounded-full font-semibold text-[10px] shrink-0 ${
                  dc.isAppropriate === true
                    ? 'text-emerald-700 bg-emerald-50 border border-emerald-200'
                    : dc.isAppropriate === false
                    ? 'text-amber-700 bg-amber-50 border border-amber-200'
                    : 'text-slate-600 bg-slate-100'
                }`}>
                  {dc.isAppropriate === true ? 'Phù hợp' : dc.isAppropriate === false ? 'Chênh lệch' : 'Chưa đủ DL'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Alerts Stream */}
      {alerts.length === 0 ? (
        <div className="p-6 rounded-xl border border-emerald-200 bg-emerald-50/60 text-center space-y-1">
          <CheckCircle2 size={24} className="mx-auto text-emerald-600" />
          <p className="font-bold text-emerald-900 text-xs">
            Không phát hiện tương tác bất lợi
          </p>
          <p className="text-[11px] text-emerald-700">
            Các hoạt chất trong đơn không có xung đột nghiêm trọng hoặc chống chỉ định theo hồ sơ của bạn.
          </p>
        </div>
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
