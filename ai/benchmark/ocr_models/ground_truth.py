"""Ground truth data and accuracy metrics for OCR benchmark (Mediscan AI).

Provides:
- Hand-verified ground truth for toa-thuoc.jpg (prescription image)
- Character Error Rate (CER) computation via Levenshtein distance
- Field-level accuracy for drug name + strength extraction
"""

from __future__ import annotations


# ── Ground truth for toa-thuoc.jpg (hand-verified against actual image) ──────

GROUND_TRUTH_TOA_THUOC_DRUGS: list[dict[str, str]] = [
    {
        "name": "Augmentin 625mg",
        "dosage": "20v",
        "morning": "1v",
        "afternoon": "1v",
        "night": "1v",
    },
    {
        "name": "Medrol 16mg",
        "dosage": "5v",
        "morning": "1v",
        "afternoon": "",
        "night": "",
    },
    {
        "name": "Ibuprofen 400mg",
        "dosage": "15v",
        "morning": "1v",
        "afternoon": "1v",
        "night": "1v",
    },
    {
        "name": "Alphachymotrysin 4,2mg",
        "dosage": "30v",
        "morning": "2v",
        "afternoon": "2v",
        "night": "2v",
    },
    {
        "name": "Paracetamol 500mg",
        "dosage": "15v",
        "morning": "1v",
        "afternoon": "1v",
        "night": "1v",
    },
    {
        "name": "Omeprazol 20mg",
        "dosage": "10v",
        "morning": "1v (trước ăn 30 phút)",
        "afternoon": "",
        "night": "1v (trước ăn 30 phút)",
    },
]

# Full expected text lines (key content lines only, order matches top-to-bottom)
GROUND_TRUTH_TOA_THUOC_KEY_LINES: list[str] = [
    "TOA THUỐC",
    "PRESCRIPTION",
    "Họ và tên (Full name):",
    "Tuổi (Age):",
    "Địa chỉ (Address):",
    "Chẩn đoán (Diagnosis):",
    "Tên thuốc (Drug): Augmentin 625mg",
    "Số lượng (Dosage): 20v",
    "Sáng (Morning): 1v",
    "Trưa (Afternoon): 1v",
    "Tối (Night): 1v",
    "Tên thuốc (Drug): Medrol 16mg",
    "Số lượng (Dosage): 5v",
    "Sáng (Morning): 1v",
    "Tên thuốc (Drug): Ibuprofen 400mg",
    "Số lượng (Dosage): 15v",
    "Sáng (Morning): 1v",
    "Trưa (Afternoon): 1v",
    "Tối (Night): 1v",
    "Tên thuốc (Drug): Alphachymotrysin 4,2mg",
    "Số lượng (Dosage): 30v",
    "Sáng (Morning): 2v",
    "Trưa (Afternoon): 2v",
    "Tối (Night): 2v",
    "Tên thuốc (Drug): Paracetamol 500mg",
    "Số lượng (Dosage): 15v",
    "Sáng (Morning): 1v",
    "Trưa (Afternoon): 1v",
    "Tối (Night): 1v",
    "Tên thuốc (Drug): Omeprazol 20mg",
    "Số lượng (Dosage): 10v",
    "Sáng (Morning): 1v (trước ăn 30 phút)",
    "Tối (Night): 1v (trước ăn 30 phút)",
    "Uống thuốc sau khi ăn no",
    "Take medicine after eating",
    "Bác sĩ điều trị (Doctor)",
    "Ký tên (Sign)",
]

# Drug name + strength targets for field-level matching
DRUG_FIELD_TARGETS: list[str] = [
    "Augmentin 625mg",
    "Medrol 16mg",
    "Ibuprofen 400mg",
    "Alphachymotrysin 4,2mg",
    "Paracetamol 500mg",
    "Omeprazol 20mg",
]


# ── CER computation (Levenshtein-based) ─────────────────────────────────────


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost: 0 if chars match, 1 otherwise
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (0 if c1 == c2 else 1)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]


def compute_cer(predicted: str, ground_truth: str) -> float:
    """Compute Character Error Rate (CER).

    CER = levenshtein_distance(predicted, ground_truth) / len(ground_truth)

    Returns:
        Float between 0.0 (perfect) and potentially >1.0 (very bad).
        Returns 0.0 if ground_truth is empty.
    """
    if not ground_truth:
        return 0.0
    distance = _levenshtein_distance(predicted, ground_truth)
    return distance / len(ground_truth)


def compute_field_accuracy(
    extracted_text: str,
    drug_targets: list[str] | None = None,
) -> dict[str, float | int | list[str]]:
    """Compute field-level accuracy: what % of drug name+strength fields are found.

    Performs case-insensitive substring search in the full extracted text.

    Args:
        extracted_text: Full OCR output joined as single string.
        drug_targets: List of expected drug name+strength strings.

    Returns:
        Dict with 'total', 'matched', 'missed', 'accuracy' keys.
    """
    if drug_targets is None:
        drug_targets = DRUG_FIELD_TARGETS

    text_lower = extracted_text.lower()
    matched: list[str] = []
    missed: list[str] = []

    for target in drug_targets:
        if target.lower() in text_lower:
            matched.append(target)
        else:
            missed.append(target)

    total = len(drug_targets)
    return {
        "total": total,
        "matched_count": len(matched),
        "matched": matched,
        "missed": missed,
        "accuracy": len(matched) / total if total > 0 else 0.0,
    }
