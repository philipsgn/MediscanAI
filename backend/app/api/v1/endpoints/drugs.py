"""[S4-Closeout/F4.3] Drug Lookup API — autocomplete từ điển thuốc.

Nguồn dữ liệu: `drug_database.search_drugs()` (đã audit ✅ Stage 3) — tìm kiếm
đa tầng Local DB (Brand fuzzy + Ingredient substring) qua rapidfuzz. KHÔNG gọi
OpenFDA ở endpoint này (autocomplete phải nhanh, offline-safe; OpenFDA tier-4
chỉ chạy trong normalization pipeline khi local miss).

Wire-format: camelCase (alias_generator=to_camel) khớp IDrugSearchResult FE.
"""
from typing import List

from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool

from app.core.config import settings
from app.schemas import DrugSearchResult
from app.services.drug_database import drug_database

router = APIRouter(prefix="/drugs", tags=["Drug Lookup"])


@router.get(
    "/search",
    response_model=List[DrugSearchResult],
    summary="Tìm kiếm thuốc cho autocomplete (brand/hoạt chất)",
)
async def search_drugs(
    q: str = Query(
        ...,
        min_length=2,
        max_length=100,
        description="Từ khóa: tên thương mại (fuzzy) hoặc hoạt chất (substring)",
    ),
    limit: int = Query(
        default=None,
        ge=1,
        le=50,
        description="Số kết quả tối đa — mặc định đọc từ Settings "
        "(DRUG_SEARCH_DEFAULT_LIMIT), không hardcode ở đây",
    ),
) -> List[DrugSearchResult]:
    """Autocomplete rút gọn: brand_name / active_ingredient / strength.

    - `limit` không truyền → dùng `settings.DRUG_SEARCH_DEFAULT_LIMIT`.
    - rapidfuzz là CPU-bound sync → chạy qua run_in_threadpool để không block
      event loop (pattern giống ocr.py).
    - Endpoint read-only, không đụng pipeline chẩn đoán — an toàn CORS public.
    """
    effective_limit = limit if limit is not None else settings.DRUG_SEARCH_DEFAULT_LIMIT
    raw_results = await run_in_threadpool(drug_database.search_drugs, q, effective_limit)
    return [
        DrugSearchResult(
            drug_id=str(drug.get("id", "")),
            brand_name=str(drug.get("brand_name", "")),
            active_ingredient=drug.get("active_ingredient") or None,
            strength=str(drug.get("strength", "") or ""),
        )
        for drug in raw_results
    ]


from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class VerifyLearnedDrugRequest(BaseModel):
    brand_name: str = Field(..., min_length=1, max_length=255)
    confirmed_active_ingredient: str = Field(..., min_length=1, max_length=500)
    strength: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=255)
    is_supplement: bool = False
    user_notes: Optional[str] = Field(None, max_length=1000)


class VerifyLearnedDrugResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]


from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db


@router.post(
    "/verify-learned",
    response_model=VerifyLearnedDrugResponse,
    summary="Active Learning: Xác thực hoặc chỉnh sửa hoạt chất của thuốc tự học (Anti-Poisoning)",
)
async def verify_learned_drug(
    payload: VerifyLearnedDrugRequest,
    db: AsyncSession = Depends(get_db),
) -> VerifyLearnedDrugResponse:
    """
    Nhận phản hồi từ người dùng tại giao diện Human-in-the-Loop (HITL) (Stage 18).
    - Nếu người dùng xác nhận đúng: Chuyển verification_status = "VERIFIED", tăng verified_count.
    - Nếu người dùng sửa hoạt chất khác: Chuyển verification_status = "USER_CORRECTED", cập nhật lại hoạt chất chuẩn
      vào RAM, File, và Database để chống ngộ độc cache vĩnh viễn (Anti-Poisoning).
    """
    updated = await drug_database.verify_and_update_learned_drug(
        brand_name=payload.brand_name,
        confirmed_active_ingredient=payload.confirmed_active_ingredient,
        strength=payload.strength,
        category=payload.category,
        is_supplement=payload.is_supplement,
        user_notes=payload.user_notes,
        session=db,
    )
    return VerifyLearnedDrugResponse(
        success=True,
        message=f"Đã cập nhật trạng thái {updated.get('verification_status')} cho '{payload.brand_name}'",
        data=updated,
    )
