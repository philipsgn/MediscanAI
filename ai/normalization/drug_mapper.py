"""
Drug Normalization & Brand-to-Generic Mapping Engine.
Maps OCR extracted text items to standardized master drug dictionary entities.
"""

import json
import os
import logging
from typing import Any, Dict, List, Optional, Tuple

from ai.configs.ocr_config import default_ocr_config
from ai.normalization.fuzzy_matcher import default_fuzzy_matcher, similarity_ratio

logger = logging.getLogger(__name__)


class DrugMapper:
    """Module chuẩn hóa danh mục thuốc và đối chiếu từ điển Dược Việt Nam."""

    def __init__(self, dictionary_path: Optional[str] = None) -> None:
        self.dictionary_path = dictionary_path or default_ocr_config.drug_dict_path
        self.drugs: List[Dict[str, Any]] = []
        self._load_dictionary()

    def _load_dictionary(self) -> None:
        """Đọc danh mục thuốc từ tệp JSON."""
        if not os.path.exists(self.dictionary_path):
            logger.warning(f"Drug dictionary file not found at: {self.dictionary_path}")
            self.drugs = []
            return

        try:
            with open(self.dictionary_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.drugs = data.get("drugs", [])
                logger.info(f"Loaded {len(self.drugs)} standard drugs into DrugMapper database.")
        except Exception as e:
            logger.error(f"Failed to load drug dictionary: {e}")
            self.drugs = []

    def map_raw_text(
        self,
        raw_text: str,
        threshold: float = 0.70,
    ) -> Dict[str, Any]:
        """
        Đối chiếu chuỗi văn bản thô từ OCR và trả về thông tin thuốc chuẩn hóa.
        """
        matched_drug, score, match_type = default_fuzzy_matcher.find_best_drug_match(
            raw_text, self.drugs, threshold=threshold
        )

        if matched_drug:
            return {
                "matched": True,
                "drug_id": matched_drug.get("id"),
                "brand_name": matched_drug.get("brand_name"),
                "active_ingredient": matched_drug.get("active_ingredient"),
                "strength": matched_drug.get("strength"),
                "dosage_form": matched_drug.get("dosage_form"),
                "default_route": matched_drug.get("default_route"),
                "max_daily_dose_mg": matched_drug.get("max_daily_dose_mg"),
                "category": matched_drug.get("category"),
                "confidence_score": score,
                "match_method": match_type,
            }

        return {
            "matched": False,
            "drug_id": None,
            "brand_name": raw_text.strip(),
            "active_ingredient": None,
            "strength": None,
            "dosage_form": None,
            "default_route": "Uống",
            "max_daily_dose_mg": None,
            "category": None,
            "confidence_score": 0.50,
            "match_method": "raw_fallback",
        }


# Global default mapper
default_drug_mapper = DrugMapper()
