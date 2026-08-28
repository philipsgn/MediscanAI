"""
OCR & AI Subsystem Configurations for MediScan AI.
Pure-ONNX Runtime (CPU-optimized) Settings.
"""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class OCRConfig:
    # Image Preprocessing
    max_dim: int = 1600
    enable_clahe: bool = True
    clahe_clip_limit: float = 2.0
    clahe_tile_grid_size: tuple = (8, 8)
    enable_deskew: bool = True
    enable_denoise: bool = True

    # Inference & ONNX Runtime
    onnx_num_threads: int = 4
    confidence_threshold: float = 0.40
    ocr_lang: str = "vi"

    # Fuzzy String Matching & Clinical NER
    similarity_threshold: float = 0.70
    min_word_length: int = 3

    # Default Clinical Time Slots
    default_slot_times: dict = field(default_factory=lambda: {
        "morning": "08:00",
        "noon": "12:00",
        "afternoon": "17:00",
        "evening": "21:00"
    })

    # Paths
    base_dir: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir: str = os.path.join(base_dir, "data")
    models_dir: str = os.path.join(base_dir, "models")
    drug_dict_path: str = os.path.join(data_dir, "drug_dictionary.json")
    clinical_rules_path: str = os.path.join(data_dir, "clinical_rules.json")


# Global default configuration instance
default_ocr_config = OCRConfig()
