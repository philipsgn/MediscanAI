"""
Unit tests for AI Image Preprocessing pipeline.
Verifies downscale, CLAHE, denoise, deskew, and full preprocess execution.
"""

import numpy as np
import pytest
from ai.pipelines.preprocessor import ImagePreprocessor


@pytest.fixture
def sample_image() -> np.ndarray:
    """Tạo một bức ảnh tổng hợp 2000x1200 BGR có nội dung gradient để test."""
    img = np.zeros((2000, 1200, 3), dtype=np.uint8)
    img[100:1900, 100:1100] = 200  # Vùng sáng
    return img


def test_downscale_preserves_aspect_ratio(sample_image):
    preprocessor = ImagePreprocessor(max_dim=1600)
    resized = preprocessor.downscale(sample_image, max_dim=1600)
    
    assert max(resized.shape[:2]) <= 1600
    assert resized.shape[0] == 1600  # Chiều cao ban đầu 2000 downscale về 1600
    assert resized.shape[1] == 960   # Chiều rộng 1200 * (1600/2000) = 960


def test_clahe_contrast_enhancement(sample_image):
    preprocessor = ImagePreprocessor()
    clahe_img = preprocessor.apply_clahe(sample_image)
    
    assert clahe_img is not None
    assert clahe_img.shape == sample_image.shape
    assert clahe_img.dtype == np.uint8


def test_bilateral_denoise(sample_image):
    preprocessor = ImagePreprocessor()
    denoised = preprocessor.denoise(sample_image)
    
    assert denoised is not None
    assert denoised.shape == sample_image.shape


def test_deskew_and_rotation(sample_image):
    preprocessor = ImagePreprocessor()
    angle = preprocessor.detect_skew_angle(sample_image)
    assert isinstance(angle, float)
    
    rotated = preprocessor.rotate_image(sample_image, 15.0)
    assert rotated is not None
    assert rotated.shape[0] > 0 and rotated.shape[1] > 0


def test_full_preprocessing_pipeline(sample_image):
    preprocessor = ImagePreprocessor(max_dim=1000)
    processed, meta = preprocessor.preprocess(sample_image, source_type="prescription")
    
    assert processed is not None
    assert max(processed.shape[:2]) <= 1000
    assert meta["original_height"] == 2000
    assert meta["original_width"] == 1200
    assert meta["source_type"] == "prescription"
