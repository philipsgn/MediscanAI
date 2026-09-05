"""
Ingestion Pipeline for Extended Master Drug Registry (Medicine_Details.csv).
Parses 11,825+ medicines, canonicalizes active ingredients, extracts strengths,
and classifies clinical categories.
Outputs backend/app/data/extended_medicines_db.json.
"""

from __future__ import annotations

import csv
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_medicines")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = PROJECT_ROOT / "drug_data" / "dataset_1788446818563" / "Medicine_Details.csv" / "Medicine_Details.csv"
OUTPUT_JSON_PATH = PROJECT_ROOT / "backend" / "app" / "data" / "extended_medicines_db.json"

# Bảng chuẩn hóa danh pháp hoạt chất quốc tế (INN Canonicalization)
INGREDIENT_CANONICAL_MAP = {
    "amoxycillin": "Amoxicillin",
    "amoxicillin": "Amoxicillin",
    "clavulanate": "Clavulanic Acid",
    "clavulanic acid": "Clavulanic Acid",
    "potassium clavulanate": "Clavulanic Acid",
    "acetaminophen": "Paracetamol",
    "paracetamol": "Paracetamol",
    "levosalbutamol": "Levosalbutamol",
    "salbutamol": "Salbutamol",
    "albuterol": "Salbutamol",
    "chlorpheniramine maleate": "Chlorpheniramine",
    "chlorpheniramine": "Chlorpheniramine",
    "ranitidine hydrochloride": "Ranitidine",
    "ranitidine": "Ranitidine",
    "omeprazole": "Omeprazole",
    "esomeprazole": "Esomeprazole",
    "pantoprazole": "Pantoprazole",
    "rabeprazole": "Rabeprazole",
    "lansoprazole": "Lansoprazole",
    "fexofenadine hydrochloride": "Fexofenadine",
    "fexofenadine": "Fexofenadine",
    "cetirizine hydrochloride": "Cetirizine",
    "cetirizine": "Cetirizine",
    "loratadine": "Loratadine",
    "desloratadine": "Desloratadine",
    "atorvastatin": "Atorvastatin",
    "rosuvastatin": "Rosuvastatin",
    "simvastatin": "Simvastatin",
    "metformin hydrochloride": "Metformin",
    "metformin": "Metformin",
    "glimepiride": "Glimepiride",
    "gliclazide": "Gliclazide",
    "amlodipine besylate": "Amlodipine",
    "amlodipine": "Amlodipine",
    "telmisartan": "Telmisartan",
    "losartan potassium": "Losartan",
    "losartan": "Losartan",
    "valsartan": "Valsartan",
    "azithromycin": "Azithromycin",
    "ciprofloxacin": "Ciprofloxacin",
    "levofloxacin": "Levofloxacin",
    "ofloxacin": "Ofloxacin",
    "cefixime": "Cefixime",
    "cefpodoxime proxetil": "Cefpodoxime",
    "cefpodoxime": "Cefpodoxime",
    "ceftriaxone": "Ceftriaxone",
    "cefaclor": "Cefaclor",
    "cefuroxime axetil": "Cefuroxime",
    "cefuroxime": "Cefuroxime",
    "ibuprofen": "Ibuprofen",
    "mefenamic acid": "Mefenamic Acid",
    "diclofenac sodium": "Diclofenac",
    "diclofenac potassium": "Diclofenac",
    "diclofenac": "Diclofenac",
    "aceclofenac": "Aceclofenac",
    "etoricoxib": "Etoricoxib",
    "celecoxib": "Celecoxib",
    "tramadol hydrochloride": "Tramadol",
    "tramadol": "Tramadol",
    "dextromethorphan": "Dextromethorphan",
    "guaifenesin": "Guaifenesin",
    "ambroxol hydrochloride": "Ambroxol",
    "ambroxol": "Ambroxol",
    "bromhexine": "Bromhexine",
    "domperidone": "Domperidone",
    "ondansetron": "Ondansetron",
}

DOSAGE_FORM_STRIP_REGEX = re.compile(
    r"\b(tablet|capsule|injection|syrup|suspension|drops|cream|gel|ointment|solution|infusion|powder|lotion|spray|respules|sachet|sr|er|cr|dr|xr|dt|forte|duo|plus)\b",
    re.IGNORECASE,
)


def parse_composition(comp_str: str) -> Tuple[str, str]:
    """
    Phân tích chuỗi Composition thành cặp (active_ingredient, strength).
    Ví dụ: 'Amoxycillin (500mg) + Clavulanic Acid (125mg)'
    -> ('Amoxicillin / Clavulanic Acid', '500mg / 125mg')
    """
    if not comp_str or not comp_str.strip():
        return "", ""

    parts = [p.strip() for p in comp_str.split("+") if p.strip()]
    ingredients: List[str] = []
    strengths: List[str] = []

    for part in parts:
        # Match 'Name (Strength)'
        m = re.match(r"^(.*?)\s*\((.*?)\)$", part)
        if m:
            raw_ing = m.group(1).strip()
            raw_str = m.group(2).strip()
        else:
            raw_ing = part
            raw_str = ""

        # Chuẩn hóa tên hoạt chất
        canonical_ing = INGREDIENT_CANONICAL_MAP.get(raw_ing.lower(), raw_ing.title())
        ingredients.append(canonical_ing)
        if raw_str:
            strengths.append(raw_str)

    clean_ingredients = " / ".join(ingredients)
    clean_strengths = " / ".join(strengths) if strengths else ""
    return clean_ingredients, clean_strengths


