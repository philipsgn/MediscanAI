"""
data_capture_service.py

Service Quản lý Lưu trữ Dữ liệu Scan, Review Queue (HITL),
và Structured Ground Truth Dataset cho Mediscan AI Data Platform.

TUÂN THỦ PRIVACY BY DESIGN (ARCHITECTURE.md 7.1):
- Xử lý hoàn toàn trong bộ nhớ RAM, KHÔNG lưu file ảnh scan.
- Chỉ lưu trữ structured text/drug artifacts, quality score, flags, và human corrections.
- `image_sha256`: Checksum SHA-256 đối soát tính duy nhất trong RAM.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning import DEFAULT_DATASET_VERSION, get_current_pipeline_lineage
from app.models.data_capture import ScanRecordModel
from app.schemas.data_platform_schema import (
    DatasetCandidateRequest,
    HumanCorrectionRequest,
    ScanRecordStatus,
    validate_state_transition,
)
from app.services.data_quality_service import data_quality_service

logger = logging.getLogger(__name__)


class ConcurrencyConflictError(Exception):
    """Ném ra khi phát hiện Optimistic Locking Conflict giữa các concurrent reviewer."""


def _to_serializable(items: Any) -> Any:
    """Helper chuyển đổi Pydantic models hoặc dataclasses thành dict để lưu JSON."""
    if items is None:
        return None
    if isinstance(items, list):
        return [_to_serializable(x) for x in items]
    if hasattr(items, "model_dump"):
        return items.model_dump()
    if hasattr(items, "dict"):
        return items.dict()
    if isinstance(items, dict):
        return {k: _to_serializable(v) for k, v in items.items()}
    return items


class DataCaptureService:
    """Service chịu trách nhiệm lưu trữ lineage, điều phối review queue và tạo dataset."""

    def __init__(self) -> None:
        self._total_captures: int = 0
        self._failed_captures: int = 0
        self._last_errors: List[Dict[str, Any]] = []

    def get_metrics(self) -> Dict[str, Any]:
        """Cung cấp metrics giám sát độ tin cậy của Data Capture subsystem."""
        return {
            "total_captures": self._total_captures,
            "failed_captures": self._failed_captures,
            "success_rate": (
                (self._total_captures - self._failed_captures) / self._total_captures
                if self._total_captures > 0
                else 1.0
            ),
            "recent_errors": self._last_errors[-10:],
        }

    async def capture_scan(
        self,
        db: AsyncSession,
        request_id: str,
        user_id: Optional[str],
        source_type: str,
        image_sha256: str,
        raw_ocr_items: List[Any],
        mapped_drugs: List[Any],
        clinical_assessment: Optional[Any] = None,
    ) -> Optional[ScanRecordModel]:
        """
        Lưu vết scan vào bảng `scan_records` kèm version lineage và quality evaluation.
        Có cơ chế Safe Degradation (không ném Exception làm ngắt quãng response của user).
        KHÔNG LƯU ẢNH THÔ: image_sha256 chỉ là checksum hash 64-hex xử lý trong RAM.
        """
        self._total_captures += 1
        try:
            # 1. Đánh giá chất lượng tự động từ structured artifacts
            quality_score, quality_flags, initial_status = data_quality_service.evaluate_scan(
                raw_ocr_items=raw_ocr_items,
                mapped_drugs=mapped_drugs,
                clinical_assessment=clinical_assessment,
            )
            lineage = get_current_pipeline_lineage()

            scan_record = ScanRecordModel(
                request_id=request_id,
                user_id=user_id,
                source_type=source_type,
                image_sha256=image_sha256,
                status=initial_status.value,
                quality_score=quality_score,
                quality_flags=quality_flags,
                raw_ocr_result=_to_serializable(raw_ocr_items) or [],
                normalized_result=_to_serializable(mapped_drugs) or [],
                clinical_result=_to_serializable(clinical_assessment),
                corrected_payload=None,
                is_dataset_candidate=False,
                dataset_version=None,
                dataset_tag=None,
                version_metadata=lineage.model_dump(),
                version=1,
            )

            db.add(scan_record)
            await db.commit()
            await db.refresh(scan_record)

            logger.info(
                "[DATA_CAPTURE_OK] scan_id=%s request_id=%s status=%s quality=%.2f sha256=%s",
                scan_record.id, request_id, scan_record.status, quality_score, image_sha256,
            )
            return scan_record

        except Exception as exc:  # noqa: BLE001
            self._failed_captures += 1
            err_entry = {
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
                "error_type": type(exc).__name__,
            }
            self._last_errors.append(err_entry)
            if len(self._last_errors) > 50:
                self._last_errors.pop(0)

            # Structured logging: Cảnh báo rõ ràng, không swallow im lặng
            logger.error(
                "[DATA_CAPTURE_PERSISTENCE_FAILED] request_id=%s error_type=%s error=%s (P1 Data Loss Risk - Degraded)",
                request_id, type(exc).__name__, exc, exc_info=True,
            )
            try:
                await db.rollback()
            except Exception:  # noqa: S110
                pass
            return None

    async def get_review_queue(
        self,
        db: AsyncSession,
        status: Optional[ScanRecordStatus] = None,
        source_type: Optional[str] = None,
        is_dataset_candidate: Optional[bool] = None,
        min_quality: Optional[float] = None,
        max_quality: Optional[float] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[ScanRecordModel]]:
        """Lấy danh sách scan trong Review Queue kèm bộ lọc và phân trang."""
        stmt = select(ScanRecordModel)

        if status is not None:
            stmt = stmt.where(ScanRecordModel.status == status.value)
        if source_type is not None:
            stmt = stmt.where(ScanRecordModel.source_type == source_type)
        if is_dataset_candidate is not None:
            stmt = stmt.where(ScanRecordModel.is_dataset_candidate == is_dataset_candidate)
        if min_quality is not None:
            stmt = stmt.where(ScanRecordModel.quality_score >= min_quality)
        if max_quality is not None:
            stmt = stmt.where(ScanRecordModel.quality_score <= max_quality)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one_or_none() or 0

        stmt = stmt.order_by(ScanRecordModel.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        items = list(result.scalars().all())

        return total, items

    async def get_scan_record(self, db: AsyncSession, scan_id: str) -> Optional[ScanRecordModel]:
        """Truy xuất chi tiết một scan record theo id."""
        stmt = select(ScanRecordModel).where(ScanRecordModel.id == scan_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def submit_human_correction(
        self,
        db: AsyncSession,
        scan_id: str,
        reviewer_id: str,
        correction_req: HumanCorrectionRequest,
    ) -> ScanRecordModel:
        """
        Ghi nhận chỉnh sửa của Reviewer (HITL).
        QUY TẮC BẢO VỆ BẤT BIẾN:
        1. Tuyệt đối không ghi đè raw_ocr_result hay normalized_result gốc của AI.
        2. Validate state transitions qua State Machine.
        3. Optimistic Locking version check để chặn Lost Update khi concurrent review.
        4. Idempotent: Gửi lại cùng payload/decision không gây conflict vô lý.
        """
        scan = await self.get_scan_record(db, scan_id)
        if not scan:
            raise ValueError(f"Scan record với ID '{scan_id}' không tồn tại.")

        current_status = ScanRecordStatus(scan.status)
        target_status = correction_req.decision

        # 1. Optimistic Locking check
        if correction_req.expected_version is not None:
            if scan.version != correction_req.expected_version:
                raise ConcurrencyConflictError(
                    f"Xung đột phiên bản (Optimistic Locking Conflict): Scan record hiện đang ở version {scan.version}, "
                    f"nhưng reviewer gửi expected_version={correction_req.expected_version}. "
                    "Một reviewer khác có thể đã cập nhật bản ghi này. Vui lòng tải lại dữ liệu mới nhất.",
                )

        # 2. Idempotency Check: nếu nội dung hiệu đính và quyết định giống hệt đã lưu
        new_drugs_dump = [d.model_dump() for d in correction_req.corrected_drugs]
        if scan.corrected_payload and isinstance(scan.corrected_payload, dict):
            saved_drugs = scan.corrected_payload.get("corrected_drugs", [])
            saved_decision = scan.corrected_payload.get("decision")
            if saved_drugs == new_drugs_dump and saved_decision == target_status.value and scan.status == target_status.value:
                logger.info("[HUMAN_CORRECTION_IDEMPOTENT] scan_id=%s decision=%s", scan.id, target_status.value)
                return scan

        # 3. State Machine Transition Validation
        validate_state_transition(current_status, target_status)

        # 4. Ghi nhận payload hiệu đính riêng biệt (Zero-Overwrite)
        corrected_payload = {
            "corrected_drugs": new_drugs_dump,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "reviewer_id": reviewer_id,
            "decision": target_status.value,
            "review_notes": correction_req.review_notes,
            "previous_status": scan.status,
            "previous_version": scan.version,
        }

        scan.corrected_payload = corrected_payload
        scan.status = target_status.value
        scan.reviewed_by = reviewer_id
        scan.reviewed_at = datetime.now(timezone.utc)
        scan.review_notes = correction_req.review_notes
        scan.version += 1  # Increment version on every successful mutation

        await db.commit()
        await db.refresh(scan)

        logger.info(
            "[HUMAN_CORRECTION_SAVED] scan_id=%s status=%s reviewer=%s version=%d drugs_count=%d",
            scan.id, scan.status, reviewer_id, scan.version, len(correction_req.corrected_drugs),
        )
        return scan

    async def mark_dataset_candidate(
        self,
        db: AsyncSession,
        scan_id: str,
        candidate_req: DatasetCandidateRequest,
    ) -> ScanRecordModel:
        """
        Đánh dấu scan làm ứng viên dataset cho Active Learning / Fine-tuning.
        QUY TẮC NGHIÊM NGẶT:
        CHỈ duy nhất trạng thái 'ACCEPTED' (đã được chuyên viên xác nhận Ground Truth)
        mới được phép chuyển thành Dataset Candidate. Mọi trạng thái khác (PROCESSED,
        REVIEW_REQUIRED, IN_REVIEW, REJECTED, REVIEWED) đều bị từ chối dứt khoát.
        """
        scan = await self.get_scan_record(db, scan_id)
        if not scan:
            raise ValueError(f"Scan record với ID '{scan_id}' không tồn tại.")

        if scan.status != ScanRecordStatus.ACCEPTED.value:
            raise ValueError(
                f"Không thể tạo Dataset Candidate từ scan có trạng thái '{scan.status}'. "
                "CHỈ DUY NHẤT trạng thái 'ACCEPTED' (Ground Truth đã xác thực) mới đủ điều kiện tạo tập dữ liệu huấn luyện.",
            )

        # Idempotency check
        target_version = candidate_req.dataset_version or scan.dataset_version or DEFAULT_DATASET_VERSION
        if scan.is_dataset_candidate and scan.dataset_version == target_version and scan.dataset_tag == candidate_req.dataset_tag:
            return scan

        scan.is_dataset_candidate = True
        scan.dataset_version = target_version
        scan.dataset_tag = candidate_req.dataset_tag or scan.dataset_tag
        scan.version += 1

        await db.commit()
        await db.refresh(scan)

        logger.info(
            "[DATASET_CANDIDATE_MARKED] scan_id=%s dataset_version=%s tag=%s version=%d",
            scan.id, scan.dataset_version, scan.dataset_tag, scan.version,
        )
        return scan

    async def export_dataset(
        self,
        db: AsyncSession,
        dataset_version: Optional[str] = None,
        status: Optional[ScanRecordStatus] = None,
    ) -> Tuple[str, List[ScanRecordModel]]:
        """
        Truy xuất toàn bộ các scan đã đánh dấu dataset candidate kèm lineage đầy đủ
        và tính toán Snapshot Hash bảo đảm tính tái lập (Reproducibility).
        """
        stmt = select(ScanRecordModel).where(ScanRecordModel.is_dataset_candidate.is_(True))

        # Chỉ export các bản ghi ACCEPTED (Ground Truth)
        stmt = stmt.where(ScanRecordModel.status == ScanRecordStatus.ACCEPTED.value)

        if dataset_version:
            stmt = stmt.where(ScanRecordModel.dataset_version == dataset_version)
        if status:
            stmt = stmt.where(ScanRecordModel.status == status.value)

        stmt = stmt.order_by(ScanRecordModel.id.asc())
        result = await db.execute(stmt)
        records = list(result.scalars().all())

        # Tính Snapshot Hash từ ID, version và image_sha256 của tất cả các samples
        snapshot_payload = [
            f"{r.id}:{r.version}:{r.image_sha256}"
            for r in records
        ]
        snapshot_hash = hashlib.sha256(json.dumps(snapshot_payload).encode("utf-8")).hexdigest()

        return snapshot_hash, records


data_capture_service = DataCaptureService()
