"""Conservative dictionary matching for OCR text."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from typing import Any


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def load_dictionary(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("drugs", data) if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise ValueError("Drug dictionary must contain a list or a 'drugs' list")
    return [entry for entry in entries if isinstance(entry, dict)]


def match_text(text: str, dictionary: list[dict[str, Any]], threshold: float = 0.62) -> dict[str, Any] | None:
    normalized = normalize_text(text)
    if not normalized:
        return None
    best: tuple[float, dict[str, Any]] | None = None
    for entry in dictionary:
        candidates = [normalize_text(str(entry.get(field, ""))) for field in ("brand_name", "active_ingredient", "strength")]
        candidates = [candidate for candidate in candidates if candidate]
        if not candidates:
            continue
        score = max(SequenceMatcher(None, normalized, candidate).ratio() for candidate in candidates)
        if best is None or score > best[0]:
            best = (score, entry)
    if best is None or best[0] < threshold:
        return None
    return {"match": best[1], "score": round(best[0], 4)}
