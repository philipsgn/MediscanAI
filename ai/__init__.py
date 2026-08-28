"""
MediScan AI Subsystem — Pure-ONNX OCR & 4-Layer Clinical Engine.
"""

from ai.configs.ocr_config import OCRConfig, default_ocr_config
from ai.pipelines.preprocessor import ImagePreprocessor, default_preprocessor
from ai.pipelines.clinical_ner_parser import ClinicalNERParser, default_ner_parser
from ai.pipelines.onnx_ocr_engine import ONNXOCREngine, default_onnx_ocr_engine
from ai.normalization.fuzzy_matcher import FuzzyMatcher, default_fuzzy_matcher
from ai.normalization.drug_mapper import DrugMapper, default_drug_mapper
from ai.clinical_evaluator.rule_engine import ClinicalRuleEngine, default_clinical_rule_engine

__all__ = [
    "OCRConfig",
    "default_ocr_config",
    "ImagePreprocessor",
    "default_preprocessor",
    "ClinicalNERParser",
    "default_ner_parser",
    "ONNXOCREngine",
    "default_onnx_ocr_engine",
    "FuzzyMatcher",
    "default_fuzzy_matcher",
    "DrugMapper",
    "default_drug_mapper",
    "ClinicalRuleEngine",
    "default_clinical_rule_engine",
]
