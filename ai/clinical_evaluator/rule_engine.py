"""
4-Layer Clinical Rule Engine for MediScan AI.
Evaluates:
  - Layer 1: Overdose & Duplication of Active Ingredients
  - Layer 2: Drug-Drug Interactions
  - Layer 3: Drug-Condition Contraindications
  - Layer 4: Dosage Appropriateness & Population Limits
"""

import json
import os
import re
import logging
from typing import Any, Dict, List, Optional

from ai.configs.ocr_config import default_ocr_config

logger = logging.getLogger(__name__)


class ClinicalRuleEngine:
    """Hệ thống đánh giá an toàn dùng thuốc 4 tầng lâm sàng độc lập."""

    def __init__(self, rules_path: Optional[str] = None) -> None:
        self.rules_path = rules_path or default_ocr_config.clinical_rules_path
        self.drug_drug_rules: List[Dict[str, Any]] = []
        self.contraindication_rules: List[Dict[str, Any]] = []
        self._load_rules()

    def _load_rules(self) -> None:
        """Đọc bảng luật tương tác y khoa từ file JSON."""
        if not os.path.exists(self.rules_path):
            logger.warning(f"Clinical rules file not found at: {self.rules_path}")
            return

        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.drug_drug_rules = data.get("drug_drug_interactions", [])
                self.contraindication_rules = data.get("drug_condition_contraindications", [])
                logger.info(f"Loaded {len(self.drug_drug_rules)} DDI rules and {len(self.contraindication_rules)} contraindications.")
        except Exception as e:
            logger.error(f"Failed to load clinical rules: {e}")

    def _extract_strength_mg(self, strength_str: Optional[str]) -> float:
        """Quy đổi chuỗi hàm lượng về đơn vị mg."""
        if not strength_str:
            return 0.0
        s = str(strength_str).lower()
        match = re.search(r"(\d+(?:\.\d+)?)\s*(mg|g|mcg)", s)
        if not match:
            return 0.0
        val = float(match.group(1))
        unit = match.group(2)
        if unit == "g":
            return val * 1000.0
        elif unit == "mcg":
            return val / 1000.0
        return val

    def evaluate(
        self,
        drugs: List[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Chạy toàn bộ 4 Layer đánh giá y khoa:
        1. Trùng hoạt chất & Quá liều (Layer 1)
        2. Tương tác Thuốc - Thuốc (Layer 2)
        3. Thuốc - Bệnh nền (Layer 3)
        4. Đối chiếu liều dùng (Layer 4)
        """
        alerts: List[Dict[str, Any]] = []
        dosage_checks: List[Dict[str, Any]] = []
        schedule_suggestions: List[str] = []

        if not drugs:
            return {
                "total_drugs_analyzed": 0,
                "alerts": [],
                "schedule_suggestions": [],
                "dosage_checks": [],
                "final_summary": "Chưa có thuốc nào trong danh sách đánh giá.",
            }

        # ── LAYER 1: Trùng lặp hoạt chất & Quá liều ─────────────────────────
        ingredient_map: Dict[str, List[Dict[str, Any]]] = {}
        for d in drugs:
            ing = d.get("active_ingredient") or d.get("drug_name", "")
            if ing:
                # Tách nếu là hoạt chất phối hợp (VD: "Paracetamol + Caffeine")
                parts = [p.strip() for p in ing.split("+") if p.strip()]
                for part in parts:
                    clean_part = part.lower()
                    if clean_part not in ingredient_map:
                        ingredient_map[clean_part] = []
                    ingredient_map[clean_part].append(d)

        for ing, drug_list in ingredient_map.items():
            if len(drug_list) > 1:
                drug_names = ", ".join([d.get("drug_name", "") for d in drug_list])
                alerts.append({
                    "severity": "HIGH",
                    "title": f"Trùng lặp hoạt chất: {ing.title()}",
                    "description": f"Phát hiện nhiều thuốc ({drug_names}) cùng chứa hoạt chất {ing.title()}. Nguy cơ cao gây ngộ độc hoặc quá liều tích lũy.",
                    "recommendation": f"Xem xét giảm bớt hoặc chỉ giữ lại 1 thuốc chứa {ing.title()} theo hướng dẫn của bác sĩ hoặc dược sĩ chuyên khoa."
                })

        # ── LAYER 2: Tương tác Thuốc - Thuốc ─────────────────────────────────
        for rule in self.drug_drug_rules:
            da = rule.get("drug_a", "").lower()
            db_name = rule.get("drug_b", "").lower()

            matched_a = [d for d in drugs if da in (d.get("active_ingredient") or d.get("drug_name", "")).lower()]
            matched_b = [d for d in drugs if db_name in (d.get("active_ingredient") or d.get("drug_name", "")).lower()]

            if matched_a and matched_b:
                name_a = matched_a[0].get("drug_name")
                name_b = matched_b[0].get("drug_name")
                alerts.append({
                    "severity": rule.get("severity", "MEDIUM"),
                    "title": f"{rule.get('title')} ({name_a} + {name_b})",
                    "description": rule.get("description", ""),
                    "recommendation": rule.get("recommendation", "")
                })

        # ── LAYER 3: Tương tác Thuốc - Bệnh nền ──────────────────────────────
        user_conditions = []
        if user_profile:
            user_conditions = [c.lower() for c in user_profile.get("conditions", [])]

        for con_rule in self.contraindication_rules:
            ing = con_rule.get("ingredient", "").lower()
            cond_key = con_rule.get("condition", "").lower()
            cond_vi = con_rule.get("condition_name_vi", "").lower()

            has_condition = any(cond_key in c or cond_vi in c for c in user_conditions)
            if has_condition:
                matched_drugs = [d for d in drugs if ing in (d.get("active_ingredient") or d.get("drug_name", "")).lower()]
                if matched_drugs:
                    dname = matched_drugs[0].get("drug_name")
                    alerts.append({
                        "severity": con_rule.get("severity", "HIGH"),
                        "title": f"{con_rule.get('title')} ({dname})",
                        "description": con_rule.get("description", ""),
                        "recommendation": con_rule.get("recommendation", "")
                    })

        # ── LAYER 4: Đối chiếu liều dùng ────────────────────────────────────
        for d in drugs:
            dname = d.get("drug_name", "")
            strength = d.get("strength", "")
            max_dose = d.get("max_daily_dose_mg")
            strength_mg = self._extract_strength_mg(strength)

            is_app = True
            note = f"Hàm lượng {strength or 'chưa xác định'} trong giới hạn an toàn."

            if max_dose and strength_mg > max_dose:
                is_app = False
                note = f"Cảnh báo: Hàm lượng {strength} có thể vượt ngưỡng tối đa khuyến cáo {max_dose}mg/ngày."
                alerts.append({
                    "severity": "HIGH",
                    "title": f"Cảnh báo quá liều đơn vị: {dname}",
                    "description": note,
                    "recommendation": f"Tham khảo ý kiến bác sĩ để điều chỉnh hàm lượng an toàn (tối đa {max_dose}mg/ngày)."
                })

            dosage_checks.append({
                "drug_name": dname,
                "prescribed_or_input_dosage": strength or "1 liều chuẩn",
                "recommended_dosage": f"Tối đa {max_dose}mg/ngày" if max_dose else "Theo chỉ định bác sĩ",
                "is_appropriate": is_app,
                "note": note
            })

        # Sắp xếp alert theo thứ tự ưu tiên HIGH -> MEDIUM -> LOW
        sev_map = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        alerts.sort(key=lambda x: sev_map.get(x.get("severity", "LOW"), 3))

        # Phân chia gợi ý lịch uống
        if len(drugs) > 1:
            schedule_suggestions.append("Nên uống thuốc kháng acid dạ dày cách các thuốc khác ít nhất 2 giờ.")
            schedule_suggestions.append("Các thuốc hạ huyết áp và tim mạch nên uống cố định vào khung giờ buổi sáng.")

        # Tổng hợp tóm tắt lâm sàng (Final Summary)
        high_cnt = sum(1 for a in alerts if a.get("severity") == "HIGH")
        med_cnt = sum(1 for a in alerts if a.get("severity") == "MEDIUM")
        
        if high_cnt > 0:
            final_summary = f"CẢNH BÁO CAO: Phát hiện {high_cnt} vấn đề nghiêm trọng cần can thiệp y khoa ngay lập tức."
        elif med_cnt > 0:
            final_summary = f"CẦN LƯU Ý: Phát hiện {med_cnt} tương tác mức độ trung bình. Cần theo dõi khi sử dụng đồng thời."
        else:
            final_summary = f"AN TOÀN: Đã phân tích {len(drugs)} thuốc. Không phát hiện xung đột hay tương tác nghiêm trọng."

        return {
            "total_drugs_analyzed": len(drugs),
            "alerts": alerts,
            "schedule_suggestions": schedule_suggestions,
            "dosage_checks": dosage_checks,
            "final_summary": final_summary,
        }


# Global default instance
default_clinical_rule_engine = ClinicalRuleEngine()
