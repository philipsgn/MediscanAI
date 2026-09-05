# Drug Database Service - Local DB + OpenFDA API Integration
# Cung cấp tra cứu thông tin thuốc chuẩn hóa: hoạt chất, nhóm điều trị, liều tối đa, chống chỉ định
from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from typing import Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class DrugDatabase:
    """Unified drug database: Local JSON + OpenFDA API fallback."""

    def __init__(self) -> None:
        self.local_db_path = Path(__file__).parent.parent / "data" / "vietnam_drugs_db.json"
        self.extended_db_path = Path(__file__).parent.parent / "data" / "extended_medicines_db.json"
        self.learned_cache_path = Path(__file__).parent.parent / "data" / "learned_drugs_cache.json"
        
        # Tier 1: Gold Standard Vietnam DB (105 curated drugs)
        self.local_db: list[dict[str, Any]] = []
        self.brand_to_drug: dict[str, dict[str, Any]] = {}
        self.ingredient_to_drugs: dict[str, list[dict[str, Any]]] = {}

        # Tier 2: Extended Master Registry (11,400+ generic medicines)
        self.extended_db: list[dict[str, Any]] = []
        self.extended_brand_to_drug: dict[str, dict[str, Any]] = {}
        self.extended_ingredient_to_drugs: dict[str, list[dict[str, Any]]] = {}

        # Tier 2.5: Dynamic Learned Drugs Cache (AI-resolved supplements & rare drugs)
        self.learned_brand_to_drug: dict[str, dict[str, Any]] = {}
        self._cache_lock = threading.Lock()

        self._openfda_brand_cache: dict[str, Optional[dict[str, Any]]] = {}
        self._openfda_ingredient_cache: dict[str, list[dict[str, Any]]] = {}
        self._load_local_db()

    def _load_local_db(self) -> None:
        # 1. Nạp Tier 1: Gold Standard Vietnam
        try:
            with open(self.local_db_path, "r", encoding="utf-8") as f:
                self.local_db = json.load(f)
            
            for drug in self.local_db:
                brand_lower = drug.get("brand_name", "").lower().strip()
                if brand_lower:
                    self.brand_to_drug[brand_lower] = drug
                    base_brand = re.sub(r"\s*\d+(?:[\.,]\d+)?\s*(?:mg|g|ml|mcg|iu|%|\/).*$", "", brand_lower).strip()
                    if base_brand and base_brand not in self.brand_to_drug:
                        self.brand_to_drug[base_brand] = drug
                
                ingredients = drug.get("active_ingredient", "")
                if ingredients:
                    for ing in ingredients.split("/"):
                        ing_clean = ing.strip().lower()
                        if ing_clean not in self.ingredient_to_drugs:
                            self.ingredient_to_drugs[ing_clean] = []
                        self.ingredient_to_drugs[ing_clean].append(drug)
            
            logger.info("Loaded %d drugs from Tier 1 local DB (Gold Standard)", len(self.local_db))
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Failed to load local drug DB (%s): %s", type(e).__name__, e)
            self.local_db = []

        # 2. Nạp Tier 2: Extended Master Registry (nếu tồn tại)
        if self.extended_db_path.exists():
            try:
                with open(self.extended_db_path, "r", encoding="utf-8") as f:
                    self.extended_db = json.load(f)
                
                for drug in self.extended_db:
                    b_full = drug.get("brand_name", "").lower().strip()
                    b_base = drug.get("base_brand_name", "").lower().strip()
                    if b_full and b_full not in self.extended_brand_to_drug:
                        self.extended_brand_to_drug[b_full] = drug
                    if b_base and b_base not in self.extended_brand_to_drug:
                        self.extended_brand_to_drug[b_base] = drug

                    # Index thêm dạng gọt bỏ dạng bào chế (VD: "Aciloc 150 Tablet" -> "aciloc 150")
                    b_no_form = re.sub(
                        r"\b(tablet|capsule|syrup|injection|drops|cream|gel|ointment|suspension|powder|respules|sr|er|cr|dr|dt|forte|duo|plus)\b",
                        "",
                        b_full,
                        flags=re.IGNORECASE,
                    ).strip()
                    b_no_form = re.sub(r"\s+", " ", b_no_form).strip()
                    if b_no_form and b_no_form not in self.extended_brand_to_drug:
                        self.extended_brand_to_drug[b_no_form] = drug

                    # Index thêm dạng không dấu gạch ngang / khoảng trắng
                    b_clean_no_hyphen = re.sub(r"[-\s]+", " ", b_base).strip()
                    if b_clean_no_hyphen and b_clean_no_hyphen not in self.extended_brand_to_drug:
                        self.extended_brand_to_drug[b_clean_no_hyphen] = drug

                    ingredients = drug.get("active_ingredient", "")
                    if ingredients:
                        for ing in ingredients.split("/"):
                            ing_clean = ing.strip().lower()
                            if ing_clean not in self.extended_ingredient_to_drugs:
                                self.extended_ingredient_to_drugs[ing_clean] = []
                            self.extended_ingredient_to_drugs[ing_clean].append(drug)

                logger.info("Loaded %d drugs from Tier 2 Extended Master Registry", len(self.extended_db))
            except (OSError, json.JSONDecodeError) as e:
                logger.error("Failed to load extended drug DB (%s): %s", type(e).__name__, e)
                self.extended_db = []

        # 3. Nạp Tier 2.5: Dynamic Learned Drugs Cache (TPCN / Thuốc lạ học từ LLM)
        if self.learned_cache_path.exists():
            try:
                with open(self.learned_cache_path, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                if isinstance(cache_data, dict):
                    for k, drug in cache_data.items():
                        k_clean = str(k).lower().strip()
                        self.learned_brand_to_drug[k_clean] = drug
                        b_name = str(drug.get("brand_name", "")).lower().strip()
                        if b_name:
                            self.learned_brand_to_drug[b_name] = drug
                    logger.info("Loaded %d learned drugs from Tier 2.5 Dynamic Cache", len(cache_data))
            except Exception as e:
                logger.warning("Failed to load learned drugs cache (%s): %s", type(e).__name__, e)

    # ─────────────────────────────────────────────────────────────────────────
    # Local DB Lookup (Dual-Tier + Learned Cache Architecture)
    # ─────────────────────────────────────────────────────────────────────────

    def find_by_brand_exact(self, brand_name: str) -> Optional[dict[str, Any]]:
        """Tìm thuốc theo tên thương mại chính xác (case-insensitive) qua Dual-Tier + Learned Cache."""
        if not brand_name:
            return None
        b_clean = brand_name.lower().strip()

        # 1. Khớp trực tiếp Tier 1
        res = self.brand_to_drug.get(b_clean)
        if res:
            return res

        # 2. Khớp trực tiếp Tier 2
        res_ext = self.extended_brand_to_drug.get(b_clean)
        if res_ext:
            return res_ext

        # 2.5 Khớp trực tiếp Tier 2.5 (Dynamic Learned Cache)
        res_learned = self.learned_brand_to_drug.get(b_clean)
        if res_learned:
            res_learned["hit_count"] = res_learned.get("hit_count", 0) + 1
            try:
                from app.services.ai_telemetry_service import ai_telemetry_service
                ai_telemetry_service.record_cache_hit(b_clean)
            except Exception:
                pass
            return res_learned

        # 3. Base Brand Normalization (loại bỏ hàm lượng kèm theo kể cả số trần)
        base_name = re.sub(r"\s*\d+(?:[\.,]\d+)?\s*(?:mg|g|ml|mcg|iu|%|\/|\b).*$", "", b_clean).strip()
        if base_name and base_name != b_clean:
            if base_name in self.brand_to_drug:
                return self.brand_to_drug[base_name]
            if base_name in self.extended_brand_to_drug:
                return self.extended_brand_to_drug[base_name]
            if base_name in self.learned_brand_to_drug:
                l_drug = self.learned_brand_to_drug[base_name]
                l_drug["hit_count"] = l_drug.get("hit_count", 0) + 1
                try:
                    from app.services.ai_telemetry_service import ai_telemetry_service
                    ai_telemetry_service.record_cache_hit(base_name)
                except Exception:
                    pass
                return l_drug

        # 4. Gọt bỏ đuôi Tablet/Capsule/Syrup/Injection...
        no_form = re.sub(
            r"\b(tablet|capsule|syrup|injection|drops|cream|gel|ointment|suspension|powder|respules|sr|er|cr|dr|dt|forte|duo|plus)\b",
            "",
            b_clean,
            flags=re.IGNORECASE,
        ).strip()
        no_form = re.sub(r"\s+", " ", no_form).strip()
        if no_form and no_form != b_clean:
            if no_form in self.brand_to_drug:
                return self.brand_to_drug[no_form]
            if no_form in self.extended_brand_to_drug:
                return self.extended_brand_to_drug[no_form]
            if no_form in self.learned_brand_to_drug:
                l_drug = self.learned_brand_to_drug[no_form]
                l_drug["hit_count"] = l_drug.get("hit_count", 0) + 1
                try:
                    from app.services.ai_telemetry_service import ai_telemetry_service
                    ai_telemetry_service.record_cache_hit(no_form)
                except Exception:
                    pass
                return l_drug

        return None

    def find_by_brand_fuzzy(self, brand_name: str, threshold: int = 70) -> Optional[dict[str, Any]]:
        """Tìm thuốc theo tên thương mại dùng fuzzy matching qua Dual-Tier + Learned Cache."""
        from rapidfuzz import process, fuzz

        if not brand_name:
            return None
        term = brand_name.lower().strip()

        # 1. Ưu tiên khớp Tier 1 (Gold Standard VN)
        if self.brand_to_drug:
            best = process.extractOne(
                term,
                list(self.brand_to_drug.keys()),
                scorer=fuzz.token_sort_ratio,
                score_cutoff=threshold,
            )
            if best:
                return self.brand_to_drug.get(best[0])

        # 2. Khớp Tier 2 (Extended Master Registry) với ngưỡng an toàn cao >= 85
        if self.extended_brand_to_drug:
            best_ext = process.extractOne(
                term,
                list(self.extended_brand_to_drug.keys()),
                scorer=fuzz.token_sort_ratio,
                score_cutoff=max(threshold, 85),
            )
            if best_ext:
                matched_key = best_ext[0]
                # Bảo vệ an toàn y tế: không khớp nếu độ chênh lệch độ dài quá lớn
                if abs(len(term) - len(matched_key)) <= 2 or min(len(term), len(matched_key)) >= 8:
                    return self.extended_brand_to_drug.get(matched_key)

        # 3. Khớp Tier 2.5 (Learned Cache)
        if self.learned_brand_to_drug:
            best_learned = process.extractOne(
                term,
                list(self.learned_brand_to_drug.keys()),
                scorer=fuzz.token_sort_ratio,
                score_cutoff=max(threshold, 80),
            )
            if best_learned:
                matched_drug = self.learned_brand_to_drug.get(best_learned[0])
                if matched_drug:
                    matched_drug["hit_count"] = matched_drug.get("hit_count", 0) + 1
                    try:
                        from app.services.ai_telemetry_service import ai_telemetry_service
                        ai_telemetry_service.record_cache_hit(term)
                    except Exception:
                        pass
                return matched_drug

        return None

    def save_learned_drug(self, drug_data: dict[str, Any]) -> None:
        """Lưu trữ sản phẩm/thuốc lạ đã giải mã từ LLM vào Dynamic Cache (thread-safe)."""
        brand_raw = str(drug_data.get("brand_name", "")).strip()
        if not brand_raw:
            return
        b_clean = brand_raw.lower()
        with self._cache_lock:
            self.learned_brand_to_drug[b_clean] = drug_data
            base_name = re.sub(r"\s*\d+(?:[\.,]\d+)?\s*(?:mg|g|ml|mcg|iu|%|\/|\b).*$", "", b_clean).strip()
            if base_name and base_name != b_clean:
                self.learned_brand_to_drug[base_name] = drug_data

            try:
                cache_to_write = {}
                if self.learned_cache_path.exists():
                    try:
                        with open(self.learned_cache_path, "r", encoding="utf-8") as f:
                            cache_to_write = json.load(f)
                    except Exception:
                        cache_to_write = {}
                cache_to_write[b_clean] = drug_data
                with open(self.learned_cache_path, "w", encoding="utf-8") as f:
                    json.dump(cache_to_write, f, ensure_ascii=False, indent=2)
                logger.info("[drug_db] Successfully saved learned drug to cache: %s", brand_raw)
            except Exception as e:
                logger.warning("[drug_db] Failed to write learned drug cache (%s): %s", type(e).__name__, e)

    async def sync_learned_to_db(self, drug_data: dict[str, Any], session: Optional[Any] = None) -> None:
        """Đồng bộ bản ghi đã học vào CSDL quan hệ (PostgreSQL / SQLite) (Stage 18)."""
        brand_raw = str(drug_data.get("brand_name", "")).strip()
        if not brand_raw:
            return
        b_clean = brand_raw.lower()

        async def _do_sync(s: Any) -> None:
            from sqlalchemy import select
            from app.models.learned_drug import LearnedDrugModel

            query = select(LearnedDrugModel).where(LearnedDrugModel.brand_name_normalized == b_clean)
            res = await s.execute(query)
            row = res.scalar_one_or_none()
            if row:
                row.active_ingredient = drug_data.get("active_ingredient") or row.active_ingredient
                row.strength = drug_data.get("strength") or row.strength
                row.category = drug_data.get("category") or row.category
                row.is_supplement = bool(drug_data.get("is_supplement", False))
                row.hit_count = row.hit_count + 1
                row.notes = drug_data.get("notes") or row.notes
            else:
                new_row = LearnedDrugModel(
                    brand_name=brand_raw,
                    brand_name_normalized=b_clean,
                    active_ingredient=drug_data.get("active_ingredient"),
                    strength=drug_data.get("strength"),
                    category=drug_data.get("category"),
                    is_supplement=bool(drug_data.get("is_supplement", False)),
                    confidence_score=float(drug_data.get("confidence_score", 0.75)),
                    verification_status=str(drug_data.get("verification_status", "PENDING_REVIEW")),
                    hit_count=int(drug_data.get("hit_count", 1)),
                    verified_count=int(drug_data.get("verified_count", 0)),
                    notes=drug_data.get("notes"),
                    contraindications=drug_data.get("contraindications") or [],
                    source=str(drug_data.get("source", "ai_llm_inference")),
                )
                s.add(new_row)
            await s.commit()

        try:
            if session is not None:
                await _do_sync(session)
            else:
                from app.db.session import AsyncSessionLocal
                async with AsyncSessionLocal() as s:
                    await _do_sync(s)
            logger.info("[drug_db] Successfully synced learned drug to database: %s", brand_raw)
        except Exception as e:
            logger.warning("[drug_db] Could not sync learned drug to DB: %s", e)

    async def load_learned_from_db(self) -> None:
        """Nạp các thuốc tự học từ CSDL vào L1 RAM tại thời điểm khởi động (Stage 18)."""
        try:
            from sqlalchemy import select
            from app.db.session import AsyncSessionLocal
            from app.models.learned_drug import LearnedDrugModel

            async with AsyncSessionLocal() as session:
                query = select(LearnedDrugModel)
                res = await session.execute(query)
                rows = res.scalars().all()
                for row in rows:
                    drug_dict = {
                        "brand_name": row.brand_name,
                        "brand_name_normalized": row.brand_name_normalized,
                        "active_ingredient": row.active_ingredient,
                        "strength": row.strength,
                        "category": row.category,
                        "is_supplement": row.is_supplement,
                        "confidence_score": row.confidence_score,
                        "verification_status": row.verification_status,
                        "hit_count": row.hit_count,
                        "verified_count": row.verified_count,
                        "notes": row.notes,
                        "contraindications": row.contraindications or [],
                        "source": row.source,
                    }
                    with self._cache_lock:
                        self.learned_brand_to_drug[row.brand_name_normalized] = drug_dict
                logger.info("[drug_db] Loaded %d learned drugs from Database into L1 RAM", len(rows))
        except Exception as e:
            logger.warning("[drug_db] Could not load learned drugs from DB (%s): %s", type(e).__name__, e)

    async def verify_and_update_learned_drug(
        self,
        brand_name: str,
        confirmed_active_ingredient: str,
        strength: Optional[str] = None,
        category: Optional[str] = None,
        is_supplement: bool = False,
        user_notes: Optional[str] = None,
        session: Optional[Any] = None,
    ) -> dict[str, Any]:
        """
        Active Learning Loop & Anti-Poisoning (Stage 18):
        Cập nhật trạng thái xác thực từ người dùng (HITL).
        Nếu người dùng sửa hoạt chất khác so với AI gợi ý, lưu lại hoạt chất do người dùng sửa.
        """
        brand_raw = str(brand_name).strip()
        b_clean = brand_raw.lower()

        # 1. Cập nhật trong L1 RAM
        with self._cache_lock:
            existing = self.learned_brand_to_drug.get(b_clean, {})
            prev_ingredient = existing.get("active_ingredient", "")
            is_corrected = bool(prev_ingredient and prev_ingredient.lower() != confirmed_active_ingredient.lower())
            new_status = "USER_CORRECTED" if is_corrected else "VERIFIED"

            updated_data = {
                "brand_name": brand_raw,
                "brand_name_normalized": b_clean,
                "active_ingredient": confirmed_active_ingredient,
                "strength": strength or existing.get("strength"),
                "category": category or existing.get("category"),
                "is_supplement": is_supplement,
                "confidence_score": 0.95 if new_status == "VERIFIED" else 0.90,
                "verification_status": new_status,
                "hit_count": existing.get("hit_count", 1),
                "verified_count": existing.get("verified_count", 0) + 1,
                "notes": user_notes or existing.get("notes"),
                "contraindications": existing.get("contraindications", []),
                "source": "hitl_user_verification",
            }
            self.learned_brand_to_drug[b_clean] = updated_data
            base_name = re.sub(r"\s*\d+(?:[\.,]\d+)?\s*(?:mg|g|ml|mcg|iu|%|\/|\b).*$", "", b_clean).strip()
            if base_name and base_name != b_clean:
                self.learned_brand_to_drug[base_name] = updated_data

            # 2. Cập nhật vào L3 JSON File
            try:
                cache_to_write = {}
                if self.learned_cache_path.exists():
                    try:
                        with open(self.learned_cache_path, "r", encoding="utf-8") as f:
                            cache_to_write = json.load(f)
                    except Exception:
                        cache_to_write = {}
                cache_to_write[b_clean] = updated_data
                with open(self.learned_cache_path, "w", encoding="utf-8") as f:
                    json.dump(cache_to_write, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning("[drug_db] Error updating JSON cache during verification: %s", e)

        # 3. Cập nhật vào L2 Database
        async def _do_db_update(s: Any) -> None:
            from sqlalchemy import select
            from app.models.learned_drug import LearnedDrugModel

            query = select(LearnedDrugModel).where(LearnedDrugModel.brand_name_normalized == b_clean)
            res = await s.execute(query)
            row = res.scalar_one_or_none()
            if row:
                row.active_ingredient = confirmed_active_ingredient
                if strength:
                    row.strength = strength
                if category:
                    row.category = category
                row.is_supplement = is_supplement
                row.verification_status = new_status
                row.verified_count = row.verified_count + 1
                row.confidence_score = 0.95 if new_status == "VERIFIED" else 0.90
                if user_notes:
                    row.notes = user_notes
            else:
                new_row = LearnedDrugModel(
                    brand_name=brand_raw,
                    brand_name_normalized=b_clean,
                    active_ingredient=confirmed_active_ingredient,
                    strength=strength,
                    category=category,
                    is_supplement=is_supplement,
                    confidence_score=0.95,
                    verification_status=new_status,
                    hit_count=1,
                    verified_count=1,
                    notes=user_notes,
                    contraindications=[],
                    source="hitl_user_verification",
                )
                s.add(new_row)
            await s.commit()

        try:
            if session is not None:
                await _do_db_update(session)
            else:
                from app.db.session import AsyncSessionLocal
                async with AsyncSessionLocal() as s:
                    await _do_db_update(s)
            logger.info("[drug_db] Verified and updated learned drug in DB: %s (%s)", brand_raw, new_status)
        except Exception as e:
            logger.warning("[drug_db] Could not update learned drug in DB: %s", e)

        return updated_data

    def find_by_ingredient(self, ingredient: str) -> list[dict[str, Any]]:
        """Tìm tất cả thuốc chứa hoạt chất cụ thể trong Dual-Tier."""
        if not ingredient:
            return []
        ing_clean = ingredient.lower().strip()
        res = list(self.ingredient_to_drugs.get(ing_clean, []))

        # Hợp nhất tối đa 20 thuốc từ Tier 2 (không trùng lặp tên)
        ext_matches = self.extended_ingredient_to_drugs.get(ing_clean, [])
        if ext_matches:
            seen_names = {d.get("brand_name", "").lower() for d in res}
            for d in ext_matches:
                b_low = d.get("brand_name", "").lower()
                if b_low not in seen_names:
                    res.append(d)
                    seen_names.add(b_low)
                if len(res) >= 25:
                    break
        return res

    def get_drug_info(self, drug_id: str) -> Optional[dict[str, Any]]:
        """Lấy thông tin đầy đủ theo ID thuốc (Tier 1 -> Tier 2)."""
        for drug in self.local_db:
            if drug.get("id") == drug_id:
                return drug
        for drug in self.extended_db:
            if drug.get("id") == drug_id:
                return drug
        return None

    def get_drug_variants(self, brand_or_ingredient: str) -> list[str]:
        """Lấy danh sách các biến thể hàm lượng chuẩn theo tên thương mại hoặc hoạt chất."""
        if not brand_or_ingredient:
            return []
        term = brand_or_ingredient.lower().strip()
        # 1. Tra cứu theo brand name exact / fuzzy
        drug = self.find_by_brand_exact(term) or self.find_by_brand_fuzzy(term, threshold=75)
        if drug and drug.get("common_strengths"):
            return list(drug["common_strengths"])
        if drug and drug.get("strength"):
            return [str(drug["strength"])]

        # 2. Tra cứu theo hoạt chất
        drugs_by_ing = self.find_by_ingredient(term)
        variants = []
        for d in drugs_by_ing:
            if d.get("common_strengths"):
                for s in d["common_strengths"]:
                    if s not in variants:
                        variants.append(s)
            elif d.get("strength") and d["strength"] not in variants:
                variants.append(str(d["strength"]))
        return variants

    def search_drugs(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Tìm kiếm thuốc theo từ khóa (brand name hoặc hoạt chất) trong Dual-Tier CSDL."""
        from rapidfuzz import process, fuzz

        query_lower = query.lower().strip()
        results = []
        seen_ids = set()

        # 1. Tìm kiếm trong Tier 1 (Gold Standard VN)
        brands_tier1 = list(self.brand_to_drug.keys())
        matches_tier1 = process.extract(
            query_lower,
            brands_tier1,
            scorer=fuzz.token_sort_ratio,
            limit=limit,
            score_cutoff=60,
        )
        for match_str, score, _ in matches_tier1:
            drug = self.brand_to_drug[match_str]
            if drug["id"] not in seen_ids:
                drug_copy = drug.copy()
                drug_copy["_match_score"] = score
                drug_copy["_match_type"] = "brand"
                results.append(drug_copy)
                seen_ids.add(drug["id"])

        # Tìm theo hoạt chất Tier 1
        for ing, drugs in self.ingredient_to_drugs.items():
            if query_lower in ing:
                for drug in drugs:
                    if drug["id"] not in seen_ids:
                        drug_copy = drug.copy()
                        drug_copy["_match_score"] = 100
                        drug_copy["_match_type"] = "ingredient"
                        results.append(drug_copy)
                        seen_ids.add(drug["id"])

        # 2. Nếu chưa đủ limit, tìm kiếm bổ sung trong Tier 2 (Extended Master)
        if len(results) < limit and self.extended_brand_to_drug:
            # Khớp substring nhanh cho brand name Tier 2
            for b_name, drug in self.extended_brand_to_drug.items():
                if query_lower in b_name and drug["id"] not in seen_ids:
                    drug_copy = drug.copy()
                    drug_copy["_match_score"] = 90
                    drug_copy["_match_type"] = "brand_extended"
                    results.append(drug_copy)
                    seen_ids.add(drug["id"])
                    if len(results) >= limit:
                        break

            # Khớp substring theo hoạt chất Tier 2
            if len(results) < limit:
                for ing, drugs in self.extended_ingredient_to_drugs.items():
                    if query_lower in ing:
                        for drug in drugs:
                            if drug["id"] not in seen_ids:
                                drug_copy = drug.copy()
                                drug_copy["_match_score"] = 85
                                drug_copy["_match_type"] = "ingredient_extended"
                                results.append(drug_copy)
                                seen_ids.add(drug["id"])
                                if len(results) >= limit:
                                    break
                        if len(results) >= limit:
                            break

        return sorted(results, key=lambda d: d.get("_match_score", 0), reverse=True)[:limit]

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

    @staticmethod
    def is_valid_openfda_substance_query(token: Optional[str]) -> bool:
        """Kiểm tra điều kiện an toàn trước khi gửi query substance lên OpenFDA:
        1. Độ dài >= 5 ký tự chữ cái (a-z, A-Z) có nghĩa.
        2. KHÔNG chứa dấu gạch nối '-' mà một trong các phần tách ra có độ dài <= 3 ký tự
           (chặn 'S-ALA', 'T-P', 'AB-CD', 'Vitamin-C', 'X-ray' để tránh match nhầm hóa chất/oncology).
        """
        if not token or not isinstance(token, str):
            return False

        # Lấy danh sách các ký tự chữ cái thuần túy
        alpha_chars = [c for c in token if c.isalpha()]
        if len(alpha_chars) < 5:
            return False

        # Kiểm tra các phần phân tách bởi dấu gạch nối '-'
        if "-" in token:
            parts = [p.strip() for p in token.split("-") if p.strip()]
            for p in parts:
                p_alpha = [c for c in p if c.isalpha()]
                if len(p_alpha) <= 3:
                    return False

        return True

    async def fetch_openfda_by_ingredient(self, ingredient: str) -> list[dict[str, Any]]:
        """Tra cứu OpenFDA theo hoạt chất (có OpenFDA query gating)."""
        try:
            clean_ing = ingredient.strip().lower()
            if not self.is_valid_openfda_substance_query(clean_ing):
                return []

            if clean_ing in self._openfda_ingredient_cache:
                return self._openfda_ingredient_cache[clean_ing]

            clean_ing = ingredient.strip()
            async with httpx.AsyncClient(timeout=6.0) as client:
                params = {
                    "search": f'openfda.substance_name:"{clean_ing}"',
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

        # 3b. OpenFDA by brand treated as active ingredient/substance (chỉ khi thỏa gating)
        if self.is_valid_openfda_substance_query(brand_name):
            openfda_substance = await self.fetch_openfda_by_ingredient(brand_name)
            if openfda_substance:
                res_sub = openfda_substance[0]
                res_sub["source"] = "openfda_ingredient"
                return res_sub

        # 4. OpenFDA by ingredient hint (chỉ khi thỏa gating)
        if ingredient_hint and self.is_valid_openfda_substance_query(ingredient_hint):
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