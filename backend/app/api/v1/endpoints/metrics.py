"""
AI & System Metrics Endpoint (Stage 18).
Expose các chỉ số Telemetry giám sát chi phí và hiệu quả của tầng AI Cache.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.ai_telemetry_service import ai_telemetry_service

router = APIRouter(prefix="/metrics", tags=["AI & System Metrics"])


@router.get(
    "/ai-cache",
    response_model=Dict[str, Any],
    summary="Thống kê Telemetry của tầng AI Cache (Tokens saved, ROI, Hit Ratio)",
)
async def get_ai_cache_metrics(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Trả về toàn bộ chỉ số hiệu năng và chi phí của AI Cache (Stage 18):
    - total_lookups: Tổng số lần tra cứu
    - cache_hits: Số lần trúng cache
    - cache_misses: Số lần gọi LLM bên ngoài
    - cache_hit_ratio_percent: Tỷ lệ trúng cache (%)
    - estimated_tokens_saved_all_time: Tổng tokens tiết kiệm được
    - estimated_cost_saved_usd: Tổng chi phí USD tiết kiệm
    - estimated_latency_saved_seconds: Tổng độ trễ giảm thiểu
    - storage_stats: Thống kê CSDL (verified vs pending review)
    - top_reused_drugs: Danh sách các thuốc tái sử dụng nhiều nhất
    """
    return await ai_telemetry_service.get_metrics(session=db)
