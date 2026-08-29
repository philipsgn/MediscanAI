# Packaging Data Pipeline

This directory contains the ingestion, annotation, merge, split, and validation
pipeline for medicine packaging images. It is independent of the runtime
backend/frontend.

## Safety and provenance

- Sources are never searched or crawled. Local images must be listed in a JSONL
  manifest; web images must be listed in a JSONL manifest and use HTTPS.
- Web hosts are explicitly allowlisted at invocation time. `robots.txt` is
  checked and a configurable delay is applied between requests.
- Each accepted image is validated, SHA-256 hashed, perceptually hashed, and
  recorded in `metadata.jsonl`. `--resume` skips previously accepted records.
- OCR is local only. `pytesseract` is optional; without it annotations are
  emitted with `engine: unavailable`, zero OCR confidence, and `needs_review`.
  No commercial vision API is supported.

## Manifests and commands

Manifest entries are JSONL, for example:

```json
{"source_id":"box-001","uri":"/data/box-001.jpg","group_id":"product-001"}
```

From the repository root:

```text
python ai/training/packaging/data_scrapers/scrape_pharmacy_images.py --manifest manifest.jsonl --limit-drugs 20 --max-images-per-drug 10 --resume
python ai/training/packaging/annotation/auto_annotate_real.py --metadata ai/training/packaging/datasets/metadata/real.jsonl --output ai/training/packaging/datasets/annotated_real
python ai/training/packaging/annotation/validate_annotations.py ai/training/packaging/datasets/annotated_real/annotations.jsonl --output-root ai/training/packaging/datasets/annotated_real
python ai/training/packaging/scripts/merge_dataset.py --real ai/training/packaging/datasets/annotated_real --synthetic ai/training/packaging/datasets/annotated_synthetic --output ai/training/packaging/datasets/final --report reports/merge.json
python ai/training/packaging/scripts/split_dataset.py --source ai/training/packaging/datasets/final --output ai/training/packaging/datasets/final --metadata ai/training/packaging/datasets/metadata/real.jsonl
python ai/training/packaging/scripts/build_dataset.py --root ai/training/packaging/datasets/final --report reports/final.json
```

The scripts also work when invoked directly from their own directory. Training
labels remain standard YOLO text labels with classes `brand_name`,
`active_ingredient`, and `strength`.
