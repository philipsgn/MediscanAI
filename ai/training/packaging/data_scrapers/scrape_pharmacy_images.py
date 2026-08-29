"""Ingest explicitly listed medicine-package images; never search or crawl."""
from __future__ import annotations

import argparse
import json
import shutil
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

if __package__ in (None, ""):
    from ai.training.packaging.data_scrapers.source_adapters.base import Image
    from ai.training.packaging.data_scrapers.source_adapters.open_dataset import OpenDatasetAdapter
    from ai.training.packaging.data_scrapers.source_adapters.permitted_web_source import PermittedWebSourceAdapter
    from ai.training.packaging.data_scrapers.utils import hamming_distance, perceptual_hash, sha256_file, validate_image
else:
    from .source_adapters.base import Image
    from .source_adapters.open_dataset import OpenDatasetAdapter
    from .source_adapters.permitted_web_source import PermittedWebSourceAdapter
    from .utils import hamming_distance, perceptual_hash, sha256_file, validate_image


def _download(uri: str, destination: Path, timeout: float, retries: int) -> None:
    for attempt in range(retries + 1):
        try:
            if uri.startswith("https://"):
                request = urllib.request.Request(uri, headers={"User-Agent": "MediscanPackagingDataset/1.0"})
                with urllib.request.urlopen(request, timeout=timeout) as response, destination.open("wb") as target:
                    shutil.copyfileobj(response, target)
            else:
                shutil.copyfile(Path(uri).expanduser(), destination)
            return
        except (OSError, urllib.error.URLError):
            if attempt >= retries:
                raise
            time.sleep(min(30.0, 2.0 ** attempt))


def ingest(images: Iterable[Image], output: Path, metadata: Path, *, limit_drugs: int | None = None, max_images_per_drug: int | None = None, resume: bool = False, timeout: float = 30.0, retries: int = 2, phash_threshold: int = 4) -> dict[str, int]:
    output.mkdir(parents=True, exist_ok=True)
    completed: set[str] = set()
    hashes: set[str] = set()
    perceptual: list[str] = []
    per_drug: dict[str, int] = {}
    if resume and metadata.exists():
        for line in metadata.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line); completed.add(record["image_id"]); hashes.add(record["sha256"]); perceptual.append(record["perceptual_hash"]); per_drug[record["drug_id"]] = per_drug.get(record["drug_id"], 0) + 1
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    allowed_drugs: set[str] | None = None
    items = list(images)
    if limit_drugs is not None:
        allowed_drugs = set()
        for image in items:
            allowed_drugs.add(image.product.drug_id)
            if len(allowed_drugs) >= max(0, limit_drugs): break
    counts = {"accepted": 0, "duplicates": 0, "invalid": 0, "skipped": 0}
    metadata.parent.mkdir(parents=True, exist_ok=True)
    with metadata.open("a" if resume else "w", encoding="utf-8") as handle:
        for image in items:
            drug_id = image.product.drug_id
            if image.image_id in completed or (allowed_drugs is not None and drug_id not in allowed_drugs) or (max_images_per_drug is not None and per_drug.get(drug_id, 0) >= max_images_per_drug):
                counts["skipped"] += 1; continue
            destination = output / f"{image.image_id}{Path(image.uri).suffix.lower() or '.jpg'}"
            try:
                _download(image.uri, destination, timeout, retries)
                width, height, image_format = validate_image(destination)
                digest, image_phash = sha256_file(destination), perceptual_hash(destination)
                if digest in hashes or any(hamming_distance(image_phash, old) <= phash_threshold for old in perceptual):
                    destination.unlink(missing_ok=True); counts["duplicates"] += 1; continue
                timestamp = datetime.now(timezone.utc).isoformat()
                record = {"image_id": image.image_id, "filename": destination.name, "path": str(destination), "drug_id": drug_id, "brand_name": image.product.brand_name, "active_ingredient": image.product.active_ingredient, "strength": image.product.strength, "group_id": image.group_id or drug_id, "source_name": image.source_name, "source_url": image.source_url, "license": image.license, "timestamp": timestamp, "download_timestamp": timestamp, "sha256": digest, "perceptual_hash": image_phash, "width": width, "height": height, "format": image_format}
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"); handle.flush()
                hashes.add(digest); perceptual.append(image_phash); per_drug[drug_id] = per_drug.get(drug_id, 0) + 1; counts["accepted"] += 1
            except (OSError, ValueError, urllib.error.URLError):
                destination.unlink(missing_ok=True); counts["invalid"] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True); parser.add_argument("--output", type=Path, default=Path("ai/training/packaging/datasets/raw_real_images")); parser.add_argument("--metadata", type=Path, default=Path("ai/training/packaging/datasets/metadata/real.jsonl")); parser.add_argument("--source", choices=("local", "web"), default="local"); parser.add_argument("--permitted-host", action="append", default=[]); parser.add_argument("--limit-drugs", type=int); parser.add_argument("--max-images-per-drug", type=int); parser.add_argument("--timeout", type=float, default=30.0); parser.add_argument("--retries", type=int, default=2); parser.add_argument("--rate-limit", type=float, default=2.0); parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    adapter = OpenDatasetAdapter(args.manifest) if args.source == "local" else PermittedWebSourceAdapter(args.manifest, set(args.permitted_host), "MediscanPackagingDataset/1.0", args.rate_limit)
    print(json.dumps(ingest(adapter.items(), args.output, args.metadata, limit_drugs=args.limit_drugs, max_images_per_drug=args.max_images_per_drug, resume=args.resume, timeout=args.timeout, retries=args.retries), sort_keys=True))


if __name__ == "__main__": main()
