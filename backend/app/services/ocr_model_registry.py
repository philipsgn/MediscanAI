"""
OCR Model Registry & Lifecycle Management (Stage 11 Architecture Gate).
Single Source of Truth cho việc quản lý phiên bản, kiểm tra tính toàn vẹn (Validation),
phân giải trọng số (Resolution), và Rollback an toàn cho hệ thống OCR On-Premise.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class ModelArtifactManifest(BaseModel):
    """Đặc tả siêu dữ liệu (Metadata Contract) cho một phiên bản mô hình OCR Release."""

    version: str = Field(..., description="Mã định danh phiên bản (VD: 'ppocrv6_tiny_baseline', 'prescription_v1')")
    model_type: Literal["baseline", "fine_tuned", "experimental"] = Field(
        "baseline", description="Phân loại mô hình"
    )
    base_model: str = Field("PP-OCRv6_tiny", description="Kiến trúc mô hình gốc")
    domain: Literal["general", "prescription", "packaging"] = Field(
        "general", description="Miền dữ liệu chuyên biệt"
    )
    training_framework: str = Field("PaddleOCR 3.7.0 / PaddleX 3.7.2", description="Framework huấn luyện")
    inference_runtime: str = Field("onnxruntime", description="Runtime suy luận Production")
    
    # Model parameters for PaddleOCR / PaddleX runtime
    text_detection_model_name: Optional[str] = Field(
        None, description="Tên mô hình Detection mặc định của PaddleX (nếu dùng pretrained)"
    )
    text_detection_model_dir: Optional[str] = Field(
        None, description="Đường dẫn thư mục chứa artifact Detection custom (inference.onnx + inference.yml)"
    )
    text_recognition_model_name: Optional[str] = Field(
        None, description="Tên mô hình Recognition mặc định của PaddleX (nếu dùng pretrained)"
    )
    text_recognition_model_dir: Optional[str] = Field(
        None, description="Đường dẫn thư mục chứa artifact Recognition custom (inference.onnx + inference.yml)"
    )
    character_dict_path: Optional[str] = Field(
        None, description="Đường dẫn tệp từ điển ký tự (nếu Recognition dùng từ điển tùy chỉnh)"
    )

    # Provenance & Audit
    dataset_version: Optional[str] = Field(None, description="Phiên bản tập dữ liệu huấn luyện")
    training_commit: Optional[str] = Field(None, description="Git commit hash của mã nguồn huấn luyện")
    exported_at: Optional[str] = Field(None, description="Thời điểm export sang ONNX (ISO 8601)")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Kết quả benchmark/accuracy")
    status: Literal["production", "staging", "candidate", "deprecated", "archived"] = Field(
        "production", description="Trạng thái triển khai"
    )

    @field_validator("version")
    @classmethod
    def validate_version_format(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Version identifier cannot be empty.")
        return v.strip()


class OCRModelRegistry:
    """Quản lý danh mục mô hình OCR, phân giải trọng số và kiểm soát tính toàn vẹn (Fail-Fast)."""

    DEFAULT_BASELINE_VERSION = "ppocrv6_tiny_baseline"

    def __init__(self, registry_file: Optional[Path] = None) -> None:
        self.registry_file = registry_file
        self._registry: Dict[str, ModelArtifactManifest] = {}
        self._load_default_registry()

    def _load_default_registry(self) -> None:
        """Nạp registry mặc định với Baseline PP-OCRv6 Tiny chuẩn."""
        baseline_manifest = ModelArtifactManifest(
            version=self.DEFAULT_BASELINE_VERSION,
            model_type="baseline",
            base_model="PP-OCRv6_tiny",
            domain="general",
            training_framework="PaddleOCR 3.7.0 / PaddleX 3.7.2",
            inference_runtime="onnxruntime",
            text_detection_model_name="PP-OCRv6_tiny_det",
            text_recognition_model_name="PP-OCRv6_tiny_rec",
            metrics={
                "benchmark_sla_ms": 15000,
                "avg_cpu_latency_ms": 5590,
                "engine": "PP-OCRv6_tiny-ONNX",
            },
            status="production",
        )
        self._registry[self.DEFAULT_BASELINE_VERSION] = baseline_manifest

        # Nếu có file registry tùy biến trên đĩa, nạp thêm
        if self.registry_file and self.registry_file.exists():
            try:
                data = json.loads(self.registry_file.read_text(encoding="utf-8"))
                for entry in data.get("models", []):
                    manifest = ModelArtifactManifest(**entry)
                    self._registry[manifest.version] = manifest
            except Exception as exc:
                logger.warning("Không thể nạp registry từ %s: %s", self.registry_file, exc)

    def get_manifest(self, version: str) -> Optional[ModelArtifactManifest]:
        """Truy xuất metadata của một phiên bản mô hình."""
        return self._registry.get(version)

    def register_manifest(self, manifest: ModelArtifactManifest) -> None:
        """Đăng ký một phiên bản mô hình mới vào Registry."""
        self._registry[manifest.version] = manifest

    def list_versions(self) -> List[str]:
        """Danh sách tất cả các phiên bản mô hình đã đăng ký."""
        return list(self._registry.keys())

    def validate_artifact_integrity(self, manifest: ModelArtifactManifest) -> None:
        """
        Kiểm tra tính toàn vẹn của artifact trước khi nạp vào Runtime (Fail-Fast Principle).
        Nếu chỉ định custom model dir, thư mục bắt buộc phải tồn tại và chứa inference.onnx + inference.yml.
        """
        if manifest.text_detection_model_dir:
            det_dir = Path(manifest.text_detection_model_dir)
            if not det_dir.exists() or not det_dir.is_dir():
                raise FileNotFoundError(
                    f"OCR Detection model directory not found: '{det_dir}'. Fail-Fast triggered."
                )
            required_files = ["inference.onnx", "inference.yml"]
            missing = [f for f in required_files if not (det_dir / f).exists()]
            if missing:
                raise FileNotFoundError(
                    f"OCR Detection model directory '{det_dir}' is missing required artifact files: {missing}"
                )

        if manifest.text_recognition_model_dir:
            rec_dir = Path(manifest.text_recognition_model_dir)
            if not rec_dir.exists() or not rec_dir.is_dir():
                raise FileNotFoundError(
                    f"OCR Recognition model directory not found: '{rec_dir}'. Fail-Fast triggered."
                )
            required_files = ["inference.onnx", "inference.yml"]
            missing = [f for f in required_files if not (rec_dir / f).exists()]
            if missing:
                raise FileNotFoundError(
                    f"OCR Recognition model directory '{rec_dir}' is missing required artifact files: {missing}"
                )

        if manifest.character_dict_path:
            dict_file = Path(manifest.character_dict_path)
            if not dict_file.exists() or not dict_file.is_file() or dict_file.stat().st_size == 0:
                raise FileNotFoundError(
                    f"OCR Character dictionary file not found or empty: '{dict_file}'"
                )

    def resolve_runtime_params(
        self,
        version: str,
        stream_type: Literal["prescription", "packaging"] = "prescription",
        orientation_enabled: bool = False,
        unwarping_enabled: bool = False,
    ) -> Dict[str, Any]:
        """
        Phân giải các tham số khởi tạo PaddleOCR chính xác theo Release Manifest và Profile luồng.
        - Stream A (Prescription): Text threshold tối ưu cho toa thuốc / thermal receipt
        - Stream B (Packaging): Text threshold tối ưu cho bao bì / vỏ hộp / lọ thuốc
        """
        manifest = self.get_manifest(version)
        if not manifest:
            raise ValueError(
                f"OCR model version '{version}' is not registered. Registered versions: {self.list_versions()}"
            )

        # Kiểm tra tính toàn vẹn của artifacts (Fail-Fast nếu thiếu file)
        self.validate_artifact_integrity(manifest)

        params: Dict[str, Any] = {
            "device": "cpu",
            "engine": manifest.inference_runtime,
            "use_textline_orientation": False,
        }

        # Detection params
        if manifest.text_detection_model_dir:
            params["text_detection_model_dir"] = manifest.text_detection_model_dir
        else:
            params["text_detection_model_name"] = manifest.text_detection_model_name or "PP-OCRv6_tiny_det"

        # Recognition params
        if manifest.text_recognition_model_dir:
            params["text_recognition_model_dir"] = manifest.text_recognition_model_dir
        else:
            params["text_recognition_model_name"] = manifest.text_recognition_model_name or "PP-OCRv6_tiny_rec"

        # Dual-stream tuning parameters
        if stream_type == "packaging":
            params["use_doc_orientation_classify"] = orientation_enabled
            params["use_doc_unwarping"] = unwarping_enabled
            params["text_det_thresh"] = 0.4
            params["text_det_box_thresh"] = 0.6
            params["text_det_unclip_ratio"] = 1.8
        else:
            # Prescription / Receipt
            params["use_doc_orientation_classify"] = False
            params["use_doc_unwarping"] = False
            params["text_det_thresh"] = 0.3
            params["text_det_box_thresh"] = 0.5
            params["text_det_unclip_ratio"] = 1.6

        return params


# Singleton Registry instance dùng chung
ocr_model_registry = OCRModelRegistry()
