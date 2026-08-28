"""
Fuzzy String Matching & Medical Typo Correction Module.
Uses Levenshtein distance, character-level OCR confusion matrix corrections,
and normalized similarity scoring for Vietnamese pharmaceutical brand/generic matching.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple


def normalize_vietnamese_text(text: str) -> str:
    """Loại bỏ dấu tiếng Việt và ký tự đặc biệt, chuẩn hóa về chữ thường."""
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = re.sub(r"[\u0300-\u036f]", "", text)
    text = text.replace("đ", "d").replace("Đ", "D")
    text = re.sub(r"[^\w\s\.]", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def clean_ocr_typos(text: str) -> str:
    """Tự động sửa các lỗi OCR nhầm lẫn ký tự số - chữ phổ biến trong biệt dược."""
    if not text:
        return ""
    
    cleaned = text
    # 0 -> o trong từ, 1 -> l/i, 4 -> a, 5 -> s, 8 -> b, 9 -> g
    cleaned = re.sub(r"(?<=[a-zA-Z])0(?=[a-zA-Z])", "o", cleaned)
    cleaned = re.sub(r"(?<=[a-zA-Z])1(?=[a-zA-Z])", "l", cleaned)
    cleaned = re.sub(r"(?<=[a-zA-Z])4(?=[a-zA-Z])", "a", cleaned)
    cleaned = re.sub(r"(?<=[a-zA-Z])5(?=[a-zA-Z])", "s", cleaned)
    cleaned = re.sub(r"(?<=[a-zA-Z])8(?=[a-zA-Z])", "b", cleaned)
    cleaned = re.sub(r"(?<=[a-zA-Z])9(?=[a-zA-Z])", "g", cleaned)
    
    # OCR thường nhầm 'in' thành 'ln', 'ic' thành 'lc' trong tên thuốc
    cleaned = re.sub(r"(?<=[a-zA-Z])ln\b", "in", cleaned)
    cleaned = re.sub(r"(?<=[a-zA-Z])ln(?=[a-zA-Z])", "in", cleaned)
    cleaned = re.sub(r"(?<=[a-zA-Z])lc(?=[a-zA-Z])", "ic", cleaned)
    
    cleaned = cleaned.replace("|", "l").replace("!", "i")
    return cleaned


def levenshtein_distance(s1: str, s2: str) -> int:
    """Tính khoảng cách Levenshtein chuẩn giữa 2 chuỗi."""
    if s1 == s2:
        return 0
    if len(s1) == 0:
        return len(s2)
    if len(s2) == 0:
        return len(s1)

    v0 = list(range(len(s2) + 1))
    v1 = [0] * (len(s2) + 1)

    for i in range(len(s1)):
        v1[0] = i + 1
        for j in range(len(s2)):
            cost = 0 if s1[i] == s2[j] else 1
            v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
        v0, v1 = v1, [0] * (len(s2) + 1)

    return v0[len(s2)]


def similarity_ratio(s1: str, s2: str) -> float:
    """Tính điểm tương đồng chuẩn hóa từ 0.0 đến 1.0."""
    n1 = normalize_vietnamese_text(clean_ocr_typos(s1))
    n2 = normalize_vietnamese_text(clean_ocr_typos(s2))
    
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0

    max_len = max(len(n1), len(n2))
    if max_len == 0:
        return 1.0

    dist = levenshtein_distance(n1, n2)
    ratio = 1.0 - (dist / float(max_len))
    return max(0.0, min(1.0, ratio))


class FuzzyMatcher:
    """Lớp đối sánh chuỗi mờ và tự sửa lỗi OCR cho từ điển Dược lâm sàng."""

    def __init__(self, default_threshold: float = 0.70) -> None:
        self.default_threshold = default_threshold

    def find_best_drug_match(
        self,
        query: str,
        drug_database: List[Dict[str, Any]],
        threshold: Optional[float] = None,
    ) -> Tuple[Optional[Dict[str, Any]], float, str]:
        """
        Tìm kiếm biệt dược phù hợp nhất từ danh mục thuốc.
        Trả về (drug_dict, similarity_score, match_method).
        """
        if not query or not str(query).strip():
            return None, 0.0, "none"

        thresh = threshold if threshold is not None else self.default_threshold
        norm_query = normalize_vietnamese_text(clean_ocr_typos(query))

        best_drug: Optional[Dict[str, Any]] = None
        highest_score: float = 0.0
        match_type: str = "none"

        # 1. Exact & Alias Match
        for item in drug_database:
            brand = item.get("brand_name", "")
            norm_brand = normalize_vietnamese_text(brand)

            if norm_query == norm_brand:
                return item, 1.0, "exact"

            # Check aliases
            for alias in item.get("aliases", []):
                norm_alias = normalize_vietnamese_text(alias)
                if norm_query == norm_alias:
                    return item, 1.0, "alias_exact"

                score = similarity_ratio(norm_query, norm_alias)
                if score > highest_score:
                    highest_score = score
                    best_drug = item
                    match_type = "alias_fuzzy"

            # Fuzzy with brand_name
            brand_score = similarity_ratio(norm_query, norm_brand)
            if brand_score > highest_score:
                highest_score = brand_score
                best_drug = item
                match_type = "brand_fuzzy"

        # 2. Substring & Prefix Check (Ví dụ query chứa brand hoặc ngược lại)
        if highest_score < thresh:
            for item in drug_database:
                norm_brand = normalize_vietnamese_text(item.get("brand_name", ""))
                brand_tokens = norm_brand.split()
                first_token = brand_tokens[0] if brand_tokens else ""

                if len(first_token) >= 4 and first_token in norm_query:
                    score = 0.82
                    if score > highest_score:
                        highest_score = score
                        best_drug = item
                        match_type = "token_prefix_match"

        if highest_score >= thresh and best_drug is not None:
            return best_drug, round(highest_score, 4), match_type

        return None, round(highest_score, 4), "no_match"


# Global default instance
default_fuzzy_matcher = FuzzyMatcher()
