'use client';

/**
 * InteractionAlertCards — Thẻ Cảnh Báo Tương Tác Lâm Sàng (Minimalist Clinical Grade).
 * Border 1px, đơn sắc chức năng (#0F172A, #334155, #FFFFFF, #E2E8F0, rounded-none / rounded-sm).
 * Khớp 100% Data Contract: IInteractionAlert & IEvaluationResponse (types/medication.ts).
 */

import React, { useState } from 'react';
import { IInteractionAlert, IEvaluationResponse } from '@/types/medication';
import { AlertTriangle, AlertOctagon, CheckCircle2, ChevronDown, ChevronUp, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AlertCardProps {
  alert: IInteractionAlert;
}

function AlertCard({ alert }: AlertCardProps) {
  const [expanded, setExpanded] = useState(true);

  const config = {
    HIGH: {
      border: 'border-rose-300',
      bg: 'bg-rose-50/50',
      headerBg: 'bg-rose-100/60',
      icon: <AlertOctagon className="text-rose-700 shrink-0" size={18} />,
      badge: 'bg-rose-700 text-white',
      badgeText: 'CẢNH BÁO NẶNG (HIGH)',
      titleColor: 'text-rose-900',
      textColor: 'text-rose-800',
    },
    MEDIUM: {
      border: 'border-amber-300',
      bg: 'bg-amber-50/50',
      headerBg: 'bg-amber-100/60',
      icon: <AlertTriangle className="text-amber-700 shrink-0" size={18} />,
      badge: 'bg-amber-600 text-white',
      badgeText: 'CẦN CHÚ Ý (MEDIUM)',
      titleColor: 'text-amber-900',
      textColor: 'text-amber-800',
    },
    LOW: {
      border: 'border-slate-300',
      bg: 'bg-slate-50',
      headerBg: 'bg-slate-100',
      icon: <AlertTriangle className="text-slate-600 shrink-0" size={18} />,
      badge: 'bg-slate-700 text-white',
      badgeText: 'THÔNG TIN (LOW)',
      titleColor: 'text-slate-900',
      textColor: 'text-slate-800',
    },
  };

  const c = config[alert.severity] ?? config.LOW;

  return (
    <div className={cn('border overflow-hidden font-mono text-xs', c.border, c.bg)}>
      {/* Header */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className={cn('w-full flex items-center gap-2.5 p-3 text-left transition-colors', c.headerBg)}
      >
        {c.icon}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={cn('text-[10px] font-bold px-1.5 py-0.2', c.badge)}>{c.badgeText}</span>
          </div>
          <p className={cn('font-bold text-xs mt-1 truncate', c.titleColor)}>
            {alert.title}
          </p>
        </div>
        <div className="text-slate-500">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>

      {/* Expanded Body */}
      {expanded && (
        <div className="p-3.5 space-y-2.5 border-t border-slate-200">
          <div>
            <span className="text-[10px] font-bold text-slate-500 uppercase block mb-0.5">
              Cơ chế tương tác & Mô tả:
            </span>
            <p className="text-slate-800 leading-relaxed text-xs">
              {alert.description}
            </p>
          </div>

          {alert.recommendation && (
            <div className="p-2.5 bg-white border border-slate-200 space-y-1">
              <span className="text-[10px] font-bold text-slate-700 uppercase block">
                Khuyến cáo lâm sàng & Xử trí:
              </span>
              <p className="text-slate-900 text-xs leading-relaxed font-semibold">
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
  const highestSeverity = hasHigh ? 'HIGH' : hasMedium ? 'MEDIUM' : alerts.length > 0 ? 'LOW' : 'NONE';
  const isSafe = !hasHigh;

  return (
    <div className="space-y-4 font-mono text-xs">
      
      {/* Final Summary Banner */}
      {report.finalSummary && (
        <div className="p-3.5 border border-slate-300 bg-slate-900 text-white space-y-1">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            TỔNG KẾT ĐÁNH GIÁ AN TOÀN TOÀN BỘ ĐƠN THUỐC
          </span>
          <p className="text-xs leading-relaxed text-slate-100">
            {report.finalSummary}
          </p>
        </div>
      )}

      {/* Overview Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
        <div className="p-2.5 border border-slate-200 bg-slate-50">
          <span className="text-[10px] text-slate-500 uppercase block">Tổng thuốc:</span>
          <strong className="text-sm font-bold text-slate-900">{report.totalDrugsAnalyzed}</strong>
        </div>
        <div className="p-2.5 border border-slate-200 bg-slate-50">
          <span className="text-[10px] text-slate-500 uppercase block">Tổng cảnh báo:</span>
          <strong className="text-sm font-bold text-slate-900">{alerts.length}</strong>
        </div>
        <div className="p-2.5 border border-slate-200 bg-slate-50">
          <span className="text-[10px] text-slate-500 uppercase block">Mức cao nhất:</span>
          <strong className="text-xs font-bold text-slate-900">{highestSeverity}</strong>
        </div>
        <div className="p-2.5 border border-slate-200 bg-slate-50">
          <span className="text-[10px] text-slate-500 uppercase block">An toàn đơn thuốc:</span>
          <strong className={`text-xs font-bold ${isSafe ? 'text-emerald-700' : 'text-rose-700'}`}>
            {isSafe ? 'ĐẠT AN TOÀN' : 'CÓ NGUY CƠ'}
          </strong>
        </div>
      </div>

      {/* Layer 4 Dosage Checks if present */}
      {report.dosageChecks && report.dosageChecks.length > 0 && (
        <div className="border border-slate-200 bg-white p-3 space-y-2">
          <span className="text-[10px] font-bold text-slate-700 uppercase block border-b border-slate-100 pb-1">
            ĐỐI CHIẾU LIỀU DÙNG THỰC TẾ (LAYER 4):
          </span>
          <div className="space-y-1.5">
            {report.dosageChecks.map((dc, i) => (
              <div key={i} className="p-2 border border-slate-200 bg-slate-50 flex items-start justify-between gap-2 text-[11px]">
                <div>
                  <span className="font-bold text-slate-900">{dc.drugName}</span>
                  <div className="text-slate-600">
                    Kê/Nhập: <strong>{dc.prescribedOrInputDosage}</strong> • Chuẩn: {dc.recommendedDosage}
                  </div>
                  {dc.note && <div className="text-[10px] text-slate-500 italic mt-0.5">{dc.note}</div>}
                </div>
                <span className={`px-1.5 py-0.2 border font-bold text-[10px] shrink-0 ${
                  dc.isAppropriate === true
                    ? 'text-emerald-800 bg-emerald-50 border-emerald-300'
                    : dc.isAppropriate === false
                    ? 'text-amber-800 bg-amber-50 border-amber-300'
                    : 'text-slate-700 bg-slate-100 border-slate-300'
                }`}>
                  {dc.isAppropriate === true ? 'PHÙ HỢP' : dc.isAppropriate === false ? 'CHÊNH LỆCH' : 'CHƯA ĐỦ DL'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Alerts Stream */}
      {alerts.length === 0 ? (
        <div className="p-6 border border-emerald-300 bg-emerald-50 text-center space-y-1">
          <CheckCircle2 size={24} className="mx-auto text-emerald-700" />
          <p className="font-bold text-emerald-900 text-xs uppercase">
            KHÔNG PHÁT HIỆN TƯƠNG TÁC BẤT LỢI
          </p>
          <p className="text-[11px] text-emerald-800">
            Các hoạt chất trong đơn không có xung đột nghiêm trọng hoặc chống chỉ định theo hồ sơ bệnh nhân.
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
