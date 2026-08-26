# Normalization Engine - Map OCR Raw Text -> Standard Drug IDs từ Drug Database
# Sử dụng rapidfuzz để fuzzy match brand name và ingredient
from __future__ import annotations

import logging
import re
from typing import Optional

from rapidfuzz import process, fuzz

from app.schemas import DrugItem
from app.services.drug_database import drug_database

logger = logging.getLogger(__name__)


def _normalize_str(value: Optional[str]) -> str:
    """Chuẩn hóa chuỗi so sánh: gỡ khoảng trắng, lowercase (dùng cho F3.7 strength match)."""
    if not value:
        return ""
    return re.sub(r"\s+", "", value.strip()).lower()


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

    async def normalize_drug_item_full(self, raw_drug: DrugItem) -> DrugItem:
        """[P2/F3.4] Chuẩn hóa 4 tầng: 3 tầng local (sync — giữ nguyên hành vi
        cho test cũ) + tầng 4 OpenFDA khi local miss toàn bộ, đúng thiết kế
        "CSDL thuốc quốc gia kết hợp tra cứu ngoài" (ARCHITECTURE.md §4.1).

        Nguồn ngoài (OpenFDA): KHÔNG BAO GIỜ tự đánh dấu is_verified=True —
        buộc Human-in-the-Loop xác nhận (AGENTS.md §B.2); confidence trần 0.6."""
        item = self.normalize_drug_item(raw_drug)  # 3 tầng local (exact/fuzzy/ingredient)

        if item.match_method is not None:
            return item  # local đã match — không tốn network call

        info = await drug_database.get_drug_full_info(item.brand_name, None)
        if not info or not str(info.get("source", "")).startswith("openfda"):
            return item  # giữ nhánh unmatched (confidence ≤ 0.4, unverified)

        # Áp dụng thông tin OpenFDA một cách bảo thủ (chỉ ghi trường có thật)
        fda_brand = info.get("brand_name")
        if fda_brand:
            item.brand_name = str(fda_brand)
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
        # OpenFDA không cung cấp nhóm điều trị theo chuẩn VN / liều tối đa VN:
        item.category = None
        item.max_daily_dosage = None
        item.match_method = str(info.get("source"))  # "openfda" | "openfda_ingredient"

        # Confidence: trung bình OCR × điểm nguồn ngoài, TRẦN CỨNG 0.6 (chưa HITL)
        external_conf = 0.5
        item.confidence_score = round(
            min(0.6, (item.confidence_score + external_conf) / 2), 4
        )
        item.is_verified = False  # BẮT BUỘC Human-in-the-Loop với nguồn ngoài
        logger.info(
            "[normalization] OpenFDA tier-4: %s -> %s (conf=%.2f)",
            item.brand_name,
            item.active_ingredient,
            item.confidence_score,
        )
        return item

    async def normalize_ocr_items_full(self, ocr_items: list[DrugItem]) -> list[DrugItem]:
        """[P2/F3.4] Wrapper async 4 tầng — endpoint /ocr/scan gọi hàm này."""
        return [await self.normalize_drug_item_full(item) for item in ocr_items]

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

        # [P2/F3.4 + P3/F3.6] Gắn match_method chính thức lên item — vừa làm
        # marker chặn tầng 4 OpenFDA, vừa fix contract field luôn null.
        raw_drug.match_method = match_method
        
        # Chuẩn hóa tên thương mại
        raw_drug.brand_name = db_drug.get("brand_name", raw_drug.brand_name)
        
        # Chuẩn hóa hoạt chất gốc
        raw_drug.active_ingredient = db_drug.get("active_ingredient", raw_drug.active_ingredient)
        
        # Chuẩn hóa hàm lượng - dùng DB nếu OCR không có hoặc match score cao
        db_strength = db_drug.get("strength")
        # [F3.7] Cảnh báo khi hàm lượng user/OCR nhập khác hẳn với DB chuẩn
        # (non-blocking hint cho Human-in-the-Loop; KHÔNG đổi logic gán strength).
        if raw_drug.strength and db_strength and _normalize_str(
            raw_drug.strength
        ) != _normalize_str(db_strength):
            raw_drug.strength_mismatch_warning = (
                f"Hàm lượng '{raw_drug.strength}' khác với hàm lượng chuẩn "
                f"cơ sở dữ liệu '{db_strength}' — vui lòng xác nhận lại với bác sĩ/dược sĹ."
            )
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
