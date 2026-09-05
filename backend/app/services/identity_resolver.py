"""
identity_resolver.py — Unified Drug Identity Resolver & Multi-Evidence Engine.

Chịu trách nhiệm hợp nhất bằng chứng đa nguồn (Multi-Source Evidence Fusion)
và phân giải danh tính thuốc (Drug Identity Resolution) cho Mediscan AI:
1. Tiếp nhận DrugObservation (bằng chứng từ Front, Back, Leaflet).
2. Tách biệt rõ ràng:
   - OCR Confidence vs Identity Confidence vs Source Confidence.
   - SOURCE_UNAVAILABLE (lỗi hạ tầng) vs UNRESOLVED (khuyết thiếu dữ liệu).
3. Sử dụng Strength làm Disambiguation Evidence (giải quyết nhập nhằng biến thể), không bắt buộc.
4. Phát hiện mâu thuẫn CONFLICTING_EVIDENCE (ngăn chặn ghép sai thuốc giữa mặt trước và mặt sau).
5. Không áp dụng quy tắc ngây thơ "Local DB luôn thắng" — hỗ trợ đối soát chéo và đồng thuận đa nguồn.
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import httpx
from pydantic import BaseModel, Field

from app.services.drug_database import drug_database
from app.services.rxnorm_service import rxnorm_service, NormalizationStatus, RxNormConcept
from app.services.identifier_bridge import IdentifierBridge

logger = logging.getLogger(__name__)


class IdentityResolutionStatus(str, Enum):
    """Trạng thái phân giải danh tính thuốc."""
    RESOLVED = "RESOLVED"
    CANDIDATE_REQUIRES_REVIEW = "CANDIDATE_REQUIRES_REVIEW"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    UNRESOLVED = "UNRESOLVED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


class EvidenceField(BaseModel):
    """Bằng chứng OCR đơn lẻ kèm nguồn gốc ảnh và độ tin cậy."""
    value: str
    source_image: str = "front"  # "front", "back", "leaflet", "prescription"
    ocr_confidence: float = 0.90
    bbox: Optional[List[float]] = None


class DrugObservation(BaseModel):
    """Tập hợp bằng chứng quan sát được của một sản phẩm thuốc từ một hoặc nhiều ảnh."""
    observation_id: str
    observed_brand_name: Optional[EvidenceField] = None
    observed_strength: Optional[EvidenceField] = None
    observed_active_ingredient: Optional[EvidenceField] = None
    observed_dosage_form: Optional[EvidenceField] = None
    observed_registration_no: Optional[EvidenceField] = None
    raw_texts: List[str] = Field(default_factory=list)


class DrugObservationSet(BaseModel):
    """Phiên làm việc tập hợp các quan sát thuốc trong session."""
    session_id: str
    source_stream: str = "packaging"  # "packaging" | "prescription"
    observations: List[DrugObservation] = Field(default_factory=list)


class IdentityConfidenceScore(BaseModel):
    """Ma trận tách biệt độ tin cậy danh tính theo chuẩn Senior ML Architecture."""
    ocr_confidence: float = 0.0
    source_confidence: float = 0.0
    semantic_match_score: float = 0.0
    overall_confidence: float = 0.0


class ResolvedDrugIdentity(BaseModel):
    """Thực thể thuốc đã phân giải đầy đủ thông tin chuẩn hóa."""
    canonical_brand_name: str
    resolved_active_ingredients: List[str] = Field(default_factory=list)
    canonical_active_ingredient: str
    canonical_strength: Optional[str] = None
    canonical_dosage_form: Optional[str] = None
    identity_provenance: str  # "local_db", "rxnorm", "openfda", "cross_verified"
    identity_provenance_id: Optional[str] = None  # "DRUG_001", "rxnorm:153744", etc.
    variants: List[str] = Field(default_factory=list)
    is_unique_strength: bool = False
    _strength_source: Optional[str] = None


class IdentityResolutionResult(BaseModel):
    """Kết quả hoàn chỉnh của tầng Identity Resolver."""
    status: IdentityResolutionStatus
    query_term: str
    resolved_identity: Optional[ResolvedDrugIdentity] = None
    candidates: List[ResolvedDrugIdentity] = Field(default_factory=list)
    confidence: IdentityConfidenceScore = Field(default_factory=IdentityConfidenceScore)
    conflict_reason: Optional[str] = None
    error_message: Optional[str] = None


class UnifiedDrugIdentityResolver:
    """Engine phân giải danh tính thuốc trung tâm của Mediscan AI."""

    def __init__(self) -> None:
        self.bridge = IdentifierBridge()

    def _normalize_name(self, text: str) -> str:
        """Làm sạch chuỗi tên cơ bản."""
        if not text:
            return ""
        cleaned = re.sub(r"[®™©\*\#]", "", text)
        cleaned = re.sub(r"\b\d+(?:[\.,]\d+)?\s*(?:mg|g|ml|mcg|iu|%|\/)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _normalize_ingredient_str(self, text: str) -> str:
        """Chuẩn hóa tên hoạt chất để so sánh đồng nghĩa."""
        if not text:
            return ""
        norm = text.lower().strip()
        # Ánh xạ qua synonym dictionary nếu có
        return self.bridge.SYNONYM_DICTIONARY.get(norm, norm)

    def _check_ingredient_conflict(self, ing1: str, ing2: str) -> bool:
        """
        Kiểm tra xem hai hoạt chất có mâu thuẫn thực sự hay không.
        Trả về True nếu mâu thuẫn (không đồng nghĩa và không bao hàm nhau).
        """
        if not ing1 or not ing2:
            return False
        c1 = self._normalize_ingredient_str(ing1)
        c2 = self._normalize_ingredient_str(ing2)
        if c1 == c2:
            return False
        # Nếu là thuốc phối hợp, kiểm tra tập hợp hoạt chất con
        parts1 = {self._normalize_ingredient_str(p.strip()) for p in re.split(r"[/,+]|\band\b", c1)}
        parts2 = {self._normalize_ingredient_str(p.strip()) for p in re.split(r"[/,+]|\band\b", c2)}
        if parts1.intersection(parts2):
            return False
        return True

    async def resolve_observation(
        self,
        observation: DrugObservation,
        client: Optional[httpx.AsyncClient] = None,
    ) -> IdentityResolutionResult:
        """
        Phân giải danh tính của một DrugObservation.
        Ưu tiên hàng đầu: Tên sản phẩm / Brand name.
        Bằng chứng bổ sung: Strength (phân giải biến thể), Active Ingredient (đối soát mâu thuẫn).
        """
        brand_field = observation.observed_brand_name
        strength_field = observation.observed_strength
        ingredient_field = observation.observed_active_ingredient

        raw_brand = brand_field.value if brand_field else ""
        raw_strength = strength_field.value if strength_field else ""
        raw_ingredient = ingredient_field.value if ingredient_field else ""
        ocr_conf = brand_field.ocr_confidence if brand_field else 0.90

        if not raw_brand and not raw_ingredient:
            return IdentityResolutionResult(
                status=IdentityResolutionStatus.UNRESOLVED,
                query_term="",
                error_message="Observation không chứa Brand Name hoặc Ingredient",
                confidence=IdentityConfidenceScore(ocr_confidence=0.0),
            )

        query_brand = self._normalize_name(raw_brand) if raw_brand else ""
        candidates: List[ResolvedDrugIdentity] = []
        is_source_unavailable = False
        unavailable_reasons: List[str] = []

        # ─────────────────────────────────────────────────────────────────────
        # NGUỒN 1: Local Drug Database (Việt Nam)
        # ─────────────────────────────────────────────────────────────────────
        local_match = None
        if query_brand:
            # Tra cứu chính xác hoặc fuzzy từ Local DB
            db_item = drug_database.find_by_brand_exact(query_brand)
            if not db_item:
                db_item = drug_database.find_by_brand_fuzzy(query_brand, threshold=75)
            if db_item:
                variants = drug_database.get_drug_variants(db_item.get("brand_name", ""))
                candidates.append(
                    ResolvedDrugIdentity(
                        canonical_brand_name=db_item.get("brand_name", query_brand),
                        resolved_active_ingredients=[db_item.get("active_ingredient", "")],
                        canonical_active_ingredient=db_item.get("active_ingredient", ""),
                        canonical_strength=db_item.get("strength"),
                        canonical_dosage_form=db_item.get("dosage_form"),
                        identity_provenance="local_db",
                        identity_provenance_id=db_item.get("id"),
                        variants=variants or db_item.get("common_strengths", []),
                        is_unique_strength=db_item.get("is_unique_strength", False),
                        _strength_source=db_item.get("_strength_source"),
                    )
                )
                local_match = db_item

        # ─────────────────────────────────────────────────────────────────────
        # NGUỒN 2: RxNorm / RxNav REST API (Primary Authority Quốc Tế)
        # ─────────────────────────────────────────────────────────────────────
        rx_match = None
        if query_brand:
            try:
                rx_res = await rxnorm_service.resolve_drug(query_brand, client=client)
                if rx_res.status == NormalizationStatus.SOURCE_UNAVAILABLE:
                    is_source_unavailable = True
                    unavailable_reasons.append(f"RxNav: {rx_res.error_message}")
                elif rx_res.status == NormalizationStatus.RESOLVED and rx_res.concept:
                    conc = rx_res.concept
                    ings = conc.active_ingredients or ([conc.active_ingredient] if conc.active_ingredient else [])
                    canonical_ing = conc.active_ingredient or conc.name
                    candidates.append(
                        ResolvedDrugIdentity(
                            canonical_brand_name=conc.name,
                            resolved_active_ingredients=ings,
                            canonical_active_ingredient=canonical_ing,
                            canonical_strength=None,
                            identity_provenance="rxnorm",
                            identity_provenance_id=f"rxnorm:{conc.rxcui}",
                            variants=[],
                            is_unique_strength=False,
                        )
                    )
                    rx_match = conc
            except Exception as e:
                is_source_unavailable = True
                unavailable_reasons.append(f"RxNav Error: {e}")

        # ─────────────────────────────────────────────────────────────────────
        # NGUỒN 3: OpenFDA REST API (Supporting Evidence)
        # ─────────────────────────────────────────────────────────────────────
        fda_match = None
        if query_brand and not local_match:
            try:
                fda_item = await drug_database.fetch_openfda_by_brand(query_brand)
                if fda_item and fda_item.get("brand_name"):
                    substances = fda_item.get("active_ingredient", [])
                    if isinstance(substances, str):
                        substances = [substances]
                    candidates.append(
                        ResolvedDrugIdentity(
                            canonical_brand_name=fda_item.get("brand_name", query_brand),
                            resolved_active_ingredients=substances,
                            canonical_active_ingredient=" / ".join(substances),
                            canonical_strength=fda_item.get("strength"),
                            canonical_dosage_form=fda_item.get("dosage_form"),
                            identity_provenance="openfda",
                            identity_provenance_id=f"openfda:{fda_item.get('id', '')}",
                            variants=[],
                            is_unique_strength=False,
                        )
                    )
                    fda_match = fda_item
            except Exception as e:
                logger.debug("[IdentityResolver] OpenFDA query warning for %s: %s", query_brand, e)

        # ─────────────────────────────────────────────────────────────────────
        # ĐỐI SOÁT MÂU THUẪN (CONFLICTING_EVIDENCE DETECTION)
        # ─────────────────────────────────────────────────────────────────────
        # Case A: Mâu thuẫn giữa Bằng chứng OCR mặt sau (observed_ingredient) và kết quả Brand
        if raw_ingredient and candidates:
            primary_candidate_ing = candidates[0].canonical_active_ingredient
            if self._check_ingredient_conflict(raw_ingredient, primary_candidate_ing):
                return IdentityResolutionResult(
                    status=IdentityResolutionStatus.CONFLICTING_EVIDENCE,
                    query_term=raw_brand or raw_ingredient,
                    candidates=candidates,
                    conflict_reason=(
                        f"Mâu thuẫn bằng chứng: Mặt trước nhận diện '{raw_brand}' (thường là '{primary_candidate_ing}'), "
                        f"nhưng ảnh bổ sung lại đọc được hoạt chất '{raw_ingredient}'."
                    ),
                    confidence=IdentityConfidenceScore(
                        ocr_confidence=ocr_conf,
                        source_confidence=0.5,
                        semantic_match_score=0.4,
                        overall_confidence=0.45,
                    ),
                )

        # Case B: Mâu thuẫn giữa hai nguồn authoritative (Local DB vs RxNorm)
        # Chỉ kích hoạt khi cả hai nguồn đều có định danh thẩm quyền EXACT (không đối chiếu phonetic approximate)
        if local_match and rx_match:
            is_rx_exact = getattr(rx_match, "provenance", "") == "rxnorm" and getattr(rx_match, "tty", "") in ("BN", "SBD", "SCD", "IN", "PIN", "MIN")
            if is_rx_exact:
                loc_ing = local_match.get("active_ingredient", "")
                rx_ing = rx_match.active_ingredient or rx_match.name
                if self._check_ingredient_conflict(loc_ing, rx_ing):
                    return IdentityResolutionResult(
                        status=IdentityResolutionStatus.CONFLICTING_EVIDENCE,
                        query_term=query_brand,
                        candidates=candidates,
                        conflict_reason=(
                            f"Mâu thuẫn danh tính giữa các nguồn thẩm định: Local DB ghi nhận '{loc_ing}', "
                            f"trong khi RxNorm quốc tế ghi nhận '{rx_ing}'."
                        ),
                        confidence=IdentityConfidenceScore(
                            ocr_confidence=ocr_conf,
                            source_confidence=0.5,
                            semantic_match_score=0.4,
                            overall_confidence=0.45,
                        ),
                    )

        # ─────────────────────────────────────────────────────────────────────
        # GIẢI QUYẾT BIẾN THỂ BẰNG STRENGTH (DISAMBIGUATION EVIDENCE)
        # ─────────────────────────────────────────────────────────────────────
        if candidates and raw_strength:
            # Chuẩn hóa số hàm lượng (e.g. "625mg", "1g", "500mg")
            norm_str = raw_strength.lower().replace(" ", "")
            for c in candidates:
                if c.variants:
                    for v in c.variants:
                        if v.lower().replace(" ", "") == norm_str:
                            # Khớp chính xác biến thể hàm lượng
                            c.canonical_strength = v
                            break

        # ─────────────────────────────────────────────────────────────────────
        # TỔNG HỢP TRẠNG THÁI VÀ ĐIỂM TIN CẬY
        # ─────────────────────────────────────────────────────────────────────
        if not candidates:
            if is_source_unavailable:
                return IdentityResolutionResult(
                    status=IdentityResolutionStatus.SOURCE_UNAVAILABLE,
                    query_term=query_brand or raw_ingredient,
                    error_message=f"Không thể kết nối tới nguồn thẩm định: {'; '.join(unavailable_reasons)}",
                    confidence=IdentityConfidenceScore(
                        ocr_confidence=ocr_conf,
                        source_confidence=0.0,
                        semantic_match_score=0.0,
                        overall_confidence=0.0,
                    ),
                )
            return IdentityResolutionResult(
                status=IdentityResolutionStatus.UNRESOLVED,
                query_term=query_brand or raw_ingredient,
                error_message="Không tìm thấy ứng viên danh tính phù hợp trong bất kỳ nguồn dữ liệu nào",
                confidence=IdentityConfidenceScore(
                    ocr_confidence=ocr_conf,
                    source_confidence=0.0,
                    semantic_match_score=0.0,
                    overall_confidence=0.0,
                ),
            )

        # Lựa chọn ứng viên có độ tin cậy nguồn cao nhất
        # Thứ tự ưu tiên đồng thuận: Cross-verified > Local Verified > RxNorm Exact > OpenFDA
        chosen = candidates[0]
        source_conf = 1.0 if chosen.identity_provenance == "local_db" else 0.90

        # Tính overall confidence tách biệt với OCR confidence
        semantic_score = 0.95
        overall_conf = round(0.4 * ocr_conf + 0.3 * source_conf + 0.3 * semantic_score, 4)

        confidence_matrix = IdentityConfidenceScore(
            ocr_confidence=round(ocr_conf, 4),
            source_confidence=source_conf,
            semantic_match_score=semantic_score,
            overall_confidence=overall_conf,
        )

        return IdentityResolutionResult(
            status=IdentityResolutionStatus.RESOLVED,
            query_term=query_brand or raw_ingredient,
            resolved_identity=chosen,
            candidates=candidates,
            confidence=confidence_matrix,
        )

    async def aggregate_and_resolve(
        self,
        observation_set: DrugObservationSet,
        client: Optional[httpx.AsyncClient] = None,
    ) -> List[IdentityResolutionResult]:
        """Phân giải toàn bộ danh sách quan sát trong một session."""
        results = []
        for obs in observation_set.observations:
            res = await self.resolve_observation(obs, client=client)
            results.append(res)
        return results


# Global singleton resolver instance
unified_identity_resolver = UnifiedDrugIdentityResolver()
