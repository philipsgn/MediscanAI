"""Image validation, content hashing, perceptual deduplication, and JSONL IO."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_image(path: Path, min_width: int = 640, min_height: int = 640, max_bytes: int = 25_000_000) -> tuple[int, int, str]:
    if path.suffix.lower() not in IMAGE_EXTENSIONS or not path.is_file() or path.stat().st_size > max_bytes:
        raise ValueError(f"Unsupported, missing, or oversized image: {path}")
    try:
        from PIL import Image
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
            fmt = image.format or path.suffix[1:].upper()
    except ImportError:
        data = path.read_bytes()[:16]
        width, height, fmt = 0, 0, "unknown"
        if data.startswith(b"\xff\xd8"):
            fmt = "JPEG"
        elif data.startswith(b"\x89PNG"):
            fmt = "PNG"
    except (OSError, ValueError) as exc:
        raise ValueError(f"Unreadable image: {path}") from exc
    if width and (width < min_width or height < min_height):
        raise ValueError(f"Image is smaller than {min_width}x{min_height}: {path}")
    return width, height, fmt


def perceptual_hash(path: Path, size: int = 16) -> str:
    """Average hash; deliberately dependency-light and stable across formats."""
    from PIL import Image
    with Image.open(path) as image:
        pixels = list(image.convert("L").resize((size, size)).getdata())
    average = sum(pixels) / len(pixels)
    return "".join("1" if pixel >= average else "0" for pixel in pixels)


def hamming_distance(left: str, right: str) -> int:
    return sum(a != b for a, b in zip(left, right)) + abs(len(left) - len(right))


def write_jsonl(path: Path, records: Iterable[dict[str, Any]], append: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
