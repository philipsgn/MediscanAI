"""
rxnorm_service.py

RxNorm / RxNav REST API Client — Primary Drug Normalization Authority (Stage 11/12).
Tuân thủ chuẩn US National Library of Medicine (NLM) RxNav REST API:
- Endpoint: https://rxnav.nlm.nih.gov/REST/
- Không yêu cầu API Key
- Không forced matching: Ambiguous / Unverified -> UNRESOLVED hoặc CANDIDATE_REQUIRES_REVIEW
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import httpx

logger = logging.getLogger(__name__)


class NormalizationStatus(str, Enum):
    """Trạng thái chuẩn hóa danh tính thuốc theo State Machine."""
    RESOLVED = "RESOLVED"
    CANDIDATE_REQUIRES_REVIEW = "CANDIDATE_REQUIRES_REVIEW"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    UNRESOLVED = "UNRESOLVED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


class RxNormConcept(BaseModel):
    """Thông tin thực thể thuốc / hoạt chất trích xuất từ RxNorm."""
    rxcui: str = Field(..., description="RxNorm Concept Unique Identifier")
    name: str = Field(..., description="Tên canonical từ RxNorm")
    tty: str = Field(..., description="Term Type: IN (Ingredient), PIN, MIN, BN (Brand Name), SCD, SBD")
    synonym: Optional[str] = None
    active_ingredient: Optional[str] = None
    active_ingredients: List[str] = Field(default_factory=list, description="Danh sách hoạt chất (hỗ trợ thuốc phối hợp)")
    provenance: str = Field("rxnorm", description="Nguồn gốc chuẩn hóa")
    confidence_score: float = Field(1.0, description="Độ tin cậy của concept")


class RxNormResolutionResult(BaseModel):
    """Kết quả phân giải danh tính thuốc qua RxNorm."""
    status: NormalizationStatus
    query_term: str
    concept: Optional[RxNormConcept] = None
    candidates: List[RxNormConcept] = Field(default_factory=list)
    error_message: Optional[str] = None


class RxNormService:
    """Async Client tương tác với RxNav REST API có LRU Cache và Fail-fast Resilience."""

    BASE_URL: str = "https://rxnav.nlm.nih.gov/REST"
    TIMEOUT_SECONDS: float = 4.0

    def __init__(self, base_url: Optional[str] = None, timeout: float = 4.0) -> None:
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.timeout = timeout
        self._cache: Dict[str, RxNormResolutionResult] = {}

    def _clean_query(self, term: str) -> str:
        """Chuẩn hóa query: loại bỏ ký tự đặc biệt, dấu hàm lượng nếu có."""
        if not term:
            return ""
        cleaned = re.sub(r"\b\d+(?:[\.,]\d+)?\s*(?:mg|g|ml|mcg|iu|%|\/)\b", "", term, flags=re.IGNORECASE)
        cleaned = re.sub(r"[^\w\s\-]", " ", cleaned).strip()
        return " ".join(cleaned.split())

    async def get_rxcui_by_name(self, name: str, client: Optional[httpx.AsyncClient] = None) -> Optional[str]:
        """Tra cứu chính xác RxCUI theo tên (Exact Name lookup)."""
        clean_name = self._clean_query(name)
        if not clean_name:
            return None

        url = f"{self.base_url}/rxcui.json"
        params = {"name": clean_name, "allsrc": "0", "srclist": "RXNORM"}

        try:
            if client:
                resp = await client.get(url, params=params, timeout=self.timeout)
            else:
                async with httpx.AsyncClient() as http_client:
                    resp = await http_client.get(url, params=params, timeout=self.timeout)

            if resp.status_code != 200:
                return None

            data = resp.json()
            id_group = data.get("idGroup", {})
            rxnorm_ids = id_group.get("rxnormId", [])
            if rxnorm_ids and len(rxnorm_ids) > 0:
                return str(rxnorm_ids[0])
            return None
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError):
            raise
        except Exception as e:
            logger.warning("[RxNormService] Error fetching rxcui for '%s': %s", clean_name, e)
            return None

    async def get_concept_properties(self, rxcui: str, client: Optional[httpx.AsyncClient] = None) -> Optional[RxNormConcept]:
        """Lấy thuộc tính chi tiết của RxCUI (properties.json)."""
        if not rxcui:
            return None

        url = f"{self.base_url}/rxcui/{rxcui}/properties.json"
        try:
            if client:
                resp = await client.get(url, timeout=self.timeout)
            else:
                async with httpx.AsyncClient() as http_client:
                    resp = await http_client.get(url, timeout=self.timeout)

            if resp.status_code != 200:
                return None

            data = resp.json()
            props = data.get("properties", {})
            if not props:
                return None

            return RxNormConcept(
                rxcui=str(props.get("rxcui", rxcui)),
                name=props.get("name", ""),
                tty=props.get("tty", ""),
                synonym=props.get("synonym", ""),
                active_ingredient=props.get("name", "") if props.get("tty") in ("IN", "PIN", "MIN") else None,
                provenance="rxnorm",
                confidence_score=1.0 if props.get("tty") in ("IN", "PIN", "BN", "SCD", "SBD") else 0.85,
            )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError):
            raise
        except Exception as e:
            logger.warning("[RxNormService] Error fetching properties for rxcui '%s': %s", rxcui, e)
            return None

    async def get_approximate_terms(
        self,
        term: str,
        max_entries: int = 5,
        client: Optional[httpx.AsyncClient] = None,
    ) -> List[Dict[str, Any]]:
        """Tra cứu approximate terms từ RxNav (approximateTerm.json)."""
        clean_term = self._clean_query(term)
        if not clean_term:
            return []

        url = f"{self.base_url}/approximateTerm.json"
        params = {"term": clean_term, "maxEntries": str(max_entries)}

        try:
            if client:
                resp = await client.get(url, params=params, timeout=self.timeout)
            else:
                async with httpx.AsyncClient() as http_client:
                    resp = await http_client.get(url, params=params, timeout=self.timeout)

            if resp.status_code != 200:
                return []

            data = resp.json()
            approx_group = data.get("approximateGroup", {})
            candidates = approx_group.get("candidate", [])
            return candidates if isinstance(candidates, list) else []
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError):
            raise
        except Exception as e:
            logger.warning("[RxNormService] Error fetching approximateTerm for '%s': %s", clean_term, e)
            return []

    async def get_related_ingredients(
        self,
        rxcui: str,
        client: Optional[httpx.AsyncClient] = None,
    ) -> List[RxNormConcept]:
        """
        [Official RxNav Traversal API]
        Tra cứu mối quan hệ phân cấp từ Brand/Drug CUI (BN, SBD, SCD) sang Active Ingredient(s) (IN, PIN, MIN).
        URL: https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/allrelated.json
        """
        if not rxcui:
            return []

        url = f"{self.base_url}/rxcui/{rxcui}/allrelated.json"
        try:
            if client:
                resp = await client.get(url, timeout=self.timeout)
            else:
                async with httpx.AsyncClient() as http_client:
                    resp = await http_client.get(url, timeout=self.timeout)

            if resp.status_code != 200:
                return []

            data = resp.json()
            groups = data.get("allRelatedGroup", {}).get("conceptGroup", [])
            ingredients: List[RxNormConcept] = []

            for g in groups:
                tty = g.get("tty", "")
                if tty in ("IN", "PIN", "MIN"):
                    concepts = g.get("conceptProperties", [])
                    for c in concepts:
                        c_rxcui = str(c.get("rxcui", ""))
                        c_name = str(c.get("name", ""))
                        if c_rxcui and c_name:
                            ingredients.append(
                                RxNormConcept(
                                    rxcui=c_rxcui,
                                    name=c_name,
                                    tty=tty,
                                    synonym=c.get("synonym"),
                                    active_ingredient=c_name,
                                    active_ingredients=[c_name],
                                    provenance="rxnorm_traversal",
                                    confidence_score=1.0 if tty in ("IN", "PIN") else 0.9,
                                )
                            )
            return ingredients
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError):
            raise
        except Exception as e:
            logger.warning("[RxNormService] Error fetching related ingredients for rxcui '%s': %s", rxcui, e)
            return []

    async def resolve_multi_rxcui(
        self,
        rxcuis: List[str],
        client: Optional[httpx.AsyncClient] = None,
    ) -> List[str]:
        """
        [Multi-RxCUI Resolution]
        Khi OpenFDA hoặc RxNav trả về nhiều RxCUIs khác nhau (ví dụ các SBD của các hàm lượng khác nhau),
        hàm này duyệt traversal về các IN (Canonical Ingredient) chung nhất và loại bỏ trùng lặp.
        """
        if not rxcuis:
            return []

        unique_ingredients: set[str] = set()
        for rc in rxcuis[:4]:  # Giới hạn 4 CUI đại diện
            try:
                ings = await self.get_related_ingredients(str(rc), client=client)
                for ing in ings:
                    if ing.name:
                        unique_ingredients.add(ing.name.lower())
            except Exception as e:
                logger.debug("[RxNormService] Error in multi-rxcui resolution for %s: %s", rc, e)
                continue

        return sorted(list(unique_ingredients))

    async def resolve_drug(
        self,
        query: str,
        client: Optional[httpx.AsyncClient] = None,
    ) -> RxNormResolutionResult:
        """
        Phân giải danh tính thuốc theo chuẩn Primary Normalization Authority:
        1. Exact Match -> Tự động duyệt allrelated.json lấy active_ingredient -> RESOLVED
        2. Approximate Match:
           - 1 candidate vượt ngưỡng tin cậy -> Tự động duyệt allrelated.json -> RESOLVED
           - Nhiều candidate hoặc điểm trung bình -> CANDIDATE_REQUIRES_REVIEW
        3. Không tìm thấy -> UNRESOLVED (data absent)
        4. Mạng lỗi / Timeout -> SOURCE_UNAVAILABLE (infrastructure issue)
        """
        raw_query = (query or "").strip()
        if not raw_query:
            return RxNormResolutionResult(
                status=NormalizationStatus.UNRESOLVED,
                query_term=query,
                error_message="Query term rỗng",
            )

        # Kiểm tra Cache
        cache_key = raw_query.lower()
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # 1. Tra cứu chính xác
            exact_rxcui = await self.get_rxcui_by_name(raw_query, client=client)
            if exact_rxcui:
                props = await self.get_concept_properties(exact_rxcui, client=client)
                if props:
                    # Nếu là Brand (BN) hoặc SBD/SCD, tra cứu quan hệ để lấy Active Ingredient
                    if not props.active_ingredient and props.tty in ("BN", "SBD", "SCD"):
                        rel_ings = await self.get_related_ingredients(props.rxcui, client=client)
                        if rel_ings:
                            props.active_ingredients = [ing.name for ing in rel_ings]
                            props.active_ingredient = " / ".join(props.active_ingredients)

                    res = RxNormResolutionResult(
                        status=NormalizationStatus.RESOLVED,
                        query_term=raw_query,
                        concept=props,
                    )
                    self._cache[cache_key] = res
                    return res

            # 2. Tra cứu approximate terms
            approx_candidates = await self.get_approximate_terms(raw_query, max_entries=4, client=client)
            if approx_candidates:
                parsed_candidates: List[RxNormConcept] = []
                for cand in approx_candidates:
                    c_rxcui = str(cand.get("rxcui", ""))
                    c_name = cand.get("name") or cand.get("rxaui", "")
                    if c_rxcui:
                        parsed_candidates.append(
                            RxNormConcept(
                                rxcui=c_rxcui,
                                name=str(c_name),
                                tty="APPROX",
                                provenance="rxnorm_approximate",
                                confidence_score=0.75,
                            )
                        )

                if parsed_candidates:
                    first_score = float(approx_candidates[0].get("score", 0.0))
                    if len(parsed_candidates) == 1 or first_score >= 8.0:
                        best_props = await self.get_concept_properties(parsed_candidates[0].rxcui, client=client)
                        if best_props:
                            best_props.confidence_score = 0.85
                            best_props.provenance = "rxnorm_approximate"
                            if not best_props.active_ingredient and best_props.tty in ("BN", "SBD", "SCD"):
                                rel_ings = await self.get_related_ingredients(best_props.rxcui, client=client)
                                if rel_ings:
                                    best_props.active_ingredients = [ing.name for ing in rel_ings]
                                    best_props.active_ingredient = " / ".join(best_props.active_ingredients)

                            res = RxNormResolutionResult(
                                status=NormalizationStatus.RESOLVED,
                                query_term=raw_query,
                                concept=best_props,
                                candidates=parsed_candidates,
                            )
                            self._cache[cache_key] = res
                            return res

                    # Nhiều candidate ambiguous -> CANDIDATE_REQUIRES_REVIEW (chống auto-accept)
                    res = RxNormResolutionResult(
                        status=NormalizationStatus.CANDIDATE_REQUIRES_REVIEW,
                        query_term=raw_query,
                        candidates=parsed_candidates,
                        error_message="Phát hiện nhiều candidate ambiguous từ RxNav, cần người dùng xác nhận",
                    )
                    self._cache[cache_key] = res
                    return res

            # 3. Không tìm thấy (HTTP 200 nhưng 0 candidate)
            res = RxNormResolutionResult(
                status=NormalizationStatus.UNRESOLVED,
                query_term=raw_query,
                error_message="Không tìm thấy concept tương ứng trong RxNorm",
            )
            self._cache[cache_key] = res
            return res

        except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
            logger.error("[RxNormService] Network/Timeout error connecting to RxNav: %s", e)
            return RxNormResolutionResult(
                status=NormalizationStatus.SOURCE_UNAVAILABLE,
                query_term=raw_query,
                error_message=f"Lỗi kết nối tới dịch vụ RxNav: {type(e).__name__}",
            )
        except Exception as e:
            logger.error("[RxNormService] Unexpected error in resolve_drug: %s", e)
            return RxNormResolutionResult(
                status=NormalizationStatus.SOURCE_UNAVAILABLE,
                query_term=raw_query,
                error_message=str(e),
            )


rxnorm_service = RxNormService()
