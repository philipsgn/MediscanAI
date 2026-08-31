"""
data_quality_service.py

Service Đánh giá Chất lượng Dữ liệu (Data Quality Engine) cho Mediscan AI.
Tự động tính toán Quality Score và gán Quality Flags để đưa các trường hợp
chưa chắc chắn vào Review Queue (HITL).
"""

import logging
from typing import Any, List, Optional, Tuple

from app.schemas.data_platform_schema import ScanRecordStatus

logger = logging.getLogger(__name__)


class DataQualityService:
    """Đánh giá chất lượng dữ liệu scan tự động và kích hoạt Review Queue."""

    MIN_ITEM_CONFIDENCE_THRESHOLD: float = 0.70
    MIN_AVG_CONFIDENCE_THRESHOLD: float = 0.80

    def evaluate_scan(
        self,
        raw_ocr_items: List[Any],
        mapped_drugs: List[Any],
        clinical_assessment: Optional[Any] = None,
    ) -> Tuple[float, List[str], ScanRecordStatus]:
        """
        Đánh giá chất lượng scan.
        Returns:
            (quality_score: float, quality_flags: List[str], initial_status: ScanRecordStatus)
        """
        flags: List[str] = []

        # 1. Kiểm tra OCR Confidence
        if not raw_ocr_items:
            flags.append("EMPTY_OCR_RESULT")
            avg_ocr_conf = 0.0
        else:
            confidences = [
                getattr(item, "confidence", 1.0)
                if hasattr(item, "confidence")
                else (item.get("confidence", 1.0) if isinstance(item, dict) else 1.0)
                for item in raw_ocr_items
            ]
            avg_ocr_conf = sum(confidences) / len(confidences) if confidences else 1.0
            has_low_item = any(c < self.MIN_ITEM_CONFIDENCE_THRESHOLD for c in confidences)

            if has_low_item or avg_ocr_conf < self.MIN_AVG_CONFIDENCE_THRESHOLD:
                flags.append("LOW_OCR_CONFIDENCE")

        # 2. Kiểm tra Kết quả Chuẩn hóa Thuốc (Normalization)
        if not mapped_drugs and raw_ocr_items:
            flags.append("NO_DRUGS_EXTRACTED")
        else:
            for drug in mapped_drugs:
                is_verified = (
                    getattr(drug, "is_verified", False)
                    if hasattr(drug, "is_verified")
                    else (drug.get("is_verified", False) if isinstance(drug, dict) else False)
                )
                match_method = (
                    getattr(drug, "match_method", None)
                    if hasattr(drug, "match_method")
                    else (drug.get("match_method", None) if isinstance(drug, dict) else None)
                )
                strength_warning = (
                    getattr(drug, "strength_mismatch_warning", None)
                    if hasattr(drug, "strength_mismatch_warning")
                    else (drug.get("strength_mismatch_warning", None) if isinstance(drug, dict) else None)
                )

                if not is_verified or match_method is None:
                    if "UNVERIFIED_DRUG_MATCH" not in flags:
                        flags.append("UNVERIFIED_DRUG_MATCH")

                if strength_warning and "STRENGTH_MISMATCH" not in flags:
                    flags.append("STRENGTH_MISMATCH")

        # 3. Kiểm tra Clinical Alerts (nếu có)
        if clinical_assessment:
            alerts = []
            if hasattr(clinical_assessment, "alerts"):
                alerts = getattr(clinical_assessment, "alerts") or []
            elif isinstance(clinical_assessment, dict) and "alerts" in clinical_assessment:
                alerts = clinical_assessment.get("alerts") or []
            elif hasattr(clinical_assessment, "drug_drug_interactions"):
                alerts = [
                    *(getattr(clinical_assessment, "drug_drug_interactions", []) or []),
                    *(getattr(clinical_assessment, "drug_condition_interactions", []) or []),
                    *(getattr(clinical_assessment, "overdose_duplication_alerts", []) or []),
                ]

            has_high_alert = any(
                (getattr(a, "severity", "") == "HIGH")
                if hasattr(a, "severity")
                else (isinstance(a, dict) and a.get("severity") == "HIGH")
                for a in alerts
            )
            if has_high_alert and "HIGH_SEVERITY_ALERT" not in flags:
                flags.append("HIGH_SEVERITY_ALERT")

        # 4. Tính toán Quality Score (0.0 -> 1.0)
        score = avg_ocr_conf
        if "UNVERIFIED_DRUG_MATCH" in flags:
            score -= 0.15
        if "STRENGTH_MISMATCH" in flags:
            score -= 0.10
        if "HIGH_SEVERITY_ALERT" in flags:
            score -= 0.05
        if "EMPTY_OCR_RESULT" in flags or "NO_DRUGS_EXTRACTED" in flags:
            score -= 0.30

        quality_score = max(0.0, min(1.0, round(score, 4)))

        # 5. Quyết định Trạng thái (Review Trigger)
        if flags or quality_score < 0.85:
            initial_status = ScanRecordStatus.REVIEW_REQUIRED
        else:
            initial_status = ScanRecordStatus.PROCESSED

        logger.debug(
            "[DATA_QUALITY] score=%.4f status=%s flags=%s",
            quality_score, initial_status.value, flags,
        )
        return quality_score, flags, initial_status


data_quality_service = DataQualityService()
