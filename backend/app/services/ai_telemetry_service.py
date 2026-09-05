"""
AI Cost & Performance Telemetry Service (Stage 18).
Đo lường & Giám sát hiệu năng AI:
1. Tỷ lệ Cache Hit Ratio (%).
2. Ước tính Tokens tiết kiệm được (Estimated Tokens Saved).
3. Ước tính Chi phí tiết kiệm (USD Saved).
4. Ước tính Thời gian giảm thiểu độ trễ (Latency Saved).
5. Thống kê kho tri thức tự học (Verified vs Pending Review).
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.learned_drug import LearnedDrugModel

logger = logging.getLogger(__name__)


class AITelemetryService:
    """Singleton service giám sát chi phí và độ hiệu quả của tầng AI Cache."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total_lookups: int = 0
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._tokens_per_llm_call: int = 350  # ~250 prompt + ~100 completion tokens
        self._cost_per_token_usd: float = 0.0000005  # ~$0.5 per 1M tokens (Gemini Flash / GPT-4o-mini)
        self._latency_saved_per_hit_sec: float = 1.2  # LLM API trung bình ~1.2s vs Cache ~0.0001s

    def record_cache_hit(self, brand_name: str) -> None:
        """Ghi nhận 1 lượt tra cứu thành công từ Cache (L1 RAM / L2 Database)."""
        with self._lock:
            self._total_lookups += 1
            self._cache_hits += 1

    def record_cache_miss(self, brand_name: str) -> None:
        """Ghi nhận 1 lượt MISS cache phải gọi LLM bên ngoài."""
        with self._lock:
            self._total_lookups += 1
            self._cache_misses += 1

    async def get_metrics(self, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """
        Tổng hợp toàn bộ chỉ số vận hành và ROI của tầng AI Cache.
        """
        with self._lock:
            total_lookups = self._total_lookups
            cache_hits = self._cache_hits
            cache_misses = self._cache_misses

        # Nếu chưa có lookup nào trong phiên hiện tại, tính toán từ db hits nếu có
        hit_ratio = round((cache_hits / total_lookups * 100.0), 2) if total_lookups > 0 else 100.0
        tokens_saved = cache_hits * self._tokens_per_llm_call
        cost_saved = round(tokens_saved * self._cost_per_token_usd, 5)
        latency_saved_sec = round(cache_hits * self._latency_saved_per_hit_sec, 2)

        # Truy vấn thống kê từ Database
        db_stats = {
            "total_learned_drugs": 0,
            "verified_count": 0,
            "pending_review_count": 0,
            "user_corrected_count": 0,
            "cumulative_db_hits": 0,
        }
        top_reused_drugs: List[Dict[str, Any]] = []

        should_close_session = False
        if session is None:
            try:
                session = AsyncSessionLocal()
                should_close_session = True
            except Exception as e:
                logger.warning("Could not create DB session for telemetry: %s", e)
                session = None

        if session is not None:
            try:
                # Tổng số thuốc đã học
                count_res = await session.execute(select(func.count(LearnedDrugModel.id)))
                db_stats["total_learned_drugs"] = count_res.scalar_one_or_none() or 0

                # Số thuốc đã verified
                verified_res = await session.execute(
                    select(func.count(LearnedDrugModel.id)).where(
                        LearnedDrugModel.verification_status == "VERIFIED"
                    )
                )
                db_stats["verified_count"] = verified_res.scalar_one_or_none() or 0

                # Số thuốc đang chờ duyệt
                pending_res = await session.execute(
                    select(func.count(LearnedDrugModel.id)).where(
                        LearnedDrugModel.verification_status == "PENDING_REVIEW"
                    )
                )
                db_stats["pending_review_count"] = pending_res.scalar_one_or_none() or 0

                # Số thuốc do người dùng chỉnh sửa đúng
                corr_res = await session.execute(
                    select(func.count(LearnedDrugModel.id)).where(
                        LearnedDrugModel.verification_status == "USER_CORRECTED"
                    )
                )
                db_stats["user_corrected_count"] = corr_res.scalar_one_or_none() or 0

                # Tổng hit count tích lũy trong DB
                cum_hits_res = await session.execute(select(func.sum(LearnedDrugModel.hit_count)))
                db_stats["cumulative_db_hits"] = cum_hits_res.scalar_one_or_none() or 0

                # Top thuốc được tái sử dụng nhiều nhất
                top_query = (
                    select(LearnedDrugModel)
                    .order_by(desc(LearnedDrugModel.hit_count))
                    .limit(5)
                )
                top_res = await session.execute(top_query)
                for drug in top_res.scalars().all():
                    top_reused_drugs.append(
                        {
                            "brand_name": drug.brand_name,
                            "active_ingredient": drug.active_ingredient,
                            "hit_count": drug.hit_count,
                            "status": drug.verification_status,
                            "is_supplement": drug.is_supplement,
                        }
                    )
            except Exception as e:
                logger.warning("Error fetching learned drugs telemetry from DB: %s", e)
            finally:
                if should_close_session:
                    await session.close()

        # Nếu DB có tổng cumulative hits lớn hơn phiên in-memory, kết hợp để báo cáo chính xác
        total_tokens_all_time = max(tokens_saved, (db_stats["cumulative_db_hits"] or 0) * self._tokens_per_llm_call)
        total_cost_all_time = round(total_tokens_all_time * self._cost_per_token_usd, 5)

        return {
            "total_lookups": total_lookups,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "cache_hit_ratio_percent": hit_ratio,
            "estimated_tokens_saved_session": tokens_saved,
            "estimated_tokens_saved_all_time": total_tokens_all_time,
            "estimated_cost_saved_usd": total_cost_all_time,
            "estimated_latency_saved_seconds": latency_saved_sec,
            "storage_stats": db_stats,
            "top_reused_drugs": top_reused_drugs,
        }


# Singleton instance
ai_telemetry_service = AITelemetryService()
