"""
identifier_bridge.py

Identifier Bridge Architecture: RxNorm Canonical Concepts ↔ DDInter Local Entities (Stage 11/12).
Tuân thủ các Bất biến An toàn Y tế (Clinical Safety Invariants):
- INV-01: NO FORCED MATCH (Không đoán danh tính khi không có bằng chứng)
- INV-02: NO DDI WITHOUT SAFE IDENTITY (Chỉ cho phép tra cứu DDI khi danh tính đã verify)
- INV-03 & INV-04: SOURCE & VERSION PROVENANCE (Lưu vết rõ ràng)
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.services.rxnorm_service import RxNormConcept, NormalizationStatus

logger = logging.getLogger(__name__)


class BridgeMappingType(str, Enum):
    """Phân loại phương thức đối sánh Identifier."""
    DIRECT_CANONICAL = "DIRECT_CANONICAL"
    SYNONYM_BRIDGE_VERIFIED = "SYNONYM_BRIDGE_VERIFIED"
    UNSUPPORTED_NO_MATCH = "UNSUPPORTED_NO_MATCH"


class BridgedDrugEntity(BaseModel):
    """Thực thể thuốc đã được xác thực an toàn qua Identifier Bridge."""
    canonical_ingredient: str = Field(..., description="Tên hoạt chất canonical dùng cho DDI Engine")
    rxcui: Optional[str] = Field(None, description="RxNorm Concept Identifier nếu có")
    original_input_term: str = Field(..., description="Tên thuốc / hoạt chất ban đầu đưa vào")
    bridge_type: BridgeMappingType
    provenance: str = Field(..., description="Nguồn gốc danh tính: rxnorm, local_db, openfda_verified")
    is_safe_for_ddi: bool = Field(..., description="Có đủ điều kiện kích hoạt DDI lookup tự động hay không")


class IdentifierBridge:
    """Bridge chuyển đổi an toàn giữa danh mục RxNorm / CSDL nội bộ sang DDInter."""

    # Từ điển ánh xạ từ đồng nghĩa y khoa chuẩn quốc tế (Medical Synonym Map)
    SYNONYM_DICTIONARY: Dict[str, str] = {
        # NSAIDs & Giảm đau
        "acetylsalicylic acid": "aspirin",
        "acetaminophen": "paracetamol",
        "paracetamol": "paracetamol",
        "aspirin": "aspirin",
        "ibuprofen": "ibuprofen",
        "naproxen": "naproxen",
        "diclofenac": "diclofenac",
        "celecoxib": "celecoxib",
        "etoricoxib": "etoricoxib",
        "meloxicam": "meloxicam",
        "tramadol": "tramadol",
        # Kháng sinh & Kháng nấm
        "amoxicillin": "amoxicillin",
        "clavulanate": "clavulanate",
        "clavulanic acid": "clavulanate",
        "ciprofloxacin": "ciprofloxacin",
        "clarithromycin": "clarithromycin",
        "azithromycin": "azithromycin",
        "erythromycin": "erythromycin",
        "metronidazole": "metronidazole",
        # Tim mạch & Chống đông
        "warfarin": "warfarin",
        "clopidogrel": "clopidogrel",
        "simvastatin": "simvastatin",
        "atorvastatin": "atorvastatin",
        "rosuvastatin": "rosuvastatin",
        "amiodarone": "amiodarone",
        "digoxin": "digoxin",
        "enalapril": "enalapril",
        "losartan": "losartan",
        "spironolactone": "spironolactone",
        "nitroglycerin": "nitroglycerin",
        # Nội tiết & Tiêu hóa
        "metformin": "metformin",
        "levothyroxine": "levothyroxine",
        "omeprazole": "omeprazole",
        "esomeprazole": "omeprazole",
        "pantoprazole": "pantoprazole",
        "sildenafil": "sildenafil",
        "fluoxetine": "fluoxetine",
        "methotrexate": "methotrexate",
        # Kháng viêm dạng men (Enzymes)
        "chymotrypsin": "chymotrypsin",
        "alphachymotrypsin": "chymotrypsin",
        "alphachymotrypsine": "chymotrypsin",
    }

    def bridge_rxnorm_concept(self, concept: Optional[RxNormConcept], input_term: str) -> Optional[BridgedDrugEntity]:
        """
        Chuyển đổi RxNormConcept sang BridgedDrugEntity.
        Nếu concept là None hoặc không có canonical ingredient -> Trả về None (chặn DDI).
        """
        if not concept:
            logger.warning("[IdentifierBridge] Cannot bridge None RxNormConcept for term '%s'", input_term)
            return None

        # Ưu tiên lấy active_ingredient hoặc canonical name
        raw_name = (concept.active_ingredient or concept.name or "").strip().lower()
        if not raw_name:
            return None

        # 1. Kiểm tra trong Medical Synonym Dictionary
        if raw_name in self.SYNONYM_DICTIONARY:
            canonical = self.SYNONYM_DICTIONARY[raw_name]
            b_type = (
                BridgeMappingType.DIRECT_CANONICAL
                if canonical == raw_name
                else BridgeMappingType.SYNONYM_BRIDGE_VERIFIED
            )
            return BridgedDrugEntity(
                canonical_ingredient=canonical,
                rxcui=concept.rxcui,
                original_input_term=input_term,
                bridge_type=b_type,
                provenance=concept.provenance,
                is_safe_for_ddi=True,
            )

        # 2. Nếu tên đã ở dạng chữ thường không có trong từ điển chuẩn
        # Kiểm tra xem có chứa tên hoạt chất đã biết (ví dụ 'amoxicillin trihydrate' -> 'amoxicillin')
        for known_synonym, canonical in self.SYNONYM_DICTIONARY.items():
            if known_synonym in raw_name:
                return BridgedDrugEntity(
                    canonical_ingredient=canonical,
                    rxcui=concept.rxcui,
                    original_input_term=input_term,
                    bridge_type=BridgeMappingType.SYNONYM_BRIDGE_VERIFIED,
                    provenance=concept.provenance,
                    is_safe_for_ddi=True,
                )

        # 3. Không có safe mapping -> Không cho phép DDI
        logger.info("[IdentifierBridge] Unbridged concept '%s' (rxcui=%s) -> Blocking automatic DDI.", raw_name, concept.rxcui)
        return BridgedDrugEntity(
            canonical_ingredient=raw_name,
            rxcui=concept.rxcui,
            original_input_term=input_term,
            bridge_type=BridgeMappingType.UNSUPPORTED_NO_MATCH,
            provenance=concept.provenance,
            is_safe_for_ddi=False,
        )

    def bridge_raw_ingredient(self, ingredient_name: str, input_term: str) -> Optional[BridgedDrugEntity]:
        """
        Chuyển đổi trực tiếp từ tên hoạt chất đã được verify trong CSDL nội bộ.
        """
        clean_name = (ingredient_name or "").strip().lower()
        if not clean_name:
            return None

        # Tách nếu có nhiều hoạt chất kết hợp (ví dụ 'Amoxicillin / Clavulanate')
        first_ing = clean_name.split("/")[0].strip()

        if first_ing in self.SYNONYM_DICTIONARY:
            canonical = self.SYNONYM_DICTIONARY[first_ing]
            return BridgedDrugEntity(
                canonical_ingredient=canonical,
                rxcui=None,
                original_input_term=input_term,
                bridge_type=BridgeMappingType.DIRECT_CANONICAL if canonical == first_ing else BridgeMappingType.SYNONYM_BRIDGE_VERIFIED,
                provenance="local_db",
                is_safe_for_ddi=True,
            )

        for known_synonym, canonical in self.SYNONYM_DICTIONARY.items():
            if known_synonym in first_ing:
                return BridgedDrugEntity(
                    canonical_ingredient=canonical,
                    rxcui=None,
                    original_input_term=input_term,
                    bridge_type=BridgeMappingType.SYNONYM_BRIDGE_VERIFIED,
                    provenance="local_db",
                    is_safe_for_ddi=True,
                )

        return BridgedDrugEntity(
            canonical_ingredient=first_ing,
            rxcui=None,
            original_input_term=input_term,
            bridge_type=BridgeMappingType.UNSUPPORTED_NO_MATCH,
            provenance="local_db_unbridged",
            is_safe_for_ddi=False,
        )


identifier_bridge = IdentifierBridge()
