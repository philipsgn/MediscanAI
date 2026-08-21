# Normalization Engine - Map OCR Raw Text -> Standard Drug IDs từ Drug Database
# Sử dụng rapidfuzz để fuzzy match brand name và ingredient
from __future__ import annotations

import re
from typing import Optional

from rapidfuzz import process, fuzz

from app.schemas import DrugItem
from app.services.drug_database import drug_database


class NormalizationService:
    def __init__(self) -> None:
        pass

    def normalize_ocr_items(self, ocr_items: list[DrugItem]) -> list[DrugItem]:
        """
        Chuẩn hóa danh sách DrugItem từ OCR thô.
        Mỗi item: tìm trong Drug DB bằng brand name + ingredient hint.
        """
        normalized = []
        for raw_drug in ocr_items:
            normalized.append(self.normalize_drug_item(raw_drug))
        return normalized

    def normalize_drug_item(self, raw_drug: DrugItem) -> DrugItem:
        """
        Chuẩn hóa một DrugItem: map với Drug Database.
        Trả về DrugItem đã cập nhật: active_ingredient, strength chuẩn, drug_id, warnings, etc.
        """
        brand_raw = (raw_drug.brand_name or "").strip()
        ingredient_hint = None
        if raw_drug.active_ingredient:
            # Lấy hoạt chất đầu tiên làm hint
            ingredient_hint = raw_drug.active_ingredient.split("/")[0].strip()

        # Tìm trong local DB (exact -> fuzzy)
        matched = drug_database.find_by_brand_exact(brand_raw)
        match_method = "exact"
        match_score = 100

        if not matched:
            matched = drug_database.find_by_brand_fuzzy(brand_raw, threshold=65)
            match_method = "fuzzy"
            # Extract score từ fuzzy match
            if matched:
                # Re-compute score for logging
                best = process.extractOne(
                    brand_raw.lower(),
                    list(drug_database.brand_to_drug.keys()),
                    scorer=fuzz.token_sort_ratio,
                )
                if best:
                    match_score = best[1]

        if matched:
            # Cập nhật thông tin từ DB chuẩn
            return self._apply_db_info(raw_drug, matched, match_score, match_method)
        elif ingredient_hint:
            # Fallback: tìm theo hoạt chất
            by_ing = drug_database.find_by_ingredient(ingredient_hint)
            if by_ing:
                # Lấy thuốc đầu tiên có ingredient match
                return self._apply_db_info(raw_drug, by_ing[0], 50, "ingredient_fallback")

        # Không match được - giữ nguyên, đánh dấu unverified
        raw_drug.is_verified = False
        raw_drug.confidence_score = min(raw_drug.confidence_score, 0.4)
        return raw_drug

    def _apply_db_info(self, raw_drug: DrugItem, db_drug: dict, match_score: int, match_method: str) -> DrugItem:
        """Áp dụng thông tin từ Drug DB vào DrugItem."""
        # Gán drug_id từ DB
        raw_drug.drug_id = db_drug.get("id")
        
        # Chuẩn hóa tên thương mại
        raw_drug.brand_name = db_drug.get("brand_name", raw_drug.brand_name)
        
        # Chuẩn hóa hoạt chất gốc
        raw_drug.active_ingredient = db_drug.get("active_ingredient", raw_drug.active_ingredient)
        
        # Chuẩn hóa hàm lượng - dùng DB nếu OCR không có hoặc match score cao
        db_strength = db_drug.get("strength")
        if db_strength and (not raw_drug.strength or match_score > 85):
            raw_drug.strength = db_strength
        
        # Thêm thông tin mở rộng từ DB
        raw_drug.category = db_drug.get("category")
        raw_drug.max_daily_dosage = db_drug.get("max_daily_dosage")
        raw_drug.warnings = db_drug.get("warnings_contraindications", [])
        
        # Tính lại confidence: trung bình giữa OCR confidence và fuzzy match score
        fuzzy_conf = match_score / 100.0
        raw_drug.confidence_score = round((raw_drug.confidence_score + fuzzy_conf) / 2, 4)
        
        # Xác định verified
        if match_method == "exact" and raw_drug.confidence_score > 0.8:
            raw_drug.is_verified = True
        elif match_method == "fuzzy" and match_score > 85 and raw_drug.confidence_score > 0.75:
            raw_drug.is_verified = True
        else:
            raw_drug.is_verified = False
        
        return raw_drug


# Backward compatibility
def normalize_drug_item(raw_drug: DrugItem) -> DrugItem:
    return NormalizationService().normalize_drug_item(raw_drug)


normalization_service = NormalizationService()
