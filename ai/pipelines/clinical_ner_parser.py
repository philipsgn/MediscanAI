"""
Clinical Named Entity Recognition (NER) & Heuristic Parser.
Extracts Drug Strength, Dosage Forms, Intake Schedules (Time Slots),
Duration, and Directions from raw Vietnamese prescription and packaging texts.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from ai.configs.ocr_config import default_ocr_config


DOSAGE_FORMS = [
    "viên nén bao phim", "viên nén", "viên nang", "viên sủi", "viên đặt", "viên nhai",
    "viên bao đường", "viên ngậm", "viên", "gói", "chai", "lọ", "ống", "tuýp",
    "hỗn dịch", "siro", "dung dịch", "bột pha", "thuốc mỡ", "kem bôi"
]

STRENGTH_REGEX = re.compile(
    r"(?i)\b(\d+(?:[.,]\d+)?\s*(?:mg|g|mcg|ml|iu|ui|%)(?:\s*/\s*\d*(?:[.,]\d+)?\s*(?:mg|g|mcg|ml|iu|ui)?)?)\b"
)

DURATION_REGEX = re.compile(
    r"(?i)(?:uống|dùng|trong|đợt|liệu\s*trình|x)?(?:\s*điều\s*trị)?\s*(\d{1,3})\s*(?:ngày|ngay|day|days)\b"
)

QUANTITY_REGEX = re.compile(
    r"(?i)(?:số lượng|sl|qty|x)\s*:?\s*(\d{1,3})\s*(?:viên|gói|chai|lọ|ống|tuýp|v|tab|tabs)?\b"
)


class ClinicalNERParser:
    """Module bóc tách thực thể y khoa chuyên sâu từ văn bản toa thuốc và vỏ hộp."""

    def __init__(self, default_slot_times: Optional[Dict[str, str]] = None) -> None:
        self.default_slot_times = default_slot_times or default_ocr_config.default_slot_times

    def extract_strength(self, text: str) -> Optional[str]:
        """Trích xuất hàm lượng thuốc (VD: 500mg, 1g, 1000mg/62.5mg, 10ml, hoặc suy luận từ Oricox120)."""
        if not text:
            return None
        match = STRENGTH_REGEX.search(text)
        if match:
            return match.group(1).strip()
        # Heuristic cho dạng <TênChữ><Số> (Oricox120 -> 120mg)
        m = re.search(r"\b([a-zA-ZÀ-ỹ]{2,})[\s\-_]*(\d{1,4}(?:[\.,]\d+)?)\b", text)
        if m:
            prefix = m.group(1).lower()
            if prefix not in {"vitamin", "lan", "ngay", "gio", "vien", "tab", "tabs", "sl", "qty"}:
                return f"{m.group(2).strip()}mg"
        return None

    def extract_dosage_form(self, text: str) -> Optional[str]:
        """Trích xuất dạng bào chế của thuốc."""
        if not text:
            return None
        lower = text.lower()
        for form in DOSAGE_FORMS:
            if form in lower:
                return form.capitalize()
        return None

    def extract_duration_days(self, text: str) -> Optional[int]:
        """Trích xuất số ngày dùng thuốc trong đợt điều trị."""
        if not text:
            return None
        match = DURATION_REGEX.search(text)
        if match:
            try:
                days = int(match.group(1))
                if 1 <= days <= 365:
                    return days
            except ValueError:
                pass
        return None

    def extract_time_slots(self, text: str) -> Tuple[List[str], Dict[str, str], bool]:
        """
        Bóc tách các buổi uống trong ngày và khung giờ khuyến nghị.
        Trả về (time_slots, slot_times, is_time_extracted).
        """
        if not text:
            return [], {}, False

        lower = text.lower()
        slots: List[str] = []
        times: Dict[str, str] = {}

        # 1. Nhận diện các buổi cụ thể
        has_morning = bool(re.search(r"(?i)\b(sáng|sang|morning|am)\b", lower))
        has_noon = bool(re.search(r"(?i)\b(trưa|trua|noon)\b", lower))
        has_afternoon = bool(re.search(r"(?i)\b(chiều|chieu|afternoon|pm)\b", lower))
        has_evening = bool(re.search(r"(?i)\b(tối|toi|đêm|dem|evening|night|ngủ|ngu)\b", lower))

        if has_morning:
            slots.append("morning")
            times["morning"] = self.default_slot_times.get("morning", "08:00")
        if has_noon:
            slots.append("noon")
            times["noon"] = self.default_slot_times.get("noon", "12:00")
        if has_afternoon:
            slots.append("afternoon")
            times["afternoon"] = self.default_slot_times.get("afternoon", "17:00")
        if has_evening:
            slots.append("evening")
            times["evening"] = self.default_slot_times.get("evening", "21:00")

        # 2. Nhận diện tần suất tổng quát (VD: "ngày 2 lần", "ngày 3 lần")
        if not slots:
            if re.search(r"(?i)\b(?:ngày|ngay)\s*(?:uống|dung|dùng)?\s*3\s*lần\b", lower) or "3 lần/ngày" in lower:
                slots = ["morning", "noon", "evening"]
                for s in slots:
                    times[s] = self.default_slot_times.get(s, "08:00")
            elif re.search(r"(?i)\b(?:ngày|ngay)\s*(?:uống|dung|dùng)?\s*2\s*lần\b", lower) or "2 lần/ngày" in lower:
                slots = ["morning", "evening"]
                for s in slots:
                    times[s] = self.default_slot_times.get(s, "08:00")
            elif re.search(r"(?i)\b(?:ngày|ngay)\s*(?:uống|dung|dùng)?\s*1\s*lần\b", lower) or "1 lần/ngày" in lower:
                slots = ["morning"]
                times["morning"] = self.default_slot_times.get("morning", "08:00")

        is_extracted = len(slots) > 0
        return slots, times, is_extracted

    def parse_instruction_and_dosage(self, full_text: str) -> Dict[str, Any]:
        """
        Phân tích tổng hợp toàn bộ các trường lâm sàng từ chuỗi văn bản.
        """
        strength = self.extract_strength(full_text)
        dosage_form = self.extract_dosage_form(full_text)
        duration_days = self.extract_duration_days(full_text)
        slots, times, is_time_extracted = self.extract_time_slots(full_text)

        # Hướng dẫn liều dùng tóm tắt
        clean_text = re.sub(r"\s+", " ", full_text).strip()

        return {
            "strength": strength,
            "dosage_form": dosage_form,
            "duration_days": duration_days or 7,
            "time_slots": slots,
            "slot_times": times,
            "is_time_extracted": is_time_extracted,
            "raw_instruction": clean_text,
        }


# Global default instance
default_ner_parser = ClinicalNERParser()
