# Normalization Engine - Map OCR Raw Text -> Standard Drug IDs từ Drug Database & RxNorm/OpenFDA
# Tuân thủ kiến trúc phân tầng an toàn (Stage 11/12):
# Tier 1: Local Verified Vietnam Drug DB (Exact/Ingredient/Fuzzy) -> RESOLVED
# Tier 2: RxNorm/RxNav (Primary Normalization Authority) -> RESOLVED / CANDIDATE_REQUIRES_REVIEW
# Tier 3: OpenFDA (Secondary Supporting Evidence) -> CANDIDATE_REQUIRES_REVIEW (HITL Required)
# Tier 4: Unmatched -> UNRESOLVED (Safety Boundary: Không đoán mò)
from __future__ import annotations

import logging
import re
from typing import Optional

from rapidfuzz import process, fuzz

from app.core.config import settings
from app.schemas import DrugItem
from app.services.drug_database import drug_database
from app.services.llm_drug_resolver import llm_drug_resolver
from app.services.rxnorm_service import NormalizationStatus, rxnorm_service

logger = logging.getLogger(__name__)


TRAILING_STRENGTH_NUM_REGEX = re.compile(
    r"^([a-zA-ZÀ-ỹ\s]+?)[\s\-_]*(\d{1,4}(?:[\.,]\d+)?)$",
    re.UNICODE,
)
VITAMIN_EXCLUDE_PATTERN = re.compile(r"^(?:vitamin\s*)?[a-zA-Z]\d{1,2}$", re.IGNORECASE)


def _normalize_str(value: Optional[str]) -> str:
    """Chuẩn hóa chuỗi so sánh: gỡ khoảng trắng, lowercase."""
    if not value:
        return ""
    return re.sub(r"\s+", "", value.strip()).lower()


