"""
Unit tests cho OCR Model Lifecycle & Versioning (Stage 11 Architecture Gate).
Kiểm thử chi tiết:
1. Phân giải xác định (Deterministic Resolution) của Baseline model
2. Kiểm tra tính toàn vẹn và Fail-Fast khi artifact bị thiếu hoặc hỏng
3. Chặn hoàn toàn Silent Fallback khi cấu hình custom model bị lỗi
4. Phân tách tham số tối ưu giữa Stream A (Prescription) và Stream B (Packaging)
5. Truy xuất thông tin Model Release đang hoạt động qua get_active_model_info
"""

import tempfile
from pathlib import Path
import pytest

from app.services.ocr_engine import OcrEngine
from app.services.ocr_model_registry import (
    ModelArtifactManifest,
    OCRModelRegistry,
    ocr_model_registry,
)


def test_baseline_model_registry_resolves_deterministically():
    """Kiểm thử: Baseline model 'ppocrv6_tiny_baseline' luôn phân giải xác định các trọng số chuẩn."""
    registry = OCRModelRegistry()
    manifest = registry.get_manifest("ppocrv6_tiny_baseline")
    assert manifest is not None
    assert manifest.version == "ppocrv6_tiny_baseline"
    assert manifest.base_model == "PP-OCRv6_tiny"
    assert manifest.inference_runtime == "onnxruntime"
    assert manifest.text_detection_model_name == "PP-OCRv6_tiny_det"
    assert manifest.text_recognition_model_name == "PP-OCRv6_tiny_rec"

    # Phân giải tham số Stream A (Prescription)
    params_rx = registry.resolve_runtime_params("ppocrv6_tiny_baseline", stream_type="prescription")
    assert params_rx["text_detection_model_name"] == "PP-OCRv6_tiny_det"
    assert params_rx["text_recognition_model_name"] == "PP-OCRv6_tiny_rec"
    assert params_rx["use_doc_orientation_classify"] is False
    assert params_rx["use_doc_unwarping"] is False
    assert params_rx["text_det_thresh"] == 0.3
    assert params_rx["text_det_box_thresh"] == 0.5

    # Phân giải tham số Stream B (Packaging)
    params_pkg = registry.resolve_runtime_params(
        "ppocrv6_tiny_baseline",
        stream_type="packaging",
        orientation_enabled=True,
        unwarping_enabled=True,
    )
    assert params_pkg["text_detection_model_name"] == "PP-OCRv6_tiny_det"
    assert params_pkg["use_doc_orientation_classify"] is True
    assert params_pkg["use_doc_unwarping"] is True
    assert params_pkg["text_det_thresh"] == 0.4
    assert params_pkg["text_det_box_thresh"] == 0.6


def test_custom_model_artifact_resolution_with_valid_files():
    """Kiểm thử: Nạp custom fine-tuned model hợp lệ với đầy đủ tệp artifact."""
    registry = OCRModelRegistry()

    with tempfile.TemporaryDirectory() as tmp_dir:
        det_dir = Path(tmp_dir) / "det_v1"
        rec_dir = Path(tmp_dir) / "rec_v1"
        det_dir.mkdir()
        rec_dir.mkdir()

        # Tạo file artifact hợp lệ
        (det_dir / "inference.onnx").write_bytes(b"dummy_onnx_bytes")
        (det_dir / "inference.yml").write_text("model_name: custom_det\n", encoding="utf-8")
        (rec_dir / "inference.onnx").write_bytes(b"dummy_onnx_bytes")
        (rec_dir / "inference.yml").write_text("model_name: custom_rec\n", encoding="utf-8")

        manifest = ModelArtifactManifest(
            version="custom_prescription_v1",
            model_type="fine_tuned",
            base_model="PP-OCRv6_tiny",
            domain="prescription",
            training_framework="PaddleOCR 3.7.0 / PaddleX 3.7.2",
            inference_runtime="onnxruntime",
            text_detection_model_dir=str(det_dir),
            text_recognition_model_dir=str(rec_dir),
            status="production",
        )
        registry.register_manifest(manifest)

        params = registry.resolve_runtime_params("custom_prescription_v1", stream_type="prescription")
        assert params["text_detection_model_dir"] == str(det_dir)
        assert params["text_recognition_model_dir"] == str(rec_dir)


def test_missing_model_directory_fails_fast():
    """Kiểm thử: Fail-Fast ngay lập tức nếu đường dẫn thư mục custom model không tồn tại."""
    registry = OCRModelRegistry()

    manifest = ModelArtifactManifest(
        version="broken_model_v1",
        model_type="fine_tuned",
        text_detection_model_dir="/path/that/does/not/exist/det",
    )
    registry.register_manifest(manifest)

    with pytest.raises(FileNotFoundError) as exc_info:
        registry.resolve_runtime_params("broken_model_v1")
    assert "OCR Detection model directory not found" in str(exc_info.value)


def test_missing_required_files_inside_dir_fails_fast():
    """Kiểm thử: Fail-Fast nếu thư mục tồn tại nhưng thiếu inference.onnx hoặc inference.yml."""
    registry = OCRModelRegistry()

    with tempfile.TemporaryDirectory() as tmp_dir:
        det_dir = Path(tmp_dir) / "incomplete_det"
        det_dir.mkdir()
        # Chỉ có inference.yml, thiếu inference.onnx
        (det_dir / "inference.yml").write_text("model_name: test\n", encoding="utf-8")

        manifest = ModelArtifactManifest(
            version="incomplete_model_v1",
            model_type="fine_tuned",
            text_detection_model_dir=str(det_dir),
        )
        registry.register_manifest(manifest)

        with pytest.raises(FileNotFoundError) as exc_info:
            registry.resolve_runtime_params("incomplete_model_v1")
        assert "missing required artifact files" in str(exc_info.value)
        assert "inference.onnx" in str(exc_info.value)


def test_unregistered_model_version_rejected():
    """Kiểm thử: Yêu cầu phiên bản model chưa đăng ký sẽ bị từ chối rõ ràng bằng ValueError."""
    registry = OCRModelRegistry()
    with pytest.raises(ValueError) as exc_info:
        registry.resolve_runtime_params("non_existent_release_v99")
    assert "is not registered" in str(exc_info.value)


def test_no_silent_fallback():
    """Kiểm thử: Không bao giờ fallback ngầm về baseline nếu phiên bản cấu hình bị lỗi."""
    registry = OCRModelRegistry()
    manifest = ModelArtifactManifest(
        version="failing_custom_v1",
        model_type="fine_tuned",
        text_detection_model_dir="/non_existent_folder_abc",
    )
    registry.register_manifest(manifest)

    # Đảm bảo ném Exception thay vì âm thầm trả về PP-OCRv6_tiny_det
    with pytest.raises(FileNotFoundError):
        registry.resolve_runtime_params("failing_custom_v1")


def test_ocr_engine_model_info_reporting():
    """Kiểm thử: OcrEngine cung cấp thông tin model active chính xác."""
    engine = OcrEngine(active_version="ppocrv6_tiny_baseline")
    info = engine.get_active_model_info()
    assert info["active_version"] == "ppocrv6_tiny_baseline"
    assert info["engine"] == "onnxruntime"
    assert info["lang"] == "vi"
    assert info["manifest"]["base_model"] == "PP-OCRv6_tiny"
