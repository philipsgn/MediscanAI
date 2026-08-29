"""Common source adapter contracts.

Adapters never discover sites. Every item must come from a local manifest or a
URL explicitly listed in configuration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Mapping, Protocol


@dataclass(frozen=True)
class Product:
    """Canonical product data carried by every source adapter."""

    drug_id: str
    brand_name: str
    active_ingredient: list[str] = field(default_factory=list)
    strength: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Image:
    """An explicitly enumerated image and its provenance."""

    image_id: str
    uri: str
    product: Product
    source_name: str
    source_url: str
    license: str
    group_id: str | None = None


# Kept as a small input compatibility record for callers of the first draft.
@dataclass(frozen=True)
class SourceItem:
    source_id: str
    uri: str
    group_id: str | None = None
    metadata: Mapping[str, str] | None = None


class BaseSourceAdapter:
    """Safe adapter contract; implementations must use explicitly enumerated items."""

    def search_products(self, query: str) -> Iterator[Product]:
        raise NotImplementedError

    def get_product_metadata(self, product: Product) -> Mapping[str, Any]:
        raise NotImplementedError

    def download_image(self, image_url: str, output_path: Path) -> Path:
        raise NotImplementedError


class SourceAdapter(Protocol):
    def items(self) -> Iterator[SourceItem]: ...


def read_manifest(path: Path) -> Iterator[Image]:
    """Read JSONL manifest entries; blank lines and comments are ignored."""
    import json

    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            try:
                value = json.loads(text)
                uri = str(value["uri"])
                image_id = str(value.get("image_id", value.get("source_id", f"{path.stem}:{line_number}")))
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise ValueError(f"Invalid manifest entry {path}:{line_number}") from exc
            ingredients = value.get("active_ingredient", value.get("active_ingredients", []))
            strengths = value.get("strength", value.get("strengths", []))
            if isinstance(ingredients, str): ingredients = [ingredients]
            if isinstance(strengths, str): strengths = [strengths]
            product = Product(str(value.get("drug_id", image_id)), str(value.get("brand_name", "")), list(ingredients or []), list(strengths or []))
            yield Image(image_id, uri, product, str(value.get("source_name", path.stem)), str(value.get("source_url", uri)), str(value.get("license", "unknown")), value.get("group_id") or product.drug_id)
