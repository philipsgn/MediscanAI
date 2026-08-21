"""
Evaluation Service - Engine Đánh Giá Tương Tác Thuốc 3 Lớp
Tuân thủ kiến trúc Backend-Centralized Logic theo AGENTS.md §3.A
"""
import json
import re
from itertools import combinations
from pathlib import Path
from typing import List, Optional

from app.schemas import DrugItem, UserProfile, InteractionAlert, EvaluationResponse

# ─────────────────────────────────────────────────────────────────────────────
# Bảng Tương Tác Thuốc - Thuốc (Drug-Drug Interaction Matrix)
# Format: frozenset({ingredient_a, ingredient_b}) -> {severity, title, description, recommendation}
# ─────────────────────────────────────────────────────────────────────────────
DRUG_DRUG_INTERACTIONS: list[dict] = [
    {
        "pair": {"aspirin", "ibuprofen"},
        "severity": "HIGH",
        "title": "Chống chỉ định: Aspirin + Ibuprofen",
        "description": "Kết hợp hai NSAIDs (Aspirin và Ibuprofen) làm tăng nguy cơ xuất huyết tiêu hóa nghiêm trọng và giảm hiệu quả bảo vệ tim mạch của Aspirin liều thấp.",
        "recommendation": "KHÔNG dùng đồng thời. Tham vấn bác sĩ để lựa chọn một thuốc giảm đau phù hợp."
    },
    {
        "pair": {"aspirin", "naproxen"},
        "severity": "HIGH",
        "title": "Chống chỉ định: Aspirin + Naproxen",
        "description": "Kết hợp hai NSAIDs làm tăng nguy cơ xuất huyết tiêu hóa và giảm hiệu quả bảo vệ tim của Aspirin.",
        "recommendation": "KHÔNG dùng đồng thời. Tham vấn bác sĩ."
    },
    {
        "pair": {"warfarin", "aspirin"},
        "severity": "HIGH",
        "title": "Nguy hiểm: Warfarin + Aspirin",
        "description": "Aspirin ức chế kết tập tiểu cầu và có thể làm tăng mạnh tác dụng chống đông của Warfarin, gây nguy cơ xuất huyết đe dọa tính mạng.",
        "recommendation": "KHÔNG phối hợp trừ khi có chỉ định đặc biệt của bác sĩ tim mạch. Theo dõi INR thường xuyên."
    },
    {
        "pair": {"warfarin", "ibuprofen"},
        "severity": "HIGH",
        "title": "Nguy hiểm: Warfarin + Ibuprofen",
        "description": "NSAIDs như Ibuprofen ức chế kết tập tiểu cầu và gây tổn thương niêm mạc dạ dày, kết hợp với Warfarin gây nguy cơ xuất huyết tiêu hóa rất cao.",
        "recommendation": "Tránh phối hợp. Sử dụng Paracetamol (liều thấp) thay thế nếu cần giảm đau. Hỏi bác sĩ."
    },
    {
        "pair": {"warfarin", "paracetamol"},
        "severity": "MEDIUM",
        "title": "Thận trọng: Warfarin + Paracetamol liều cao",
        "description": "Paracetamol liều trên 2000mg/ngày có thể làm tăng tác dụng chống đông của Warfarin và tăng nguy cơ chảy máu.",
        "recommendation": "Không dùng quá 2000mg Paracetamol/ngày khi đang dùng Warfarin. Theo dõi INR chặt chẽ."
    },
    {
        "pair": {"ciprofloxacin", "calcium"},
        "severity": "MEDIUM",
        "title": "Tương tác: Ciprofloxacin + Canxi",
        "description": "Ion Canxi tạo phức với Ciprofloxacin trong đường tiêu hóa, làm giảm hấp thu kháng sinh lên đến 50-80%, giảm hiệu quả điều trị.",
        "recommendation": "Uống Ciprofloxacin cách các sản phẩm chứa Canxi (sữa, viên bổ sung) ít nhất 2 giờ."
    },
    {
        "pair": {"ciprofloxacin", "iron"},
        "severity": "MEDIUM",
        "title": "Tương tác: Ciprofloxacin + Sắt (Iron)",
        "description": "Ion Sắt tạo phức chelate với Ciprofloxacin, giảm hấp thu kháng sinh đáng kể.",
        "recommendation": "Uống Ciprofloxacin cách viên uống bổ sung Sắt ít nhất 2-4 giờ."
    },
    {
        "pair": {"amoxicillin", "methotrexate"},
        "severity": "HIGH",
        "title": "Nguy hiểm: Amoxicillin + Methotrexate",
        "description": "Amoxicillin có thể làm giảm bài tiết Methotrexate ở thận, dẫn đến tăng nồng độ Methotrexate và nguy cơ độc tính nghiêm trọng (tủy xương, gan, thận).",
        "recommendation": "Thông báo ngay cho bác sĩ nếu đang dùng Methotrexate. Theo dõi nồng độ Methotrexate trong máu."
    },
    {
        "pair": {"simvastatin", "amiodarone"},
        "severity": "HIGH",
        "title": "Nguy hiểm: Simvastatin + Amiodarone",
        "description": "Amiodarone ức chế chuyển hóa Simvastatin, làm tăng nồng độ Simvastatin trong máu, gây nguy cơ tiêu cơ vân (rhabdomyolysis) nghiêm trọng.",
        "recommendation": "Giới hạn liều Simvastatin tối đa 20mg/ngày khi dùng cùng Amiodarone. Tham khảo bác sĩ tim mạch."
    },
    {
        "pair": {"metformin", "alcohol"},
        "severity": "MEDIUM",
        "title": "Thận trọng: Metformin + Rượu/Bia",
        "description": "Rượu làm tăng nguy cơ nhiễm axit lactic (lactic acidosis) khi dùng Metformin, đặc biệt khi uống nhiều hoặc nhịn đói.",
        "recommendation": "Tránh uống rượu bia khi đang điều trị đái tháo đường bằng Metformin."
    },
    {
        "pair": {"clopidogrel", "omeprazole"},
        "severity": "MEDIUM",
        "title": "Tương tác: Clopidogrel + Omeprazole",
        "description": "Omeprazole ức chế enzyme CYP2C19, làm giảm chuyển hóa Clopidogrel thành dạng hoạt tính, giảm tác dụng chống kết tập tiểu cầu.",
        "recommendation": "Cân nhắc sử dụng Pantoprazole thay thế Omeprazole. Tham vấn bác sĩ tim mạch."
    },
    {
        "pair": {"clarithromycin", "simvastatin"},
        "severity": "HIGH",
        "title": "Chống chỉ định: Clarithromycin + Simvastatin",
        "description": "Clarithromycin ức chế mạnh CYP3A4, làm tăng nồng độ Simvastatin nhiều lần trong máu, nguy cơ cao tiêu cơ vân và tổn thương thận cấp.",
        "recommendation": "TẠM NGƯNG Simvastatin trong toàn bộ thời gian điều trị kháng sinh Clarithromycin. Thông báo cho bác sĩ."
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Bảng Thuốc - Bệnh Nền Mâu Thuẫn (Drug-Condition Conflicts)
# ─────────────────────────────────────────────────────────────────────────────
DRUG_CONDITION_CONFLICTS: list[dict] = [
    {
        "ingredients": ["pseudoephedrine", "phenylephrine"],
        "conditions": ["hypertension", "cao huyết áp", "tăng huyết áp"],
        "severity": "HIGH",
        "title": "Chống chỉ định trên bệnh nhân Cao Huyết Áp",
        "description": "Pseudoephedrine và Phenylephrine là thuốc co mạch, làm tăng huyết áp đáng kể, rất nguy hiểm cho bệnh nhân tăng huyết áp.",
        "recommendation": "KHÔNG sử dụng các thuốc thông mũi chứa Pseudoephedrine/Phenylephrine. Tham vấn bác sĩ về thuốc thay thế an toàn."
    },
    {
        "ingredients": ["ibuprofen", "naproxen", "diclofenac", "aspirin"],
        "conditions": ["peptic ulcer", "gastric ulcer", "viêm loét dạ dày", "loét dạ dày", "dạ dày"],
        "severity": "HIGH",
        "title": "Chống chỉ định NSAIDs trên bệnh nhân Loét Dạ Dày",
        "description": "NSAIDs (Ibuprofen, Naproxen, Diclofenac, Aspirin) ức chế prostaglandin bảo vệ niêm mạc dạ dày, gây loét và xuất huyết tiêu hóa nghiêm trọng trên bệnh nhân có tiền sử loét dạ dày.",
        "recommendation": "Ưu tiên sử dụng Paracetamol để giảm đau. KHÔNG dùng NSAIDs. Nếu bắt buộc phải dùng, cần kết hợp thuốc bảo vệ dạ dày (PPI) theo chỉ định bác sĩ."
    },
    {
        "ingredients": ["metformin"],
        "conditions": ["renal failure", "kidney disease", "suy thận", "suy thận mạn"],
        "severity": "HIGH",
        "title": "Chống chỉ định Metformin trên bệnh nhân Suy Thận",
        "description": "Metformin bài tiết qua thận. Suy thận làm tích lũy Metformin, tăng nguy cơ nhiễm axit lactic (lactic acidosis) nguy hiểm tính mạng.",
        "recommendation": "NGỪNG Metformin ngay. Tham vấn bác sĩ nội tiết để điều chỉnh phác đồ điều trị đái tháo đường phù hợp với chức năng thận."
    },
    {
        "ingredients": ["simvastatin", "atorvastatin", "rosuvastatin"],
        "conditions": ["liver disease", "hepatitis", "xơ gan", "viêm gan", "suy gan"],
        "severity": "HIGH",
        "title": "Chống chỉ định Statin trên bệnh nhân Bệnh Gan",
        "description": "Statin (Simvastatin, Atorvastatin...) được chuyển hóa qua gan. Bệnh gan làm tăng tích lũy thuốc, nguy cơ viêm gan do thuốc và tổn thương gan nặng thêm.",
        "recommendation": "KHÔNG dùng Statin khi có bệnh gan tiến triển. Tham vấn bác sĩ."
    },
    {
        "ingredients": ["amoxicillin", "ampicillin", "penicillin"],
        "conditions": ["penicillin allergy", "dị ứng penicillin"],
        "severity": "HIGH",
        "title": "Cảnh báo Dị Ứng: Penicillin / Amoxicillin",
        "description": "Bệnh nhân có tiền sử dị ứng Penicillin có nguy cơ cao sốc phản vệ khi dùng các kháng sinh nhóm Beta-lactam (Amoxicillin, Ampicillin).",
        "recommendation": "KHÔNG dùng kháng sinh nhóm Beta-lactam. Thông báo ngay cho bác sĩ để đổi sang nhóm kháng sinh khác."
    },
    {
        "ingredients": ["ibuprofen", "naproxen", "diclofenac"],
        "conditions": ["asthma", "hen suyễn", "hen phế quản"],
        "severity": "MEDIUM",
        "title": "Thận trọng NSAIDs trên bệnh nhân Hen Suyễn",
        "description": "Khoảng 10% bệnh nhân hen suyễn nhạy cảm với Aspirin/NSAIDs, có thể gây co thắt phế quản nghiêm trọng (hen do Aspirin).",
        "recommendation": "Theo dõi sát triệu chứng hô hấp. Ưu tiên dùng Paracetamol. Tham vấn bác sĩ trước khi dùng NSAIDs."
    },
    {
        "ingredients": ["warfarin", "apixaban", "rivaroxaban"],
        "conditions": ["pregnancy", "thai kỳ", "mang thai"],
        "severity": "HIGH",
        "title": "Chống chỉ định Thuốc Chống Đông trong Thai Kỳ",
        "description": "Thuốc chống đông máu (đặc biệt Warfarin) có thể vượt qua hàng rào nhau thai, gây dị tật thai nhi và xuất huyết ở mẹ và thai.",
        "recommendation": "KHÔNG dùng Warfarin/NOACs trong thai kỳ trừ có chỉ định đặc biệt. Tham vấn bác sĩ sản phụ khoa và tim mạch."
    },
]


def _extract_mg_value(strength_str: str) -> Optional[float]:
    """Trích xuất giá trị mg từ chuỗi hàm lượng (vd: '500mg' -> 500.0)"""
    if not strength_str:
        return None
    # Lấy số đầu tiên tìm thấy kèm đơn vị mg
    match = re.search(r'(\d+(?:\.\d+)?)\s*mg', strength_str, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _extract_max_mg(max_dose_str: str) -> Optional[float]:
    """Trích xuất giá trị mg tối đa từ chuỗi (vd: '4000mg Paracetamol' -> 4000.0)"""
    if not max_dose_str:
        return None
    match = re.search(r'(\d+(?:\.\d+)?)\s*mg', max_dose_str, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _extract_doses_per_day(instruction: Optional[str]) -> int:
    """Ước lượng số lần dùng thuốc mỗi ngày từ hướng dẫn liều."""
    if not instruction:
        return 1
    instruction_lower = instruction.lower()

    # Tìm "x N lần/ngày" hoặc "N times/day"
    match = re.search(r'x?\s*(\d+)\s*lần', instruction_lower)
    if match:
        return int(match.group(1))
    if '2 lần' in instruction_lower or 'hai lần' in instruction_lower:
        return 2
    if '3 lần' in instruction_lower or 'ba lần' in instruction_lower:
        return 3
    if '4 lần' in instruction_lower or 'bốn lần' in instruction_lower:
        return 4
    return 1


def _extract_qty_per_dose(instruction: Optional[str]) -> float:
    """Ước lượng số viên/lần dùng từ hướng dẫn liều."""
    if not instruction:
        return 1.0
    match = re.search(r'(\d+(?:\.\d+)?)\s*viên', instruction.lower())
    if match:
        return float(match.group(1))
    return 1.0


class EvaluationService:
    def __init__(self):
        self.db_path = Path(__file__).parent.parent / "data" / "vietnam_drugs_db.json"
        self.drugs_db = self._load_db()
        # Index by active_ingredient (lowercase) for fast lookup
        self.db_max_dose_index: dict[str, float] = {}
        for drug in self.drugs_db:
            ingredient_raw = drug.get("active_ingredient", "")
            max_dose_str = drug.get("max_daily_dosage", "")
            if not ingredient_raw or not max_dose_str:
                continue

            # Tách danh sách hoạt chất (vd: "Paracetamol / Caffeine" -> ["paracetamol", "caffeine"])
            ingredients = [i.strip().lower() for i in ingredient_raw.split("/")]
            max_dose_lower = max_dose_str.lower()

            for ing in ingredients:
                # Chỉ index khi chuỗi max_dose đề cập đến hoạt chất này (tránh nhầm "240mg Codeine" -> paracetamol)
                if ing not in max_dose_lower:
                    continue
                max_dose = _extract_max_mg(max_dose_str)
                if max_dose and max_dose > 0:
                    # Lấy giá trị lớn nhất (đại diện người lớn) nếu nhiều brand cùng hoạt chất
                    if ing not in self.db_max_dose_index:
                        self.db_max_dose_index[ing] = max_dose
                    else:
                        self.db_max_dose_index[ing] = max(
                            self.db_max_dose_index[ing], max_dose
                        )

    def _load_db(self) -> list[dict]:
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Lỗi tải DB: {e}")
            return []

    def evaluate_medications(
        self,
        drugs: List[DrugItem],
        user_profile: Optional[UserProfile] = None
    ) -> EvaluationResponse:
        """
        Engine Đánh Giá 3 Lớp — entry point chính.
        """
        alerts: List[InteractionAlert] = []

        # === LAYER 1: Overdose / Duplicate Active Ingredient ===
        alerts.extend(self._check_overdose(drugs))

        # === LAYER 2: Drug-Drug Interactions ===
        alerts.extend(self._check_drug_drug(drugs))

        # === LAYER 3: Drug-Condition Conflicts ===
        if user_profile:
            alerts.extend(self._check_drug_condition(drugs, user_profile))

        # Sắp xếp: HIGH trước, sau đó MEDIUM, rồi LOW
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 3))

        # Tạo schedule suggestions cơ bản
        suggestions = self._generate_schedule_suggestions(drugs, alerts)

        return EvaluationResponse(
            total_drugs_analyzed=len(drugs),
            alerts=alerts,
            schedule_suggestions=suggestions
        )

    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 1: Overdose Check
    # ─────────────────────────────────────────────────────────────────────────
    def _check_overdose(self, drugs: List[DrugItem]) -> List[InteractionAlert]:
        alerts = []
        # Gom nhóm theo hoạt chất gốc (sau khi normalize về lowercase)
        ingredient_groups: dict[str, list[DrugItem]] = {}

        for drug in drugs:
            if not drug.active_ingredient:
                continue
            # Tách hoạt chất kết hợp (vd: "Paracetamol / Caffeine") -> lấy thành phần đầu
            ingredients = [i.strip().lower() for i in drug.active_ingredient.split("/")]
            for ing in ingredients:
                if ing not in ingredient_groups:
                    ingredient_groups[ing] = []
                ingredient_groups[ing].append(drug)

        for ingredient, group in ingredient_groups.items():
            if len(group) < 1:
                continue

            # Tính tổng liều quy đổi/ngày
            total_daily_mg = 0.0
            detail_parts = []
            for drug in group:
                per_dose_mg = _extract_mg_value(drug.strength) or 0
                doses_per_day = _extract_doses_per_day(drug.dosage_instruction)
                qty_per_dose = _extract_qty_per_dose(drug.dosage_instruction)
                daily_mg = per_dose_mg * doses_per_day * qty_per_dose
                total_daily_mg += daily_mg
                detail_parts.append(
                    f"{drug.brand_name} ({drug.strength}) × {qty_per_dose} viên × {doses_per_day} lần = {daily_mg:.0f}mg/ngày"
                )

            # Kiểm tra ngưỡng tối đa từ DB
            max_dose = self.db_max_dose_index.get(ingredient)

            if len(group) > 1:
                # Có >= 2 loại thuốc cùng hoạt chất là luôn đáng cảnh báo
                severity = "HIGH" if (max_dose and total_daily_mg > max_dose) else "MEDIUM"
                title = (
                    f"🔴 Trùng lặp & Quá liều: {ingredient.title()} ({total_daily_mg:.0f}mg/ngày)"
                    if (max_dose and total_daily_mg > max_dose)
                    else f"🟡 Trùng lặp Hoạt Chất: {ingredient.title()}"
                )
                desc = (
                    f"Hệ thống phát hiện {len(group)} sản phẩm cùng chứa {ingredient.title()} trong Tủ thuốc:\n"
                    + "\n".join(f"  • {p}" for p in detail_parts)
                )
                if max_dose and total_daily_mg > max_dose:
                    desc += f"\n⚠️ Tổng liều {total_daily_mg:.0f}mg/ngày VƯỢT ngưỡng an toàn tối đa ({max_dose:.0f}mg/ngày)."

                rec = (
                    f"Chỉ nên sử dụng 1 sản phẩm chứa {ingredient.title()} tại một thời điểm. "
                    "Tham vấn bác sĩ hoặc dược sĩ ngay."
                    if severity == "HIGH"
                    else f"Theo dõi sát triệu chứng. Không tự ý tăng liều {ingredient.title()}."
                )
                alerts.append(InteractionAlert(
                    severity=severity,
                    title=title,
                    description=desc,
                    recommendation=rec
                ))

            elif max_dose and total_daily_mg > max_dose:
                # Chỉ 1 loại nhưng dùng quá liều
                alerts.append(InteractionAlert(
                    severity="HIGH",
                    title=f"🔴 Quá liều: {ingredient.title()} ({total_daily_mg:.0f}mg/ngày)",
                    description=(
                        f"Liều {ingredient.title()} từ {group[0].brand_name} là {total_daily_mg:.0f}mg/ngày, "
                        f"vượt ngưỡng an toàn tối đa {max_dose:.0f}mg/ngày.\n"
                        f"Chi tiết: {detail_parts[0]}"
                    ),
                    recommendation=(
                        f"Giảm liều xuống dưới {max_dose:.0f}mg/ngày. "
                        "Tham vấn bác sĩ hoặc dược sĩ ngay lập tức."
                    )
                ))

        return alerts

    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 2: Drug-Drug Interaction Check
    # ─────────────────────────────────────────────────────────────────────────
    def _check_drug_drug(self, drugs: List[DrugItem]) -> List[InteractionAlert]:
        alerts = []
        # Tập tất cả hoạt chất (lowercase, tách bởi /)
        all_ingredients: set[str] = set()
        for drug in drugs:
            if drug.active_ingredient:
                for ing in drug.active_ingredient.split("/"):
                    all_ingredients.add(ing.strip().lower())

        for interaction in DRUG_DRUG_INTERACTIONS:
            pair: set[str] = interaction["pair"]
            # Kiểm tra cả hai ingredient trong pair có trong tủ thuốc không
            if pair.issubset(all_ingredients):
                alerts.append(InteractionAlert(
                    severity=interaction["severity"],
                    title=interaction["title"],
                    description=interaction["description"],
                    recommendation=interaction["recommendation"]
                ))

        return alerts

    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 3: Drug-Condition Conflict Check
    # ─────────────────────────────────────────────────────────────────────────
    def _check_drug_condition(
        self, drugs: List[DrugItem], user_profile: UserProfile
    ) -> List[InteractionAlert]:
        alerts = []

        # Tập hoạt chất trong tủ thuốc (lowercase)
        all_ingredients: set[str] = set()
        for drug in drugs:
            if drug.active_ingredient:
                for ing in drug.active_ingredient.split("/"):
                    all_ingredients.add(ing.strip().lower())

        # Tập bệnh nền + dị ứng (lowercase)
        user_conditions: set[str] = set()
        for c in user_profile.conditions:
            user_conditions.add(c.strip().lower())
        for a in user_profile.allergies:
            user_conditions.add(a.strip().lower())

        for conflict in DRUG_CONDITION_CONFLICTS:
            # Kiểm tra nếu bất kỳ ingredient nào trong tủ thuốc khớp với conflict
            conflict_ingredients = {i.lower() for i in conflict["ingredients"]}
            conflict_conditions = {c.lower() for c in conflict["conditions"]}

            matching_ingredients = all_ingredients & conflict_ingredients
            matching_conditions = user_conditions & conflict_conditions

            if matching_ingredients and matching_conditions:
                alerts.append(InteractionAlert(
                    severity=conflict["severity"],
                    title=conflict["title"],
                    description=conflict["description"],
                    recommendation=conflict["recommendation"]
                ))

        return alerts

    # ─────────────────────────────────────────────────────────────────────────
    # Tạo gợi ý lịch uống thuốc an toàn
    # ─────────────────────────────────────────────────────────────────────────
    def _generate_schedule_suggestions(
        self, drugs: List[DrugItem], alerts: List[InteractionAlert]
    ) -> List[str]:
        suggestions = []

        # Nếu có tương tác MEDIUM (cần uống cách giờ)
        has_medium = any(a.severity == "MEDIUM" for a in alerts)
        if has_medium:
            suggestions.append("💊 Đối với các thuốc có tương tác nhẹ, hãy uống cách nhau ít nhất 2 giờ để giảm thiểu hấp thu cạnh tranh.")

        # Gợi ý chung về thời điểm uống
        antibiotic_drugs = [
            d.brand_name for d in drugs
            if d.active_ingredient and any(
                ab in d.active_ingredient.lower()
                for ab in ["amoxicillin", "clarithromycin", "ciprofloxacin", "azithromycin"]
            )
        ]
        if antibiotic_drugs:
            suggestions.append(f"💊 Kháng sinh ({', '.join(antibiotic_drugs)}): Uống đều đặn đúng giờ và hoàn thành đủ liệu trình điều trị, không tự ý ngưng thuốc dù thấy đỡ hơn.")

        if not alerts:
            suggestions.append("✅ Không phát hiện tương tác thuốc nguy hiểm trong Tủ thuốc hiện tại. Hãy tiếp tục theo đúng chỉ dẫn của bác sĩ.")

        suggestions.append("⚠️ Thông tin này chỉ mang tính chất tham khảo. Vui lòng tham vấn bác sĩ hoặc dược sĩ trước khi thay đổi phác đồ điều trị.")

        return suggestions


evaluation_service = EvaluationService()
