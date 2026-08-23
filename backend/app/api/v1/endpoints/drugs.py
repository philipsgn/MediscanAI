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
