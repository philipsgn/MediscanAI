"""
Evaluation Service - Engine Đánh Giá Tương Tác Thuốc 3 Lớp
Tuân thủ kiến trúc Backend-Centralized Logic theo AGENTS.md §3.A
"""
import json
import re
from pathlib import Path
from typing import Any, List, Optional, Tuple

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



# [Task5.5-fix] Bat buoc dung dung chu nay cho case CHONG CHI DINH da biet
# (Architect-approved wording; tuan thu dieu cam §5 - khong ket luan don thuoc sai.)
CONTRAINDICATION_NOTE = "Hoạt chất này có ghi nhận chống chỉ định với tình trạng sức khỏe hiện tại của bạn theo tài liệu tham khảo — cần trao đổi ngay với bác sĩ trước khi tiếp tục sử dụng."

class EvaluationService:
    def __init__(self):
        self.db_path = Path(__file__).parent.parent / "data" / "vietnam_drugs_db.json"
        self.guidelines_path = (
            Path(__file__).parent.parent / "data" / "dosage_guidelines.json"
        )
        self.drugs_db = self._load_db()
        self.dosage_guidelines: dict[str, dict] = self._load_guidelines()
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

    def _load_guidelines(self) -> dict[str, dict]:
        """[Task 5.5] Tải bảng liều khuyến cáo theo population từ dosage_guidelines.json.
        Key chuẩn hóa lowercase để tra cứu theo hoạt chất gốc đầu tiên của DrugItem."""
        try:
            with open(self.guidelines_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            guidelines = data.get("guidelines", {})
            return {k.lower().strip(): v for k, v in guidelines.items()}
        except Exception as e:
            print(f"Lỗi tải dosage_guidelines: {e}")
            return {}

    def _evaluate_drug_coverage(
        self, drugs: List[DrugItem], dd_service: Optional[Any] = None
    ) -> Tuple[str, List["DrugCoverageItem"]]:
        """[Stage 12] Đánh giá độ bao phủ CSDL tương tác thuốc cho từng thuốc đầu vào (INV-12-01..04)."""
        from app.services.ddinter_service import ddinter_service
        from app.services.identifier_bridge import identifier_bridge
        from app.schemas.ocr_schema import DrugCoverageItem, DrugCoverageStatus

        active_dd = dd_service or ddinter_service
        coverage_items: List[DrugCoverageItem] = []
        has_unresolved = False
        has_ambiguous = False
        has_not_covered = False

        if not active_dd.integrity_verified or not active_dd.get_covered_ingredients():
            # CSDL rỗng, không tải được hoặc checksum mismatch -> Fail closed sang UNAVAILABLE
            for drug in drugs:
                raw_name = drug.brand_name or "Thuốc không tên"
                coverage_items.append(DrugCoverageItem(
                    drug_name=raw_name,
                    canonical_ingredient=None,
                    status=DrugCoverageStatus.SOURCE_UNAVAILABLE,
                    provenance="ddinter_integrity_failed",
                    note="CSDL tương tác thuốc DDInter không khả dụng hoặc bị lỗi toàn vẹn checksum.",
                ))
            return "UNAVAILABLE", coverage_items

        for drug in drugs:
            raw_name = drug.brand_name or "Thuốc không tên"
            if not drug.active_ingredient or not drug.active_ingredient.strip():
                coverage_items.append(DrugCoverageItem(
                    drug_name=raw_name,
                    canonical_ingredient=None,
                    status=DrugCoverageStatus.UNRESOLVED,
                    provenance=None,
                    note="Chưa xác định được hoạt chất gốc để đối chiếu CSDL tương tác.",
                ))
                has_unresolved = True
                continue

            if drug.match_method == "rxnorm_approximate":
                coverage_items.append(DrugCoverageItem(
                    drug_name=raw_name,
                    canonical_ingredient=None,
                    status=DrugCoverageStatus.AMBIGUOUS_REVIEW_REQUIRED,
                    provenance="rxnorm_approximate",
                    note="Có nhiều ứng viên tương tự — yêu cầu xác nhận trước khi tra cứu DDI.",
                ))
                has_ambiguous = True
                continue

            # INV-12-04: OpenFDA / external unverified candidate cannot promote to COVERED without user verification
            method_clean = str(drug.match_method or "").strip().lower()
            is_unverified_external = (
                bool(method_clean)
                and ("openfda" in method_clean or "external" in method_clean or "fallback" in method_clean)
                and drug.is_verified is not True
            )
            if is_unverified_external:
                coverage_items.append(DrugCoverageItem(
                    drug_name=raw_name,
                    canonical_ingredient=drug.active_ingredient.strip(),
                    status=DrugCoverageStatus.AMBIGUOUS_REVIEW_REQUIRED,
                    provenance=str(drug.match_method),
                    note="Bằng chứng hỗ trợ từ nguồn ngoại vi chưa được xác thực — yêu cầu người dùng xác nhận trước khi tra cứu DDI.",
                ))
                has_ambiguous = True
                continue

            # Bridging to canonical ingredient
            bridged = identifier_bridge.bridge_raw_ingredient(drug.active_ingredient, drug.brand_name)
            if bridged and bridged.is_safe_for_ddi:
                canon = bridged.canonical_ingredient
                if active_dd.is_drug_in_universe(canon):
                    coverage_items.append(DrugCoverageItem(
                        drug_name=raw_name,
                        canonical_ingredient=canon,
                        status=DrugCoverageStatus.COVERED,
                        provenance=bridged.provenance,
                        note=f"Hoạt chất '{canon}' có trong CSDL tri thức DDInter v2.0.",
                    ))
                else:
                    coverage_items.append(DrugCoverageItem(
                        drug_name=raw_name,
                        canonical_ingredient=canon,
                        status=DrugCoverageStatus.NOT_COVERED_IN_DATASET,
                        provenance=bridged.provenance,
                        note=f"Hoạt chất '{canon}' chưa có dữ liệu tương tác trong CSDL DDInter v2.0.",
                    ))
                    has_not_covered = True
            else:
                coverage_items.append(DrugCoverageItem(
                    drug_name=raw_name,
                    canonical_ingredient=None,
                    status=DrugCoverageStatus.UNRESOLVED,
                    provenance="unbridged",
                    note="Hoạt chất chưa được định danh rõ ràng — không đủ điều kiện tra cứu CSDL tương tác.",
                ))
                has_unresolved = True

        if has_unresolved or has_ambiguous:
            overall_status = "UNRESOLVED"
        elif has_not_covered:
            overall_status = "PARTIAL"
        elif not drugs:
            overall_status = "FULL"
        else:
            overall_status = "FULL"

        return overall_status, coverage_items

    def _build_final_summary(
        self,
        alerts: List[InteractionAlert],
        dosage_checks: List["DosageCheckResult"],
        coverage_status: str = "FULL",
        drug_coverage_details: Optional[List["DrugCoverageItem"]] = None,
    ) -> str:
        """Tổng hợp final_summary rule-based tuân thủ bất biến lâm sàng Stage 12 (INV-12-01..04)."""
        from app.schemas.ocr_schema import DrugCoverageStatus

        high = sum(1 for a in alerts if a.severity == "HIGH")
        medium = sum(1 for a in alerts if a.severity == "MEDIUM")
        low = sum(1 for a in alerts if a.severity == "LOW")

        parts = []
        if high + medium + low == 0:
            if coverage_status == "UNAVAILABLE":
                parts.append(
                    "Cảnh báo hệ thống: CSDL tương tác thuốc DDInter không khả dụng hoặc bị lỗi toàn vẹn "
                    "— Tính năng tra cứu tương tác bị khóa an toàn (Fail-Closed). Bắt buộc tham vấn bác sĩ hoặc dược sĩ!"
                )
            elif coverage_status == "FULL":
                parts.append("Đã đối chiếu toàn bộ thuốc với CSDL Tương tác DDInter v2.0 — Không ghi nhận bản ghi tương tác nguy hiểm trong phạm vi CSDL.")
            elif coverage_status == "PARTIAL":
                uncovered = [item.drug_name for item in (drug_coverage_details or []) if item.status == DrugCoverageStatus.NOT_COVERED_IN_DATASET]
                parts.append(
                    f"Đã kiểm tra tương tác thuốc. Lưu ý: có {len(uncovered)} thuốc ({', '.join(uncovered)}) chưa có dữ liệu tương tác trong CSDL DDInter v2.0. "
                    "'Không có cảnh báo' KHÔNG đồng nghĩa với an toàn tuyệt đối — bắt buộc tham vấn bác sĩ/dược sĩ."
                )
            else:  # UNRESOLVED / AMBIGUOUS
                unresolved = [item.drug_name for item in (drug_coverage_details or []) if item.status in (DrugCoverageStatus.UNRESOLVED, DrugCoverageStatus.AMBIGUOUS_REVIEW_REQUIRED)]
                parts.append(
                    f"Có {len(unresolved)} thuốc chưa được định danh rõ ràng hoặc đang chờ xác nhận ({', '.join(unresolved)}). "
                    "Hệ thống không thể kiểm tra tương tác tự động cho các thuốc này — vui lòng kiểm tra lại bước xác nhận thông tin."
                )
        else:
            bits = []
            if high:
                bits.append(f"{high} cảnh báo mức cao")
            if medium:
                bits.append(f"{medium} cảnh báo mức trung bình")
            if low:
                bits.append(f"{low} cảnh báo mức thấp")
            parts.append(f"Phát hiện {', '.join(bits)} về tương tác/trùng lặp/chống chỉ định.")
            if coverage_status != "FULL":
                uncovered_all = [item.drug_name for item in (drug_coverage_details or []) if item.status != DrugCoverageStatus.COVERED]
                if uncovered_all:
                    parts.append(f"(Lưu ý: Có {len(uncovered_all)} thuốc chưa có đủ dữ liệu tương tác trong CSDL: {', '.join(uncovered_all)}).")

        # Thông tin Layer 4
        dosage_counts = {"flag": 0, "ok": 0, "skip": 0}
        for check in dosage_checks:
            if check.is_appropriate is False:
                dosage_counts["flag"] += 1
            elif check.is_appropriate is True:
                dosage_counts["ok"] += 1
            else:
                dosage_counts["skip"] += 1
        if dosage_counts["flag"]:
            parts.append(
                f"Có {dosage_counts['flag']} thuốc có liều dùng chênh lệch đáng xem xét — "
                "vui lòng xác nhận lại với bác sĩ kê đơn."
            )
        elif dosage_counts["ok"]:
            parts.append(
                "Liều dùng khai báo (có dữ liệu) nằm trong giới hạn khuyến cáo tham khảo."
            )
        if dosage_counts["skip"]:
            parts.append(
                f"Lưu ý: Có {dosage_counts['skip']} thuốc chưa đủ dữ liệu hàm lượng/liều dùng — "
                "Layer 4 đã bỏ qua đối chiếu liều, vui lòng kiểm tra kỹ trên bao bì/tờ HDSD hoặc hỏi ý kiến dược sĩ."
            )

        parts.append(
            "Mediscan AI chỉ mang tính tham khảo — không thay thế chỉ định của bác sĩ; "
            "vui lòng tham vấn chuyên khoa trước khi thay đổi phác đồ."
        )
        return " ".join(parts)

    # ─────────────────────────────────────────────────────────────────────────────
    # LAYER 1..4 gọi từ entry point
    # ─────────────────────────────────────────────────────────────────────────────
    def evaluate_medications(
        self,
        drugs: List[DrugItem],
        user_profile: Optional[UserProfile] = None
    ) -> EvaluationResponse:
        """
        Engine Đánh Giá Lâm Sàng — entry point chính tích hợp Stage 12 Governance.
        """
        from app.services.ddinter_service import ddinter_service

        alerts: List[InteractionAlert] = []

        # === LAYER 1: Overdose / Duplicate Active Ingredient ===
        alerts.extend(self._check_overdose(drugs))

        # === LAYER 2: Drug-Drug Interactions ===
        alerts.extend(self._check_drug_drug(drugs))

        # === LAYER 3: Drug-Condition Conflicts ===
        if user_profile:
            alerts.extend(self._check_drug_condition(drugs, user_profile))

        # === LAYER 4: Dosage Appropriateness (Task 5.5) ===
        dosage_checks = self.check_dosage_appropriateness(drugs, user_profile)

        # Sắp xếp: HIGH trước, sau đó MEDIUM, rồi LOW
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 3))

        # Tạo schedule suggestions cơ bản
        suggestions = self._generate_schedule_suggestions(drugs, alerts)

        # Stage 12: Coverage & Governance Evaluation
        coverage_status, coverage_details = self._evaluate_drug_coverage(drugs)
        provenance_metadata = ddinter_service.get_dataset_provenance()

        # Final summary — tổng hợp toàn bộ 4 layer + coverage state (INV-12-01..04)
        final_summary = self._build_final_summary(alerts, dosage_checks, coverage_status, coverage_details)

        return EvaluationResponse(
            total_drugs_analyzed=len(drugs),
            alerts=alerts,
            schedule_suggestions=suggestions,
            dosage_checks=dosage_checks,
            final_summary=final_summary,
            coverage_status=coverage_status,
            drug_coverage_details=coverage_details,
            provenance_metadata=provenance_metadata,
        )

    # ─────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────
    # LAYER 4: Dosage Appropriateness Check (Task 5.5)
    # ─────────────────────────────────────────────────────────────────────────
    def _resolve_population(self, user_profile: Optional[UserProfile]) -> str:
        """Xác định population dựa trên tuổi + bệnh nền (theo AGENTS §3.B.4).
        - ≥65 tuổi → elderly_65+; có suy thận/gan → override renal/hepatic.
        - <18 tuổi → child (KHÔNG đối chiếu tự động — chính sách an toàn).
        - Mặc định → adult."""
        if user_profile is None:
            return "adult"
        age = user_profile.age or 0
        conds = " ".join(c.lower() for c in (user_profile.conditions or []))
        if "suy thận" in conds or "suy gan" in conds:
            if "thận" in conds and "gan" not in conds:
                return "renal_impairment"
            if "gan" in conds:
                return "hepatic_impairment"
        if "suy thận" in conds:
            return "renal_impairment"
        if "suy gan" in conds or "xơ gan" in conds:
            return "hepatic_impairment"
        if age < 18:
            return "child"
        if age >= 65:
            return "elderly_65+"
        return "adult"

    def check_dosage_appropriateness(
        self,
        drugs: List[DrugItem],
        user_profile: Optional[UserProfile] = None,
    ) -> List["DosageCheckResult"]:
        """Layer 4: đối chiếu liều dùng thực tế với khuyến cáo theo population.

        Quy tắc an toàn tuyệt đối (AGENTS §3.B.4 + điều cấm §5):
        - Mọi note dùng mẫu THAM KHẢO, KHÔNG dùng từ "sai/nhầm/không đúng".
        - Hoạt chất ngoài guidelines → is_appropriate=None, note hướng dẫn
          tự đối chiếu, không suy đoán.
        - Population child → is_appropriate=None, note chuyển bác sĩ nhi khoa.
        """
        from app.schemas import DosageCheckResult

        results: List[DosageCheckResult] = []
        if not self.dosage_guidelines:
            return results

        population = self._resolve_population(user_profile)

        for drug in drugs:
            instruction = (drug.dosage_instruction or "").strip()
            if not instruction:
                results.append(DosageCheckResult(
                    drug_name=drug.brand_name,
                    prescribed_or_input_dosage="",
                    recommended_dosage="",
                    is_appropriate=None,
                    note="Chưa có dữ liệu liều dùng để đối chiếu (Layer 4 bỏ qua) — vui lòng bổ sung trong bước xác nhận thông tin.",
                ))
                continue

            ingredient = (drug.active_ingredient or drug.brand_name).split("/")[0].strip().lower()
            guideline = self.dosage_guidelines.get(ingredient)

            if guideline is None:
                results.append(DosageCheckResult(
                    drug_name=drug.brand_name,
                    prescribed_or_input_dosage=instruction,
                    recommended_dosage="",
                    is_appropriate=None,
                    note="Chưa có dữ liệu khuyến cáo cho hoạt chất này trong hệ thống — vui lòng tự đối chiếu với bác sĩ/dược sĩ.",
                ))
                continue

            if population == "child":
                results.append(DosageCheckResult(
                    drug_name=drug.brand_name,
                    prescribed_or_input_dosage=instruction,
                    recommended_dosage="",
                    is_appropriate=None,
                    note="Cần bác sĩ nhi khoa chỉ định — hệ thống không đối chiếu tự động cho trẻ em.",
                ))
                continue

            pop_data = guideline.get("populations", {}).get(
                population, guideline.get("populations", {}).get("adult", {})
            )
            max_mg = pop_data.get("max_mg_per_day")
            recommended_str = pop_data.get("recommended_range") or ""

            # Tinh lieu thuc te tu dosage_instruction
            mg = _extract_mg_value(drug.strength or "")
            if mg is None:
                results.append(DosageCheckResult(
                    drug_name=drug.brand_name,
                    prescribed_or_input_dosage=instruction,
                    recommended_dosage=recommended_str,
                    is_appropriate=None,
                    note="Bao bì không ghi rõ hàm lượng (mg) — Bỏ qua đối chiếu quá liều Layer 4, vui lòng kiểm tra thêm tờ HDSD hoặc tham vấn bác sĩ/dược sĩ.",
                ))
                continue

            daily = mg * _extract_qty_per_dose(instruction) * _extract_doses_per_day(instruction)

            if max_mg is None:
                # [Task5.5-fix] KNOWN contraindication (has tag) -> stronger note
                # than generic missing-data; still is_appropriate=None (never judged).
                ci_tag = (pop_data.get("contraindication_tag") or "").strip()
                if ci_tag:
                    results.append(DosageCheckResult(
                        drug_name=drug.brand_name,
                        prescribed_or_input_dosage=instruction,
                        recommended_dosage=recommended_str,
                        is_appropriate=None,
                        note=CONTRAINDICATION_NOTE,
                    ))
                    continue
                pop_note = (pop_data.get("note") or "").strip()
                base = (
                    f"Lieu {daily:.0f}mg/ngay khac bien so voi khuyen cao tham khao "
                    f"cho nhom '{population}'"
                )
                detail = f" ({pop_note})" if pop_note else ""
                results.append(DosageCheckResult(
                    drug_name=drug.brand_name,
                    prescribed_or_input_dosage=instruction,
                    recommended_dosage=recommended_str,
                    is_appropriate=None,
                    note=f"{base}{detail} — vui long xac nhan lai voi bac si ke don.",
                ))
                continue

            if max_mg is not None and daily > max_mg:
                results.append(DosageCheckResult(
                    drug_name=drug.brand_name,
                    prescribed_or_input_dosage=instruction,
                    recommended_dosage=recommended_str,
                    is_appropriate=False,
                    note=f"Lieu {daily:.0f}mg/ngay vuot khuyen cao {max_mg}mg/ngay — vui long xac nhan lai voi bac si ke don.",
                ))
            else:
                results.append(DosageCheckResult(
                    drug_name=drug.brand_name,
                    prescribed_or_input_dosage=instruction,
                    recommended_dosage=recommended_str,
                    is_appropriate=True,
                    note="Lieu dung trong gioi han khuyen cao tham khao.",
                ))

        return results

    # ─────────────────────────────────────────────────────────────────────────────
    # LAYER 1: Overdose Check
    # ─────────────────────────────────────────────────────────────────────────────
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
                str_display = drug.strength if drug.strength else "chưa rõ hàm lượng"
                detail_parts.append(
                    f"{drug.brand_name} ({str_display}) × {qty_per_dose} viên × {doses_per_day} lần = {daily_mg:.0f}mg/ngày"
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
    # LAYER 2: Drug-Drug Interaction Check (Core Matrix + DDInter v2.0 Local)
    # ─────────────────────────────────────────────────────────────────────────
    def _check_drug_drug(self, drugs: List[DrugItem]) -> List[InteractionAlert]:
        from app.services.ddinter_service import ddinter_service
        from app.services.identifier_bridge import identifier_bridge

        alerts: List[InteractionAlert] = []
        # Tập tất cả hoạt chất đã được verify qua Identifier Bridge
        safe_canonical_ingredients: set[str] = set()
        raw_ingredients: set[str] = set()
        alerted_pairs: set[frozenset[str]] = set()

        for drug in drugs:
            if drug.active_ingredient and drug.active_ingredient.strip():
                # INV-12-04: OpenFDA / external unverified items are blocked from safe canonical DDI lookup until verified
                method_clean = str(drug.match_method or "").strip().lower()
                if (
                    bool(method_clean)
                    and ("openfda" in method_clean or "external" in method_clean or "fallback" in method_clean)
                    and drug.is_verified is not True
                ):
                    continue
                for ing in drug.active_ingredient.split("/"):
                    clean_ing = ing.strip().lower()
                    if clean_ing:
                        raw_ingredients.add(clean_ing)
                        bridged = identifier_bridge.bridge_raw_ingredient(clean_ing, drug.brand_name)
                        if bridged and bridged.is_safe_for_ddi:
                            safe_canonical_ingredients.add(bridged.canonical_ingredient)

        # 1. Tra cứu ma trận ưu tiên cao nội bộ (Core Emergency Rules)
        for interaction in DRUG_DRUG_INTERACTIONS:
            pair: set[str] = interaction["pair"]
            # Kiểm tra cả hai ingredient trong pair có trong tủ thuốc không (raw hoặc canonical)
            if pair.issubset(raw_ingredients) or pair.issubset(safe_canonical_ingredients):
                pair_key = frozenset(pair)
                alerted_pairs.add(pair_key)
                alerts.append(InteractionAlert(
                    severity=interaction["severity"],
                    title=interaction["title"],
                    description=interaction["description"],
                    recommendation=interaction["recommendation"]
                ))

        # 2. Tra cứu mở rộng từ CSDL DDInter v2.0 On-Premise cho các hoạt chất safe (chỉ khi CSDL verified)
        if ddinter_service.integrity_verified:
            ddinter_results = ddinter_service.find_all_interactions(list(safe_canonical_ingredients))
            for entry in ddinter_results:
                pair_key = frozenset([entry.drug_a, entry.drug_b])
                if pair_key in alerted_pairs:
                    continue  # Đã có cảnh báo từ core matrix

                alerted_pairs.add(pair_key)
                title_prefix = "🔴 Chống chỉ định" if entry.severity == "HIGH" else ("🟡 Thận trọng" if entry.severity == "MEDIUM" else "ℹ️ Tương tác nhẹ")
                alerts.append(InteractionAlert(
                    severity=entry.severity,
                    title=f"{title_prefix}: {entry.drug_a.title()} + {entry.drug_b.title()} [{entry.ddinter_id}]",
                    description=(
                        f"Cơ chế: {entry.mechanism}\n"
                        f"Xử trí lâm sàng: {entry.management}\n"
                        f"(Nguồn: DDInter v{entry.dataset_version} - ID: {entry.ddinter_id})"
                    ),
                    recommendation=entry.recommendation or entry.management,
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