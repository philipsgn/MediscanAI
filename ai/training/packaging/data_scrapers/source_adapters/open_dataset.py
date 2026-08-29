"""Adapter for a local, downloaded/open dataset manifest."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from .base import Image, read_manifest


class OpenDatasetAdapter:
    """Yield only files enumerated by a local JSONL manifest."""

    def __init__(self, manifest: Path) -> None:
        self.manifest = manifest

    def items(self) -> Iterator[Image]:
        for item in read_manifest(self.manifest):
            if item.uri.startswith(("http://", "https://")):
                raise ValueError(f"Open dataset manifest must contain local files: {item.uri}")
            path = Path(item.uri).expanduser()
            if not path.is_file():
                raise FileNotFoundError(path)
            yield item
