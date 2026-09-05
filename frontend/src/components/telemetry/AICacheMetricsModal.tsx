'use client';

/**
 * [Stage 18] AI Cost & Performance Telemetry Modal Component.
 * Bảng điều khiển trực quan hóa năng lực tối ưu hóa chi phí AI,
 * tỷ lệ Cache Hit, số Token tiết kiệm và danh mục tri thức tự học (Active Learning).
 */

import React, { useEffect, useState } from 'react';
import {
  Zap,
  TrendingUp,
  Clock,
  ShieldCheck,
  Cpu,
  Layers,
  RefreshCw,
  X,
  Sparkles,
  Award,
} from 'lucide-react';
import { getAICacheMetrics, IAICacheMetrics } from '@/services/drugService';

interface AICacheMetricsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AICacheMetricsModal({ isOpen, onClose }: AICacheMetricsModalProps) {
  const [metrics, setMetrics] = useState<IAICacheMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchMetrics = async () => {
    setIsLoading(true);
    try {
      const data = await getAICacheMetrics();
      setMetrics(data);
    } catch (err) {
      console.warn('Could not fetch AI cache metrics:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchMetrics();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl bg-white rounded-2xl shadow-2xl border border-slate-100 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-5 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-500/20 border border-indigo-400/30 text-indigo-300">
              <Cpu className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold tracking-tight">AI Telemetry & Knowledge Store</h2>
                <span className="px-2 py-0.5 text-[11px] font-semibold bg-indigo-500/30 text-indigo-200 border border-indigo-400/30 rounded-full">
                  Stage 18 Enterprise
                </span>
              </div>
              <p className="text-xs text-slate-300">
                Đo lường thời gian thực: Tỷ lệ Cache Hit, Tokens tiết kiệm, & CSDL tự học
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchMetrics}
              disabled={isLoading}
              className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
              title="Làm mới dữ liệu"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-indigo-400' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Key Metric 4-Box Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {/* Metric 1: Cache Hit Ratio */}
            <div className="p-4 rounded-xl bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-100 flex flex-col justify-between">
              <div className="flex items-center justify-between text-emerald-700">
                <span className="text-xs font-semibold uppercase tracking-wider">Cache Hit Ratio</span>
                <TrendingUp className="w-4 h-4" />
              </div>
              <div className="mt-2">
                <div className="text-2xl font-black text-emerald-800">
                  {metrics ? `${metrics.cache_hit_ratio_percent}%` : '--'}
                </div>
                <div className="text-[11px] text-emerald-600 font-medium mt-0.5">
                  Độ trễ tức thì $O(1)$ (&lt;0.01ms)
                </div>
              </div>
            </div>

            {/* Metric 2: Estimated Tokens Saved */}
            <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-50 to-purple-50 border border-indigo-100 flex flex-col justify-between">
              <div className="flex items-center justify-between text-indigo-700">
                <span className="text-xs font-semibold uppercase tracking-wider">Tokens Tiết Kiệm</span>
                <Zap className="w-4 h-4" />
              </div>
              <div className="mt-2">
                <div className="text-2xl font-black text-indigo-800">
                  {metrics ? metrics.estimated_tokens_saved_all_time.toLocaleString() : '--'}
                </div>
                <div className="text-[11px] text-indigo-600 font-medium mt-0.5">
                  {metrics ? `+${metrics.estimated_tokens_saved_session} phiên này` : ''}
                </div>
              </div>
            </div>

            {/* Metric 3: Latency Saved */}
            <div className="p-4 rounded-xl bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-100 flex flex-col justify-between">
              <div className="flex items-center justify-between text-amber-700">
                <span className="text-xs font-semibold uppercase tracking-wider">Thời Gian Chờ Giảm</span>
                <Clock className="w-4 h-4" />
              </div>
              <div className="mt-2">
                <div className="text-2xl font-black text-amber-800">
                  {metrics ? `${metrics.estimated_latency_saved_seconds}s` : '--'}
                </div>
                <div className="text-[11px] text-amber-600 font-medium mt-0.5">
                  Tiết kiệm cho người dùng
                </div>
              </div>
            </div>

            {/* Metric 4: Human Verified */}
            <div className="p-4 rounded-xl bg-gradient-to-br from-blue-50 to-cyan-50 border border-blue-100 flex flex-col justify-between">
              <div className="flex items-center justify-between text-blue-700">
                <span className="text-xs font-semibold uppercase tracking-wider">Đã Kiểm Chứng</span>
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div className="mt-2">
                <div className="text-2xl font-black text-blue-800">
                  {metrics ? metrics.storage_stats.verified_count : '--'}
                </div>
                <div className="text-[11px] text-blue-600 font-medium mt-0.5">
                  {metrics ? `${metrics.storage_stats.pending_review_count} chờ duyệt` : ''}
                </div>
              </div>
            </div>
          </div>

          {/* Multi-Tier Storage Breakdown */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 mb-3">
              <Layers className="w-4 h-4 text-indigo-600" />
              Kiến Trúc Đa Tầng CSDL & Cache (Multi-Tier Architecture)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 bg-white rounded-lg border border-slate-200">
                <div className="font-semibold text-slate-800">Tier 1: Gold Standard DAV</div>
                <div className="text-slate-500 mt-1">105 thuốc chuẩn hóa quốc gia có số đăng ký & liều tối đa.</div>
                <div className="mt-2 text-emerald-600 font-bold">100% Offline</div>
              </div>
              <div className="p-3 bg-white rounded-lg border border-slate-200">
                <div className="font-semibold text-slate-800">Tier 2: Extended Master DB</div>
                <div className="text-slate-500 mt-1">11.498+ biệt dược generic bao phủ toàn diện thị trường.</div>
                <div className="mt-2 text-indigo-600 font-bold">In-Memory Hash Map</div>
              </div>
              <div className="p-3 bg-white rounded-lg border border-slate-200">
                <div className="font-semibold text-slate-800">Tier 2.5: Learned Store (Stage 18)</div>
                <div className="text-slate-500 mt-1">
                  {metrics ? `${metrics.storage_stats.total_learned_drugs} thuốc/TPCN` : 'Đang tải...'} tự học từ LLM & người dùng.
                </div>
                <div className="mt-2 text-purple-600 font-bold">Active Learning + Anti-Poisoning</div>
              </div>
            </div>
          </div>

          {/* Top Reused Drugs (ROI Leaderboard) */}
          <div className="border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-4 py-3 bg-slate-100/80 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-800 uppercase tracking-wider">
                <Award className="w-4 h-4 text-amber-500" />
                Top Chế Phẩm Tái Sử Dụng Nhiều Nhất (ROI Leaderboard)
              </div>
              <span className="text-[11px] text-slate-500 font-medium">
                Tự học 1 lần - Miễn phí vĩnh viễn
              </span>
            </div>
            <div className="divide-y divide-slate-100 text-xs">
              {metrics && metrics.top_reused_drugs && metrics.top_reused_drugs.length > 0 ? (
                metrics.top_reused_drugs.map((drug, idx) => (
                  <div key={idx} className="p-3.5 flex items-center justify-between hover:bg-slate-50/50 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="w-6 h-6 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-bold text-[11px]">
                        {idx + 1}
                      </div>
                      <div>
                        <div className="font-semibold text-slate-800 flex items-center gap-2">
                          {drug.brand_name}
                          {drug.is_supplement && (
                            <span className="px-1.5 py-0.5 text-[10px] bg-emerald-100 text-emerald-800 rounded font-medium">
                              🌿 TPCN
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          {drug.active_ingredient || 'Đang cập nhật'}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="font-bold text-indigo-700">{drug.hit_count} lượt hit</div>
                        <div className="text-[10px] text-slate-400">0 token / 0ms</div>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                          drug.status === 'VERIFIED'
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                            : drug.status === 'USER_CORRECTED'
                            ? 'bg-blue-100 text-blue-800 border border-blue-200'
                            : 'bg-amber-100 text-amber-800 border border-amber-200'
                        }`}
                      >
                        {drug.status === 'VERIFIED'
                          ? 'Đã kiểm chứng'
                          : drug.status === 'USER_CORRECTED'
                          ? 'Người dùng sửa'
                          : 'Chờ duyệt'}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-6 text-center text-slate-400 text-xs">
                  Chưa có lượt tái sử dụng nào được ghi nhận. Quét hoặc tìm kiếm một thuốc mới để bắt đầu.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
            <span>Được bảo vệ bởi cơ chế Anti-Poisoning & Active Learning Loop</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-medium transition-colors"
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
}