def classify_category(uses_str: str) -> str:
    """Gắn thẻ danh mục điều trị lâm sàng từ trường Uses."""
    u = (uses_str or "").lower()
    if any(k in u for k in ["pain", "fever", "headache", "arthr", "musc", "inflamm", "sprain"]):
        return "Giảm đau - Kháng viêm - Hạ sốt"
    if any(k in u for k in ["reflux", "ulcer", "acidity", "heartburn", "stomach", "gastro", "esophag", "gerd", "peptic"]):
        return "Dạ dày - Kháng acid - Tiêu hóa"
    if any(k in u for k in ["bacterial", "infection", "antibiotic", "urinary tract"]):
        return "Kháng sinh - Kháng khuẩn"
    if any(k in u for k in ["hypertension", "blood pressure", "heart", "cholesterol", "statin", "angina", "cardiac"]):
        return "Tim mạch - Huyết áp - Mỡ máu"
    if any(k in u for k in ["diabetes", "glyc", "insulin", "sugar", "glucose"]):
        return "Đái tháo đường"
    if any(k in u for k in ["cough", "allergy", "allergic", "asthma", "cold", "rhinitis", "sneezing", "bronch"]):
        return "Hô hấp - Dị ứng - Cảm cúm"
    if any(k in u for k in ["fungal", "fungi", "yeast", "candid"]):
        return "Kháng nấm"
    if any(k in u for k in ["viral", "virus", "hiv", "herpes"]):
        return "Kháng virus"
    if any(k in u for k in ["anxiety", "depress", "sleep", "epilep", "seizure", "schizo", "psych"]):
        return "Thần kinh - An thần"
    if any(k in u for k in ["eye", "ocular", "glaucoma"]):
        return "Thuốc nhãn khoa"
    if any(k in u for k in ["skin", "acne", "eczema", "dermat"]):
        return "Da liễu"
    return "Thuốc điều trị chuyên khoa"


def extract_base_brand(brand: str) -> str:
    """Loại bỏ dạng bào chế, hàm lượng để lấy tên gốc của biệt dược."""
    b = brand.strip()
    # Loại bỏ dạng bào chế (Tablet, Capsule, Syrup...)
    b = DOSAGE_FORM_STRIP_REGEX.sub(" ", b)
    # Loại bỏ các số kèm đơn vị (500mg, 100ml...)
    b = re.sub(r"\s*\d+(?:[\.,]\d+)?\s*(?:mg|g|ml|mcg|iu|%|\/|\b).*$", "", b, flags=re.IGNORECASE)
    # Xóa ký tự đặc biệt thừa
    b = re.sub(r"[^\w\s\-]", " ", b)
    b = re.sub(r"\s+", " ", b).strip()
    return b


def run_ingestion() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Không tìm thấy file CSV tại: {CSV_PATH}")

    logger.info("Bắt đầu đọc tệp CSV: %s", CSV_PATH)
    records: List[Dict[str, Any]] = []
    seen_brands: set[str] = set()

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            brand_name = row.get("Medicine Name", "").strip()
            composition = row.get("Composition", "").strip()
            uses = row.get("Uses", "").strip()
            side_effects = row.get("Side_effects", "").strip()
            manufacturer = row.get("Manufacturer", "").strip()

            if not brand_name or not composition:
                continue

            # Bỏ qua trùng lặp hoàn toàn tên biệt dược
            brand_lower = brand_name.lower()
            if brand_lower in seen_brands:
                continue
            seen_brands.add(brand_lower)

            active_ing, strength = parse_composition(composition)
            category = classify_category(uses)
            base_brand = extract_base_brand(brand_name)

            doc_id = f"EXT_{idx + 1:05d}"
            record = {
                "id": doc_id,
                "brand_name": brand_name,
                "base_brand_name": base_brand,
                "active_ingredient": active_ing,
                "strength": strength,
                "category": category,
                "uses": uses,
                "side_effects": side_effects,
                "manufacturer": manufacturer,
                "source": "Medicine_Details_Extended_Master",
            }
            records.append(record)

    logger.info("Đã phân tích thành công %d bản ghi thuốc.", len(records))

    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    logger.info("Đã xuất CSDL mở rộng ra: %s (Kích thước: %.2f MB)", OUTPUT_JSON_PATH, OUTPUT_JSON_PATH.stat().st_size / (1024 * 1024))


if __name__ == "__main__":
    run_ingestion()
