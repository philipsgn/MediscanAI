# Drug Database Service - Local DB + OpenFDA API Integration
# Cung cấp tra cứu thông tin thuốc chuẩn hóa: hoạt chất, nhóm điều trị, liều tối đa, chống chỉ định
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class DrugDatabase:
    """Unified drug database: Local JSON + OpenFDA API fallback."""

    def __init__(self) -> None:
        self.local_db_path = Path(__file__).parent.parent / "data" / "vietnam_drugs_db.json"
        self.local_db: list[dict[str, Any]] = []
        self.brand_to_drug: dict[str, dict[str, Any]] = {}
        self.ingredient_to_drugs: dict[str, list[dict[str, Any]]] = {}
        self._openfda_brand_cache: dict[str, Optional[dict[str, Any]]] = {}
        self._openfda_ingredient_cache: dict[str, list[dict[str, Any]]] = {}
        self._load_local_db()

    def _load_local_db(self) -> None:
        try:
            with open(self.local_db_path, "r", encoding="utf-8") as f:
                self.local_db = json.load(f)
            
            # Build indexes
            for drug in self.local_db:
                brand_lower = drug.get("brand_name", "").lower().strip()
                if brand_lower:
                    self.brand_to_drug[brand_lower] = drug
                
                ingredients = drug.get("active_ingredient", "")
                if ingredients:
                    for ing in ingredients.split("/"):
                        ing_clean = ing.strip().lower()
                        if ing_clean not in self.ingredient_to_drugs:
                            self.ingredient_to_drugs[ing_clean] = []
                        self.ingredient_to_drugs[ing_clean].append(drug)
            
            logger.info(f"Loaded {len(self.local_db)} drugs from local DB")
        except (OSError, json.JSONDecodeError) as e:
            # [P3/F3.5] File DB hỏng/thiếu quyền đọc (OSError) hoặc JSON lỗi
            # cấu trúc → khởi động với DB rỗng (graceful) nhưng log rõ loại lỗi;
            # không nuốt chung các lỗi lập trình khác.
            logger.error("Failed to load local drug DB (%s): %s", type(e).__name__, e)
            self.local_db = []

    # ─────────────────────────────────────────────────────────────────────────
    # Local DB Lookup
    # ─────────────────────────────────────────────────────────────────────────

    def find_by_brand_exact(self, brand_name: str) -> Optional[dict[str, Any]]:
        """Tìm thuốc theo tên thương mại chính xác (case-insensitive)."""
        return self.brand_to_drug.get(brand_name.lower().strip())

    def find_by_brand_fuzzy(self, brand_name: str, threshold: int = 70) -> Optional[dict[str, Any]]:
        """Tìm thuốc theo tên thương mại dùng fuzzy matching (rapidfuzz)."""
        from rapidfuzz import process, fuzz

        if not self.brand_to_drug:
            return None

        brands = list(self.brand_to_drug.keys())
        best = process.extractOne(
            brand_name.lower().strip(),
            brands,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=threshold,
        )
        if best:
            match_str, score, _ = best
            return self.brand_to_drug.get(match_str)
        return None

    def find_by_ingredient(self, ingredient: str) -> list[dict[str, Any]]:
        """Tìm tất cả thuốc chứa hoạt chất cụ thể."""
        return self.ingredient_to_drugs.get(ingredient.lower().strip(), [])

    def get_drug_info(self, drug_id: str) -> Optional[dict[str, Any]]:
        """Lấy thông tin đầy đủ theo ID thuốc."""
        for drug in self.local_db:
            if drug.get("id") == drug_id:
                return drug
        return None

    def search_drugs(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Tìm kiếm thuốc theo từ khóa (brand name hoặc hoạt chất)."""
        from rapidfuzz import process, fuzz

        query_lower = query.lower().strip()
        results = []

        # Search by brand name fuzzy
        brands = list(self.brand_to_drug.keys())
        matches = process.extract(
            query_lower,
            brands,
            scorer=fuzz.token_sort_ratio,
            limit=limit,
            score_cutoff=60,
        )
        for match_str, score, _ in matches:
            drug = self.brand_to_drug[match_str]
            drug_copy = drug.copy()
            drug_copy["_match_score"] = score
            drug_copy["_match_type"] = "brand"
            results.append(drug_copy)

        # Search by ingredient
        for ing, drugs in self.ingredient_to_drugs.items():
            if query_lower in ing:
                for drug in drugs:
                    drug_copy = drug.copy()
                    drug_copy["_match_score"] = 100
                    drug_copy["_match_type"] = "ingredient"
                    results.append(drug_copy)

        # Deduplicate by ID
        seen_ids = set()
        unique_results = []
        for drug in results:
            if drug["id"] not in seen_ids:
                seen_ids.add(drug["id"])
                unique_results.append(drug)

        return sorted(unique_results, key=lambda d: d.get("_match_score", 0), reverse=True)[:limit]

    # ─────────────────────────────────────────────────────────────────────────
    # OpenFDA API Integration
    # ─────────────────────────────────────────────────────────────────────────

    async def fetch_openfda_by_brand(self, brand_name: str) -> Optional[dict[str, Any]]:
        """Tra cứu OpenFDA theo tên thương mại.

        [P2/F3.4] Đã xóa gate `if not settings.OPENFDA_API_KEY: return None`:
        OpenFDA label API hoạt động KHÔNG cần key (đã xác minh thực nghiệm
        HTTP 200 keyless trong remediation P2). API key (nếu cấu hình) vẫn
        được đính kèm để hưởng rate-limit cao hơn."""
        try:
            import re
            clean_name = re.sub(r"[^a-zA-Z0-9\s]", " ", brand_name).strip()
            if not clean_name or len(clean_name) < 2:
                return None

            cache_key = clean_name.lower()
            if cache_key in self._openfda_brand_cache:
                return self._openfda_brand_cache[cache_key]

            async with httpx.AsyncClient(timeout=6.0) as client:
                params = {
                    "search": f'openfda.brand_name:"{clean_name}"',
                    "limit": 5,
                }
                if settings.OPENFDA_API_KEY:
                    params["api_key"] = settings.OPENFDA_API_KEY

                resp = await client.get(f"{settings.OPENFDA_BASE_URL}/label.json", params=params)
                resp.raise_for_status()
                data = resp.json()

                results = data.get("results", [])
                if results:
                    res = self._normalize_openfda_result(results[0])
                    self._openfda_brand_cache[cache_key] = res
                    return res
            self._openfda_brand_cache[cache_key] = None
        except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError) as e:
            logger.warning(
                "OpenFDA lookup failed for %s (%s): %s",
                brand_name,
                type(e).__name__,
                e,
            )
            # Cache miss/failure to prevent repeated slow timeouts
            clean_k = re.sub(r"[^a-zA-Z0-9\s]", " ", brand_name).strip().lower()
            self._openfda_brand_cache[clean_k] = None
        return None

    async def fetch_openfda_by_ingredient(self, ingredient: str) -> list[dict[str, Any]]:
        """Tra cứu OpenFDA theo hoạt chất."""
        try:
            clean_ing = ingredient.strip().lower()
            if not clean_ing or len(clean_ing) < 2:
                return []

            if clean_ing in self._openfda_ingredient_cache:
                return self._openfda_ingredient_cache[clean_ing]

            async with httpx.AsyncClient(timeout=6.0) as client:
                params = {
                    "search": f"openfda.substance_name:{ingredient.strip()}",
                    "limit": 10,
                }
                if settings.OPENFDA_API_KEY:
                    params["api_key"] = settings.OPENFDA_API_KEY

                resp = await client.get(f"{settings.OPENFDA_BASE_URL}/label.json", params=params)
                resp.raise_for_status()
                data = resp.json()

                results = data.get("results", [])
                parsed = [self._normalize_openfda_result(r) for r in results]
                self._openfda_ingredient_cache[clean_ing] = parsed
                return parsed
        except Exception as e:  # noqa: BLE001
            logger.warning(f"OpenFDA ingredient lookup failed for {ingredient}: {e}")
            self._openfda_ingredient_cache[ingredient.strip().lower()] = []
        return []

    def _normalize_openfda_result(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Chuẩn hóa kết quả OpenFDA về format nội bộ."""
        openfda = raw.get("openfda", {})
        return {
            "source": "openfda",
            "brand_name": (openfda.get("brand_name") or [None])[0],
            "generic_name": (openfda.get("generic_name") or [None])[0],
            "active_ingredient": openfda.get("substance_name", []),
            "strength": (openfda.get("strength") or [None])[0],
            "route": openfda.get("route", []),
            "dosage_form": (openfda.get("dosage_form") or [None])[0],
            "warnings": raw.get("warnings", []),
            "contraindications": raw.get("contraindications", []),
            "drug_interactions": raw.get("drug_interactions", []),
            "use_in_specific_populations": raw.get("use_in_specific_populations", []),
            "spl_id": raw.get("id"),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Unified Lookup (Local First, OpenFDA Fallback)
    # ─────────────────────────────────────────────────────────────────────────

    async def get_drug_full_info(self, brand_name: str, ingredient_hint: Optional[str] = None) -> Optional[dict[str, Any]]:
        """Lấy thông tin đầy đủ: ưu tiên local DB, fallback OpenFDA."""
        # 1. Exact match local
        local = self.find_by_brand_exact(brand_name)
        if local:
            return {"source": "local", **local}

        # 2. Fuzzy match local
        local_fuzzy = self.find_by_brand_fuzzy(brand_name)
        if local_fuzzy:
            return {"source": "local_fuzzy", **local_fuzzy}

        # 3. OpenFDA by brand
        openfda_brand = await self.fetch_openfda_by_brand(brand_name)
        if openfda_brand:
            return openfda_brand

        # 3b. OpenFDA by brand treated as active ingredient/substance
        openfda_substance = await self.fetch_openfda_by_ingredient(brand_name)
        if openfda_substance:
            res_sub = openfda_substance[0]
            res_sub["source"] = "openfda_ingredient"
            return res_sub

        # 4. OpenFDA by ingredient hint
        if ingredient_hint:
            openfda_ing = await self.fetch_openfda_by_ingredient(ingredient_hint)
            if openfda_ing:
                return {"source": "openfda_ingredient", "results": openfda_ing}

        return None

    def get_max_daily_dose(self, ingredient: str) -> Optional[float]:
        """Lấy liều tối đa/ngày từ local DB."""
        import re

        drugs = self.find_by_ingredient(ingredient)
        if not drugs:
            return None

        max_doses = []
        for drug in drugs:
            max_dose_str = drug.get("max_daily_dosage", "")
            match = re.search(r"(\d+(?:\.\d+)?)\s*mg", max_dose_str, re.IGNORECASE)
            if match:
                max_doses.append(float(match.group(1)))

        return max(max_doses) if max_doses else None


# Singleton
drug_database = DrugDatabase()