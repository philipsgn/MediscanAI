"""Generate synthetic medicine-package images and YOLO text labels.

Each sample contains one package with three independently labelled text regions:
brand name, active ingredient, and strength.  The same perspective matrix is
applied to the image and all boxes, so labels remain geometrically consistent.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path
from typing import Final

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import albumentations as A
except ImportError as exc:  # pragma: no cover - exercised in environment setup
    raise RuntimeError("Install albumentations to generate packaging data") from exc

LOGGER = logging.getLogger(__name__)
SIZE: Final[int] = 640
CLASS_NAMES: Final[tuple[str, ...]] = ("brand_name", "active_ingredient", "strength")
ROOT = Path(__file__).resolve().parents[4]
DICTIONARY = ROOT / "ai" / "data" / "drug_dictionary.json"
FONT_CANDIDATES: Final[tuple[Path, ...]] = (
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("C:/Windows/Fonts/calibrib.ttf"),
)


def _load_drugs() -> list[dict[str, str]]:
    """Load validated display fields from the repository drug dictionary."""
    try:
        data = json.loads(DICTIONARY.read_text(encoding="utf-8"))
        drugs = data["drugs"]
        return [
            {
                "brand_name": str(drug["brand_name"]),
                "active_ingredient": str(drug["active_ingredient"]),
                "strength": str(drug["strength"]),
            }
            for drug in drugs
        ]
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Unable to read drug dictionary: {DICTIONARY}") from exc


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Return a bold system font, with Pillow's built-in fallback."""
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _clip_box(points: np.ndarray) -> tuple[int, int, int, int]:
    """Convert transformed corner points to a clipped xyxy integer box."""
    x_min, y_min = np.floor(points.min(axis=0)).astype(int)
    x_max, y_max = np.ceil(points.max(axis=0)).astype(int)
    return max(0, x_min), max(0, y_min), min(SIZE - 1, x_max), min(SIZE - 1, y_max)


def _perspective(image: np.ndarray, boxes: list[tuple[int, int, int, int]]) -> tuple[np.ndarray, list[tuple[int, int, int, int]]]:
    """Apply a mild camera perspective and transform each box with it."""
    margin = random.randint(8, 24)
    source = np.float32([[0, 0], [SIZE, 0], [SIZE, SIZE], [0, SIZE]])
    target = np.float32([[margin, 0], [SIZE - margin, random.randint(0, 16)],
                         [SIZE - random.randint(0, 16), SIZE - margin],
                         [0, SIZE - random.randint(0, 16)]])
    matrix = cv2.getPerspectiveTransform(source, target)
    warped = cv2.warpPerspective(image, matrix, (SIZE, SIZE), borderMode=cv2.BORDER_REFLECT)
    transformed: list[tuple[int, int, int, int]] = []
    for x1, y1, x2, y2 in boxes:
        corners = np.float32([[[x1, y1], [x2, y1], [x2, y2], [x1, y2]]])
        transformed.append(_clip_box(cv2.perspectiveTransform(corners, matrix)[0]))
    return warped, transformed


def _augment(image: np.ndarray, boxes: list[tuple[int, int, int, int]]) -> tuple[np.ndarray, list[tuple[int, int, int, int]]]:
    """Add phone-camera noise/glare through Albumentations without moving boxes."""
    transform = A.Compose(
        [A.GaussNoise(std_range=(0.01, 0.04), p=0.7)],
        bbox_params=A.BboxParams(format="pascal_voc", label_fields=["labels"], min_visibility=0.0),
    )
    result = transform(image=image, bboxes=boxes, labels=[0, 1, 2])
    ordered = sorted(zip(result["labels"], result["bboxes"]), key=lambda item: item[0])
    return result["image"], [tuple(map(int, box)) for _, box in ordered]


def _sample(seed: int) -> tuple[np.ndarray, list[tuple[int, int, int, int]]]:
    """Render one package and return its image plus three xyxy boxes."""
    drug = random.choice(_load_drugs())
    image = Image.new("RGB", (SIZE, SIZE), tuple(random.randint(210, 250) for _ in range(3)))
    draw = ImageDraw.Draw(image, "RGBA")
    package = (random.randint(70, 120), random.randint(70, 120), random.randint(520, 570), random.randint(500, 560))
    draw.rounded_rectangle(package, radius=18, fill=(random.randint(30, 90), random.randint(100, 190), random.randint(150, 230), 255))
    draw.rectangle((package[0] + 18, package[1] + 18, package[2] - 18, package[3] - 18), outline=(255, 255, 255, 170), width=3)
    boxes: list[tuple[int, int, int, int]] = []
    colors = ((255, 255, 255, 255), (235, 245, 255, 255), (255, 220, 100, 255))
    font_sizes = (38, 25, 34)
    values = (drug["brand_name"].upper(), drug["active_ingredient"].upper(), drug["strength"])
    y = package[1] + 100
    for value, color, size in zip(values, colors, font_sizes):
        font = _font(size)
        bbox = draw.textbbox((0, 0), value, font=font, stroke_width=1)
        text_width = bbox[2] - bbox[0]
        x = package[0] + (package[2] - package[0] - text_width) // 2
        draw.text((x, y), value, font=font, fill=color, stroke_width=1, stroke_fill=(20, 40, 60, 230))
        boxes.append((x, y, x + text_width, y + bbox[3] - bbox[1]))
        y += size + 30
    # A translucent diagonal highlight models glossy plastic/cardboard glare.
    draw.ellipse((package[2] - 170, package[1] + 35, package[2] - 10, package[1] + 195), fill=(255, 255, 255, random.randint(25, 75)))
    array = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    array, boxes = _perspective(array, boxes)
    array, boxes = _augment(array, boxes)
    return array, boxes


def _write_sample(index: int, split: str, output_root: Path) -> None:
    image, boxes = _sample(index)
    image_path = output_root / "images" / split / f"packaging_{index:06d}.jpg"
    label_path = output_root / "labels" / split / f"packaging_{index:06d}.txt"
    cv2.imwrite(str(image_path), image, [cv2.IMWRITE_JPEG_QUALITY, 92])
    with label_path.open("w", encoding="ascii") as handle:
        for class_id, (x1, y1, x2, y2) in enumerate(boxes):
            x_center = ((x1 + x2) / 2) / SIZE
            y_center = ((y1 + y2) / 2) / SIZE
            width = (x2 - x1) / SIZE
            height = (y2 - y1) / SIZE
            handle.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")


def generate(num_train: int, num_val: int, output_root: Path) -> None:
    """Generate train/validation images and labels below ``output_root``."""
    if num_train < 0 or num_val < 0:
        raise ValueError("Sample counts must be non-negative")
    random.seed(20260828)
    np.random.seed(20260828)
    _load_drugs()
    for split, count, offset in (("train", num_train, 0), ("val", num_val, num_train)):
        (output_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_root / "labels" / split).mkdir(parents=True, exist_ok=True)
        for index in range(offset, offset + count):
            _write_sample(index, split, output_root)
    LOGGER.info("Generated %d train and %d val samples in %s", num_train, num_val, output_root)


def main() -> None:
    """Parse CLI options and generate a dataset."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-train", type=int, default=1000)
    parser.add_argument("--num-val", type=int, default=200)
    parser.add_argument("--output-root", type=Path, default=Path(__file__).resolve().parents[1] / "datasets")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        generate(args.num_train, args.num_val, args.output_root)
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