class NormalizationService:
    def __init__(self) -> None:
        pass

    def normalize_ocr_items(self, ocr_items: list[DrugItem]) -> list[DrugItem]:
        """
        Chuẩn hóa danh sách DrugItem từ OCR thô (Sync Fast Path).
        Mỗi item: tìm trong Drug DB bằng brand name + ingredient hint.
        """
        normalized = []
        for raw_drug in ocr_items:
            normalized.append(self.normalize_drug_item(raw_drug))
        return normalized


    async def normalize_drug_item_full(self, raw_drug: DrugItem) -> DrugItem:
        """
        [Stage 11/12/17] Chuẩn hóa phân tầng có thẩm quyền (Authority-Driven Normalization):
        1. Local Dual-Tier & Learned DB (Sync O(1)) -> 2. RxNorm/RxNav (Primary) -> 3. OpenFDA (Supporting) -> 4. LLM Fallback (Stage 17) -> 5. Unresolved.
        """
        # 1. TẦNG 1: Local Verified DB (Exact / Ingredient / Fuzzy / Learned Cache)
        item = self.normalize_drug_item(raw_drug)
        if item.match_method is not None:
            return item  # Local verified match -> Không cần network call

        # 2. TẦNG 2: RxNorm / RxNav (Primary Normalization Authority)
        clean_brand = item.brand_name.strip() if item.brand_name else ""
        rx_candidate_item = None
        if clean_brand and drug_database.is_valid_openfda_substance_query(clean_brand):
            rx_result = await rxnorm_service.resolve_drug(clean_brand)
            if rx_result.status == NormalizationStatus.RESOLVED and rx_result.concept:
                concept = rx_result.concept
                item.drug_id = f"rxnorm:{concept.rxcui}"
                item.active_ingredient = concept.active_ingredient or concept.name
                item.match_method = "rxnorm"
                item.confidence_score = round(max(item.confidence_score, concept.confidence_score), 4)
                item.is_verified = True
                logger.info(
                    "[normalization] RxNorm Primary RESOLVED: %s -> %s (RxCUI=%s, conf=%.2f)",
                    item.brand_name,
                    item.active_ingredient,
                    concept.rxcui,
                    item.confidence_score,
                )
                return item
            elif rx_result.status == NormalizationStatus.CANDIDATE_REQUIRES_REVIEW and rx_result.candidates:
                # Ghi nhận candidate từ RxNav nhưng KHÔNG return sớm, tiếp tục thử OpenFDA & LLM
                rx_candidate_item = item.model_copy()
                rx_candidate_item.drug_id = f"rxnorm_cand:{rx_result.candidates[0].rxcui}"
                rx_candidate_item.match_method = "rxnorm_approximate"
                rx_candidate_item.confidence_score = 0.6
                rx_candidate_item.is_verified = False
                logger.info(
                    "[normalization] RxNorm CANDIDATE_REQUIRES_REVIEW: %s -> %d candidates (continuing to Tier 3/4)",
                    item.brand_name,
                    len(rx_result.candidates),
                )

        # 3. TẦNG 3: OpenFDA (Secondary Supporting Evidence)
        query_name = item.brand_name
        if item.strength:
            query_name = re.sub(re.escape(item.strength), "", query_name, flags=re.IGNORECASE).strip()
        query_name = re.sub(r"[\d\.\%\/\s\w\/]*$", "", query_name).strip() if not query_name else query_name
        clean_query = re.sub(r"[^\w\s\-]", " ", item.brand_name).split()[0] if " " in item.brand_name and not query_name else (query_name or item.brand_name)

        info = await drug_database.get_drug_full_info(clean_query, None)
        if not info:
            info = await drug_database.get_drug_full_info(item.brand_name, None)

        if info and str(info.get("source", "")).startswith("openfda"):
            fda_ingredient = info.get("active_ingredient")
            if fda_ingredient:
                if isinstance(fda_ingredient, list):
                    joined = ", ".join(str(x) for x in fda_ingredient if x)
                else:
                    joined = str(fda_ingredient)
                if joined:
                    item.active_ingredient = joined
            if info.get("strength"):
                item.strength = str(info["strength"])
            fda_warnings = info.get("warnings") or []
            if fda_warnings:
                item.warnings = [str(w) for w in fda_warnings]
            spl_id = info.get("spl_id")
            if spl_id:
                item.drug_id = f"openfda:{spl_id}"

            item.category = None
            item.max_daily_dosage = None
            item.match_method = str(info.get("source"))
            external_conf = 0.5
            item.confidence_score = round(min(0.6, (item.confidence_score + external_conf) / 2), 4)
            item.is_verified = False
            logger.info(
                "[normalization] OpenFDA tier-3 supporting evidence: %s -> %s (conf=%.2f)",
                item.brand_name,
                item.active_ingredient,
                item.confidence_score,
            )
            return item

        # 4. TẦNG 4: LLM Medical Knowledge Fallback (Stage 17)
        # Kích hoạt khi Tầng 1, 2, 2.5 và Tầng 3 đều MISS đối với các thuốc lạ hoặc Thực phẩm chức năng
        if clean_brand and settings.ENABLE_LLM_DRUG_RESOLVER:
            try:
                from app.services.ai_telemetry_service import ai_telemetry_service
                ai_telemetry_service.record_cache_miss(clean_brand)
            except Exception:
                pass

            llm_res = await llm_drug_resolver.resolve_drug_with_llm(clean_brand)
            if llm_res and llm_res.get("active_ingredient"):
                item.active_ingredient = llm_res["active_ingredient"]
                if llm_res.get("category"):
                    item.category = llm_res["category"]
                if llm_res.get("strength") and not item.strength:
                    item.strength = str(llm_res["strength"])
                item.is_supplement = bool(llm_res.get("is_supplement", False))
                item.notes = llm_res.get("notes")
                if llm_res.get("contraindications"):
                    item.warnings = [str(c) for c in llm_res["contraindications"]]
                item.match_method = "ai_llm_inference"
                item.confidence_score = min(0.75, float(llm_res.get("confidence_score", 0.75)))
                item.is_verified = False

                learned_data = {
                    "brand_name": clean_brand,
                    "active_ingredient": item.active_ingredient,
                    "strength": item.strength,
                    "category": item.category,
                    "is_supplement": item.is_supplement,
                    "confidence_score": item.confidence_score,
                    "verification_status": "PENDING_REVIEW",
                    "hit_count": 1,
                    "verified_count": 0,
                    "notes": item.notes,
                    "warnings": item.warnings,
                    "source": "ai_llm_knowledge",
                }
                drug_database.save_learned_drug(learned_data)
                try:
                    await drug_database.sync_learned_to_db(learned_data)
                except Exception:
                    pass

                logger.info(
                    "[normalization] Tier-4 LLM Fallback RESOLVED: %s -> %s (is_supplement=%s, conf=%.2f)",
                    item.brand_name,
                    item.active_ingredient,
                    item.is_supplement,
                    item.confidence_score,
                )
                return item

        # 5. TẦNG 5: UNRESOLVED / CANDIDATE_REQUIRES_REVIEW (Safety Boundary)
        return rx_candidate_item or item

    async def normalize_ocr_items_full(self, ocr_items: list[DrugItem]) -> list[DrugItem]:
        """Wrapper async chạy song song toàn bộ items qua pipeline chuẩn hóa phân tầng."""
        if not ocr_items:
            return []
        import asyncio
        results = await asyncio.gather(*(self.normalize_drug_item_full(item) for item in ocr_items))
        return list(results)

    def normalize_drug_item(self, raw_drug: DrugItem) -> DrugItem:
        """
        Chuẩn hóa một DrugItem: map với Drug Database nội bộ.
        Trả về DrugItem đã cập nhật: active_ingredient, strength chuẩn, drug_id, warnings, etc.
        """
        brand_raw = (raw_drug.brand_name or "").strip()
        ingredient_hint = None
        if raw_drug.active_ingredient:
            ingredient_hint = raw_drug.active_ingredient.split("/")[0].strip()

        # 1. Tìm chính xác theo tên thương mại (Exact Brand Match)
        matched = drug_database.find_by_brand_exact(brand_raw)
        match_method = "exact"
        match_score = 100

        # 1b. Thử tìm với brand + strength (VD: 'Oricox' + '120mg' -> 'Oricox 120mg')
        if not matched and raw_drug.strength:
            matched = drug_database.find_by_brand_exact(f"{brand_raw} {raw_drug.strength}")
            if matched:
                match_method = "exact"

        # 1c. Bóc tách tiền xử lý <TênChữ><Số> (VD: Oricox120 -> brand: 'Oricox', strength: '120mg')
        if not matched and not VITAMIN_EXCLUDE_PATTERN.match(brand_raw):
            m = TRAILING_STRENGTH_NUM_REGEX.match(brand_raw)
            if m:
                inferred_brand = m.group(1).strip(" -_")
                inferred_strength = f"{m.group(2).strip()}mg"
                if len(inferred_brand) >= 2:
                    matched = (
                        drug_database.find_by_brand_exact(inferred_brand)
                        or drug_database.find_by_brand_exact(f"{inferred_brand} {inferred_strength}")
                    )
                    if matched:
                        raw_drug.brand_name = inferred_brand
                        if not raw_drug.strength:
                            raw_drug.strength = inferred_strength
                        match_method = "exact"

        # 2. Kiểm tra nếu brand_raw là tên hoạt chất gốc (Generic/Active Ingredient Matching)
        if not matched:
            name_only = re.sub(r"\d+(?:[\.,]\d+)?\s*(?:mg|g|ml|mcg|iu|%|\/)", "", brand_raw, flags=re.IGNORECASE).strip()
            ings = list(drug_database.ingredient_to_drugs.keys())
            best_ing = process.extractOne(name_only.lower(), ings, scorer=fuzz.token_sort_ratio)
            if best_ing and best_ing[1] >= 80:
                drugs_for_ing = drug_database.find_by_ingredient(best_ing[0])
                if drugs_for_ing:
                    chosen_drug = drugs_for_ing[0]
                    for cand in drugs_for_ing:
                        if cand.get("active_ingredient", "").lower() == best_ing[0].lower():
                            chosen_drug = cand
                            break
                    matched = chosen_drug
                    match_method = "ingredient"
                    match_score = int(best_ing[1])

        # 3. Tìm gần đúng theo tên thương mại (Fuzzy Brand Match)
        if not matched:
            matched = drug_database.find_by_brand_fuzzy(brand_raw, threshold=65)
            match_method = "fuzzy"
            if matched:
                best = process.extractOne(
                    brand_raw.lower(),
                    list(drug_database.brand_to_drug.keys()),
                    scorer=fuzz.token_sort_ratio,
                )
                if best:
                    match_score = best[1]

        if matched:
            return self._apply_db_info(raw_drug, matched, match_score, match_method)
        elif ingredient_hint:
            by_ing = drug_database.find_by_ingredient(ingredient_hint)
            if by_ing:
                return self._apply_db_info(raw_drug, by_ing[0], 50, "ingredient_fallback")

        # Không match được - giữ nguyên, đánh dấu unverified
        raw_drug.is_verified = False
        raw_drug.confidence_score = min(raw_drug.confidence_score, 0.4)
        return raw_drug

    def _apply_db_info(self, raw_drug: DrugItem, db_drug: dict, match_score: int, match_method: str) -> DrugItem:
        """Áp dụng thông tin từ Drug DB vào DrugItem."""
        raw_drug.drug_id = db_drug.get("id")
        raw_drug.match_method = match_method

        if match_method in ("exact", "fuzzy"):
            raw_drug.brand_name = db_drug.get("brand_name", raw_drug.brand_name)

        raw_drug.active_ingredient = db_drug.get("active_ingredient", raw_drug.active_ingredient)

        db_strength = db_drug.get("strength")
        # Gán danh sách biến thể hàm lượng chuẩn
        if db_drug.get("common_strengths"):
            raw_drug.variants = list(db_drug["common_strengths"])
        elif db_strength:
            raw_drug.variants = [str(db_strength)]

        if match_method in ("exact", "fuzzy"):
            if raw_drug.strength and db_strength and _normalize_str(
                raw_drug.strength
            ) != _normalize_str(db_strength):
                raw_drug.strength_mismatch_warning = (
                    f"Hàm lượng '{raw_drug.strength}' khác với hàm lượng chuẩn "
                    f"cơ sở dữ liệu '{db_strength}' — vui lòng xác nhận lại với bác sĩ/dược sĩ."
                )
            if not raw_drug.strength:
                # An toàn y tế: Chỉ tự động điền nếu thuốc chỉ có duy nhất 1 quy cách trên thị trường
                if db_drug.get("is_unique_strength", False) and db_strength:
                    raw_drug.strength = db_strength
                else:
                    raw_drug.strength = ""
            elif match_score > 85 and db_strength:
                raw_drug.strength = db_strength
        elif not raw_drug.strength:
            if db_drug.get("is_unique_strength", False) and db_strength:
                raw_drug.strength = db_strength
            else:
                raw_drug.strength = ""

        raw_drug.category = db_drug.get("category")
        raw_drug.max_daily_dosage = db_drug.get("max_daily_dosage")
        raw_drug.warnings = db_drug.get("warnings_contraindications", [])

        match_conf = match_score / 100.0
        raw_drug.confidence_score = round((raw_drug.confidence_score + match_conf) / 2, 4)

        if match_method == "exact" and raw_drug.confidence_score > 0.8:
            raw_drug.is_verified = True
        elif match_method == "fuzzy" and match_score > 85 and raw_drug.confidence_score > 0.75:
            raw_drug.is_verified = True
        else:
            raw_drug.is_verified = False

        return raw_drug


def normalize_drug_item(raw_drug: DrugItem) -> DrugItem:
    return NormalizationService().normalize_drug_item(raw_drug)


normalization_service = NormalizationService()
