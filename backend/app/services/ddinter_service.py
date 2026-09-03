"""
ddinter_service.py

DDInter Local Versioned Drug-Drug Interaction Knowledge Service (Stage 11/12).
Tuân thủ chuẩn on-premise dataset với provenance:
- Đọc dataset cục bộ: backend/app/data/ddinter_interactions.json
- Version Pin: 2.0 (CC BY-NC-SA 4.0)
- Zero Live External Dependency trong request path
- Tra cứu theo cặp hoạt chất canonical (frozenset)
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from app.schemas.ocr_schema import DatasetProvenanceInfo

logger = logging.getLogger(__name__)


class DDInterInteractionEntry(BaseModel):
    """Bản ghi tương tác thuốc trích xuất từ CSDL DDInter v2.0."""
    ddinter_id: str = Field(..., description="Unique ID trong CSDL DDInter (e.g. DDInter100101)")
    drug_a: str = Field(..., description="Hoạt chất canonical thứ nhất")
    drug_b: str = Field(..., description="Hoạt chất canonical thứ hai")
    severity: str = Field(..., description="Mức độ nghiêm trọng: HIGH / MEDIUM / LOW")
    mechanism: str = Field(..., description="Cơ chế tương tác dược lý / dược động học")
    management: str = Field(..., description="Khuyến cáo xử trí lâm sàng từ DDInter")
    recommendation: str = Field(..., description="Khuyến nghị hiển thị cho bệnh nhân")
    dataset_version: str = Field("2.0", description="Phiên bản dataset DDInter đã pin")
    source: str = Field("ddinter", description="Nguồn tri thức DDI")


class DDInterService:
    """Dịch vụ tra cứu tương tác thuốc On-Premise từ dataset DDInter."""

    def __init__(self, data_path: Optional[Path] = None, manifest_path: Optional[Path] = None) -> None:
        self.data_path = data_path or (
            Path(__file__).parent.parent / "data" / "ddinter_interactions.json"
        )
        self.manifest_path = manifest_path or (
            Path(__file__).parent.parent / "data" / "manifest.json"
        )
        self.dataset_metadata: Dict[str, Any] = {}
        self._interaction_map: Dict[frozenset[str], DDInterInteractionEntry] = {}
        self._covered_ingredients: Set[str] = set()
        self.integrity_verified: bool = False
        self._synonym_map: Dict[str, str] = {
            "acetylsalicylic acid": "aspirin",
            "paracetamol": "paracetamol",
            "acetaminophen": "paracetamol",
            "amoxil": "amoxicillin",
            "clavulanic acid": "clavulanate",
        }
        self.load_dataset()

    def load_dataset(self) -> None:
        """Đọc và lập chỉ mục CSDL DDInter kèm kiểm định tính toàn vẹn runtime."""
        self._interaction_map = {}
        self._covered_ingredients = set()
        self.integrity_verified = False

        if not self.data_path.exists():
            logger.error("[DDInterService] Dataset file not found at: %s", self.data_path)
            return

        # 1. Runtime Manifest & Checksum Validation (INV-12-05)
        if not self.manifest_path.exists():
            logger.error("[DDInterService] Manifest not found at: %s -> Failing closed", self.manifest_path)
            return

        try:
            with open(self.manifest_path, "r", encoding="utf-8") as mf:
                manifest_data = json.load(mf)
            active_meta = manifest_data.get("active_dataset", {})
            expected_sha = str(active_meta.get("sha256", "") or "").strip().lower()

            # Bắt buộc mã SHA256 phải là chuỗi hex hợp lệ 64 ký tự (không rỗng / None)
            if len(expected_sha) != 64:
                logger.error(
                    "[DDInterService] Manifest sha256 is missing, empty, or malformed ('%s') -> Failing closed",
                    expected_sha,
                )
                return

            actual_sha = self.calculate_checksum().lower()
            if actual_sha != expected_sha:
                logger.error(
                    "[DDInterService] CRITICAL: Checksum mismatch at runtime! Manifest=%s, Actual=%s -> Failing closed",
                    expected_sha,
                    actual_sha,
                )
                return

            self.integrity_verified = True
        except Exception as me:
            logger.error("[DDInterService] Could not parse manifest at runtime: %s -> Failing closed", me)
            return

        # 2. Parse dataset ONLY if integrity_verified is True
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            self.dataset_metadata = raw_data.get("metadata", {})
            version = self.dataset_metadata.get("dataset_version", "2.0")
            interactions = raw_data.get("interactions", [])

            indexed_count = 0
            ingredients_set: Set[str] = set()
            for item in interactions:
                drug_a = str(item.get("drug_a", "")).strip().lower()
                drug_b = str(item.get("drug_b", "")).strip().lower()
                if not drug_a or not drug_b:
                    continue

                entry = DDInterInteractionEntry(
                    ddinter_id=str(item.get("ddinter_id", "")),
                    drug_a=drug_a,
                    drug_b=drug_b,
                    severity=str(item.get("severity", "MEDIUM")).upper(),
                    mechanism=str(item.get("mechanism", "")),
                    management=str(item.get("management", "")),
                    recommendation=str(item.get("recommendation", "")),
                    dataset_version=version,
                    source="ddinter",
                )
                self._interaction_map[frozenset([drug_a, drug_b])] = entry
                ingredients_set.add(drug_a)
                ingredients_set.add(drug_b)
                indexed_count += 1

            self._covered_ingredients = ingredients_set

            logger.info(
                "[DDInterService] Successfully loaded DDInter v%s with %d interaction pairs (%d covered ingredients).",
                version,
                indexed_count,
                len(self._covered_ingredients),
            )
        except Exception as e:
            logger.error("[DDInterService] Failed to load DDInter dataset: %s -> Failing closed", e)
            self._interaction_map = {}
            self._covered_ingredients = set()
            self.integrity_verified = False

    def _normalize_name(self, name: str) -> str:
        """Chuẩn hóa tên hoạt chất theo synonym bridge nội bộ."""
        clean = (name or "").strip().lower()
        return self._synonym_map.get(clean, clean)

    def lookup_interaction(self, drug_a: str, drug_b: str) -> Optional[DDInterInteractionEntry]:
        """
        Tra cứu tương tác giữa 2 hoạt chất canonical:
        Không phân biệt thứ tự (frozenset).
        Khóa an toàn nếu integrity_verified is False.
        """
        if not self.integrity_verified:
            return None

        norm_a = self._normalize_name(drug_a)
        norm_b = self._normalize_name(drug_b)

        if not norm_a or not norm_b or norm_a == norm_b:
            return None

        key = frozenset([norm_a, norm_b])
        return self._interaction_map.get(key)

    def find_all_interactions(self, active_ingredients: List[str]) -> List[DDInterInteractionEntry]:
        """Tra cứu toàn bộ các cặp tương tác trong danh sách hoạt chất đưa vào."""
        if not self.integrity_verified or not active_ingredients or len(active_ingredients) < 2:
            return []

        cleaned_ings = list(dict.fromkeys(self._normalize_name(x) for x in active_ingredients if x))
        results: List[DDInterInteractionEntry] = []

        from itertools import combinations
        for ing_1, ing_2 in combinations(cleaned_ings, 2):
            entry = self.lookup_interaction(ing_1, ing_2)
            if entry:
                results.append(entry)

        return results

    def get_covered_ingredients(self) -> Set[str]:
        """Trả về tập hợp toàn bộ hoạt chất canonical có trong CSDL active (INV-12-03)."""
        if not self.integrity_verified:
            return set()
        return set(self._covered_ingredients)

    def is_drug_in_universe(self, canonical_ingredient: str) -> bool:
        """Xác định hoạt chất canonical có thuộc vũ trụ bao phủ của CSDL DDI hay không."""
        if not self.integrity_verified:
            return False
        norm = self._normalize_name(canonical_ingredient)
        return norm in self._covered_ingredients

    def calculate_checksum(self) -> str:
        """Tính mã băm SHA256 của tệp CSDL đang active trên đĩa."""
        if not self.data_path.exists():
            return ""
        try:
            sha256 = hashlib.sha256()
            with open(self.data_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.warning("[DDInterService] Failed to calculate checksum: %s", e)
            return ""

    def get_dataset_version_info(self) -> Dict[str, Any]:
        """Truy xuất metadata provenance của dataset DDInter."""
        return {
            "dataset_name": self.dataset_metadata.get("dataset_name", "DDInter"),
            "dataset_version": self.dataset_metadata.get("dataset_version", "2.0"),
            "license": self.dataset_metadata.get("license", "CC BY-NC-SA 4.0"),
            "total_pairs": len(self._interaction_map),
            "covered_ingredients_count": len(self._covered_ingredients),
            "sha256_checksum": self.calculate_checksum(),
        }

    def get_dataset_provenance(self) -> DatasetProvenanceInfo:
        """Khởi tạo Pydantic model DatasetProvenanceInfo phản ánh dữ liệu thực tế."""
        info = self.get_dataset_version_info()
        return DatasetProvenanceInfo(
            dataset_name=info["dataset_name"],
            active_version=info["dataset_version"],
            total_interaction_pairs=info["total_pairs"],
            covered_ingredients_count=info["covered_ingredients_count"],
            license=info["license"],
            sha256_checksum=info["sha256_checksum"],
        )


ddinter_service = DDInterService()

