"""
dataset_validator.py

Clinical Knowledge Dataset Governance & Quality Validator (Stage 12).
Thực hiện kiểm định độc lập, chặt chẽ tính toàn vẹn của CSDL DDI theo các quy tắc:
1. JSON schema parseability & metadata completeness.
2. Required fields, uniqueness của ddinter_id.
3. No self-pairs (drug_a == drug_b).
4. No duplicate symmetric pairs (frozenset uniqueness).
5. Valid severity values (HIGH / MEDIUM / LOW).
6. SHA256 checksum consistency with manifest.json.
7. Safe rollback validation (target file must physically exist and be validated).
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    is_valid: bool
    total_pairs_checked: int = 0
    total_ingredients_checked: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checksum: str = ""


class DatasetValidator:
    """Validator kiểm định chất lượng và tính toàn vẹn CSDL tri thức tương tác thuốc."""

    VALID_SEVERITIES = {"HIGH", "MEDIUM", "LOW"}
    REQUIRED_METADATA_FIELDS = {"dataset_name", "dataset_version", "license"}
    REQUIRED_INTERACTION_FIELDS = {
        "ddinter_id",
        "drug_a",
        "drug_b",
        "severity",
        "mechanism",
        "management",
        "recommendation",
    }

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Tính mã băm SHA256 của file."""
        if not file_path.exists():
            return ""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def validate_file(self, data_path: Path, manifest_path: Optional[Path] = None) -> ValidationResult:
        """Kiểm định toàn diện tệp dataset JSON và đối chiếu với manifest (nếu có)."""
        errors: List[str] = []
        warnings: List[str] = []

        if not data_path.exists():
            return ValidationResult(
                is_valid=False,
                errors=[f"Dataset file not found at: {data_path}"],
            )

        # 1. Parse JSON
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Failed to parse JSON file {data_path}: {e}"],
            )

        if not isinstance(raw_data, dict):
            return ValidationResult(
                is_valid=False,
                errors=["Top-level JSON structure must be an object (dict)."],
            )

        # 2. Validate Metadata
        metadata = raw_data.get("metadata")
        if not metadata or not isinstance(metadata, dict):
            errors.append("Missing or invalid 'metadata' section in dataset.")
        else:
            for req_field in self.REQUIRED_METADATA_FIELDS:
                if not metadata.get(req_field):
                    errors.append(f"Metadata missing required field: '{req_field}'")

        # 3. Validate Interactions
        interactions = raw_data.get("interactions")
        if interactions is None or not isinstance(interactions, list):
            errors.append("Missing or invalid 'interactions' array in dataset.")
            return ValidationResult(is_valid=False, errors=errors)

        seen_ids: Set[str] = set()
        seen_pairs: Set[frozenset[str]] = set()
        unique_ingredients: Set[str] = set()

        for idx, item in enumerate(interactions):
            if not isinstance(item, dict):
                errors.append(f"Interaction at index {idx} is not a valid JSON object.")
                continue

            # Check required fields
            for rf in self.REQUIRED_INTERACTION_FIELDS:
                val = item.get(rf)
                if val is None or str(val).strip() == "":
                    errors.append(f"Interaction at index {idx} (ID: {item.get('ddinter_id', 'unknown')}) missing field '{rf}'.")

            # Check ID uniqueness
            ddinter_id = str(item.get("ddinter_id", "")).strip()
            if ddinter_id:
                if ddinter_id in seen_ids:
                    errors.append(f"Duplicate ddinter_id detected: '{ddinter_id}'.")
                seen_ids.add(ddinter_id)

            # Check severity
            sev = str(item.get("severity", "")).strip().upper()
            if sev not in self.VALID_SEVERITIES:
                errors.append(f"Interaction '{ddinter_id}' has invalid severity '{sev}' (must be HIGH/MEDIUM/LOW).")

            # Check drugs
            drug_a = str(item.get("drug_a", "")).strip().lower()
            drug_b = str(item.get("drug_b", "")).strip().lower()

            if not drug_a or not drug_b:
                errors.append(f"Interaction '{ddinter_id}' has empty drug_a or drug_b.")
                continue

            # No self-pairs
            if drug_a == drug_b:
                errors.append(f"Self-pair detected in interaction '{ddinter_id}': drug_a == drug_b == '{drug_a}'.")

            # Symmetry / duplicate normalized pairs
            pair_key = frozenset([drug_a, drug_b])
            if pair_key in seen_pairs:
                errors.append(f"Duplicate interaction pair detected: '{drug_a}' + '{drug_b}'.")
            seen_pairs.add(pair_key)

            unique_ingredients.add(drug_a)
            unique_ingredients.add(drug_b)

        # 4. Checksum
        computed_checksum = self.compute_sha256(data_path)

        # 5. Manifest reconciliation (if manifest provided)
        if manifest_path and manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                active_meta = manifest.get("active_dataset", {})
                expected_sha = active_meta.get("sha256", "")
                if expected_sha and expected_sha != computed_checksum:
                    errors.append(
                        f"Checksum mismatch: Manifest expects '{expected_sha}', but actual file SHA256 is '{computed_checksum}'."
                    )
            except Exception as e:
                warnings.append(f"Could not read manifest at {manifest_path}: {e}")

        is_valid = len(errors) == 0
        return ValidationResult(
            is_valid=is_valid,
            total_pairs_checked=len(seen_pairs),
            total_ingredients_checked=len(unique_ingredients),
            errors=errors,
            warnings=warnings,
            checksum=computed_checksum,
        )

    def validate_rollback_target(self, target_version: str, data_dir: Path) -> ValidationResult:
        """
        Kiểm tra mục tiêu rollback:
        Tuân thủ nguyên tắc: Rollback target must physically exist and pass validation before selection.
        """
        target_filename = f"ddinter_interactions_v{target_version}.json"
        target_path = data_dir / target_filename
        if not target_path.exists():
            return ValidationResult(
                is_valid=False,
                errors=[
                    f"Rollback target version '{target_version}' is NOT AVAILABLE: file '{target_filename}' does not physically exist on disk."
                ],
            )
        return self.validate_file(target_path)


dataset_validator = DatasetValidator()
