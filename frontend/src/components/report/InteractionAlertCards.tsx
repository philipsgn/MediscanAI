'use client';

import { IInteractionAlert, IEvaluationResponse } from '@/types/medication';
import { AlertTriangle, AlertOctagon, CheckCircle2, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';

interface AlertCardProps {
  alert: IInteractionAlert;
}

function AlertCard({ alert }: AlertCardProps) {
  const [expanded, setExpanded] = useState(false);

  const config = {
    HIGH: {
      border: 'border-red-200',
      bg: 'bg-red-50',
      headerBg: 'bg-red-100',
      icon: <AlertOctagon className="text-red-600 shrink-0" size={22} />,
      badge: 'bg-red-600 text-white',
      badgeText: '🔴 NGUY CẤP',
      titleColor: 'text-red-800',
      textColor: 'text-red-700',
    },
    MEDIUM: {
      border: 'border-amber-200',
      bg: 'bg-amber-50',
      headerBg: 'bg-amber-100',
      icon: <AlertTriangle className="text-amber-600 shrink-0" size={22} />,
      badge: 'bg-amber-500 text-white',
      badgeText: '🟡 CẦN CHÚ Ý',
      titleColor: 'text-amber-800',
      textColor: 'text-amber-700',
    },
    LOW: {
      border: 'border-blue-200',
      bg: 'bg-blue-50',
      headerBg: 'bg-blue-100',
      icon: <AlertTriangle className="text-blue-500 shrink-0" size={22} />,
      badge: 'bg-blue-500 text-white',
      badgeText: '🔵 THÔNG TIN',
      titleColor: 'text-blue-800',
      textColor: 'text-blue-700',
    },
  };

  const c = config[alert.severity] ?? config.LOW;

  return (
    <div className={cn('rounded-xl border overflow-hidden shadow-sm', c.border)}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn('w-full flex items-center gap-3 p-4 text-left transition-colors', c.headerBg, 'hover:opacity-90')}
      >
        {c.icon}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={cn('text-xs font-bold px-2 py-0.5 rounded-full', c.badge)}>{c.badgeText}</span>
          </div>
          <p className={cn('font-semibold text-base mt-1 leading-tight', c.titleColor)}>{alert.title}</p>
        </div>
        <div className="shrink-0 text-gray-400">
          {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </div>
      </button>

      {/* Expandable body */}
      {expanded && (
        <div className={cn('px-4 pb-4 pt-3 space-y-3', c.bg)}>
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Chi tiết</p>
            <p className={cn('text-sm leading-relaxed whitespace-pre-line', c.textColor)}>
              {alert.description}
            </p>
          </div>
          <div className="bg-white/60 rounded-lg p-3 border border-white">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Lời khuyên</p>
            <p className={cn('text-sm font-medium leading-relaxed', c.textColor)}>{alert.recommendation}</p>
          </div>
        </div>
      )}
    </div>
  );
}

interface InteractionAlertCardsProps {
  result: IEvaluationResponse;
  onClose: () => void;
}

export function InteractionAlertCards({ result, onClose }: InteractionAlertCardsProps) {
  const highAlerts = result.alerts.filter(a => a.severity === 'HIGH');
  const mediumAlerts = result.alerts.filter(a => a.severity === 'MEDIUM');
  const lowAlerts = result.alerts.filter(a => a.severity === 'LOW');
  const isSafe = result.alerts.length === 0;

  return (
    <div className="space-y-6">
      {/* Summary header */}
      <div className={cn(
        'rounded-2xl p-6 border flex items-start gap-4',
        isSafe ? 'bg-emerald-50 border-emerald-200' : highAlerts.length > 0 ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200'
      )}>
        <div className={cn(
          'w-14 h-14 rounded-full flex items-center justify-center shrink-0',
          isSafe ? 'bg-emerald-100' : highAlerts.length > 0 ? 'bg-red-100' : 'bg-amber-100'
        )}>
          {isSafe
            ? <CheckCircle2 className="text-emerald-600" size={30} />
            : <AlertOctagon className={highAlerts.length > 0 ? 'text-red-600' : 'text-amber-600'} size={30} />
          }
        </div>
        <div>
          <h2 className={cn(
            'text-xl font-extrabold',
            isSafe ? 'text-emerald-800' : highAlerts.length > 0 ? 'text-red-800' : 'text-amber-800'
          )}>
            {isSafe
              ? '✅ Không phát hiện tương tác nguy hiểm'
              : `Phát hiện ${result.alerts.length} cảnh báo tương tác thuốc`
            }
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Đã phân tích <strong>{result.totalDrugsAnalyzed}</strong> loại thuốc trong Tủ thuốc.
            {!isSafe && <span className="text-red-600 font-semibold"> Vui lòng đọc kỹ các cảnh báo bên dưới.</span>}
          </p>
        </div>
      </div>

      {/* Medical Disclaimer Banner */}
      <div className="bg-gray-100 border border-gray-200 rounded-xl px-4 py-3 flex items-start gap-2">
        <span className="text-gray-400 text-xl mt-0.5">⚠️</span>
        <p className="text-xs text-gray-500 leading-relaxed">
          <strong className="text-gray-700">Miễn trừ trách nhiệm y tế:</strong> Thông tin này chỉ mang tính chất tham khảo, không thay thế cho ý kiến của bác sĩ, dược sĩ chuyên khoa. Mediscan AI không chịu trách nhiệm về quyết định điều trị cuối cùng. Vui lòng tham vấn chuyên gia y tế trước khi thay đổi phác đồ sử dụng thuốc.
        </p>
      </div>

      {/* Alert cards */}
      {!isSafe && (
        <div className="space-y-4">
          {highAlerts.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-red-700 uppercase tracking-widest flex items-center gap-2">
                <AlertOctagon size={14} /> Cảnh báo nghiêm trọng ({highAlerts.length})
              </h3>
              {highAlerts.map((a, i) => <AlertCard key={i} alert={a} />)}
            </div>
          )}
          {mediumAlerts.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-amber-700 uppercase tracking-widest flex items-center gap-2">
                <AlertTriangle size={14} /> Cần chú ý ({mediumAlerts.length})
              </h3>
              {mediumAlerts.map((a, i) => <AlertCard key={i} alert={a} />)}
            </div>
          )}
          {lowAlerts.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-blue-700 uppercase tracking-widest">Thông tin thêm ({lowAlerts.length})</h3>
              {lowAlerts.map((a, i) => <AlertCard key={i} alert={a} />)}
            </div>
          )}
        </div>
      )}

      {/* Schedule suggestions */}
      {result.scheduleSuggestions.length > 0 && (
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 space-y-2">
          <h3 className="text-sm font-bold text-blue-800">💊 Gợi ý lịch uống thuốc an toàn</h3>
          <ul className="space-y-1.5">
            {result.scheduleSuggestions.map((s, i) => (
              <li key={i} className="text-sm text-blue-700 leading-relaxed">{s}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Close button */}
      <button
        onClick={onClose}
        className="w-full py-3 bg-gray-800 text-white rounded-xl font-semibold hover:bg-gray-900 transition-colors"
      >
        Quay lại Tủ Thuốc
      </button>
    </div>
  );
}
