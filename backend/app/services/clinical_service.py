# Clinical Assessment Engine - LLM-based Clinical Reasoning
# Nhiệm vụ: Phân tích tương tác thuốc, chống chỉ định bệnh nền, khuyến cáo an toàn
# Sử dụng LLM local (Ollama: Qwen2.5-0.5B / Phi-3-Mini) hoặc OpenAI API
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.schemas import DrugItem, UserProfile
from app.schemas.ocr_schema import (  # Canonical clinical models [P0/F3.1]
    ClinicalAssessmentResponse,
    DrugConditionAlert,
    DrugInteractionAlert,
    OverdoseAlert,
)

logger = logging.getLogger(__name__)


class ClinicalAssessmentRequest(BaseModel):
    """Input cho Clinical Assessment Engine."""
    drugs: list[DrugItem]
    user_profile: Optional[UserProfile] = None


# [P0/F3.1] DrugInteractionAlert / DrugConditionAlert / OverdoseAlert /
# ClinicalAssessmentResponse đã hợp nhất về canonical `app.schemas.ocr_schema`
# (Task 1.2 — một schema, một nguồn sự thật); import ở đầu file.
class ClinicalService:
    """Clinical Assessment Engine - Sử dụng LLM cho clinical reasoning."""

    def __init__(self) -> None:
        self.use_local_llm = bool(settings.LOCAL_LLM_BASE_URL)
        self.local_llm_url = settings.LOCAL_LLM_BASE_URL.rstrip("/")
        self.local_llm_model = settings.LOCAL_LLM_MODEL
        self.openai_api_key = settings.OPENAI_API_KEY
        self.openai_fallback_model = settings.OPENAI_FALLBACK_MODEL  # [P3/F3.9]

    # ─────────────────────────────────────────────────────────────────────────
    # Prompt Engineering
    # ─────────────────────────────────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        return """
Bạn là một Dược sĩ Lâm sàng (Clinical Pharmacist) chuyên gia với kinh nghiệm 20 năm.
Nhiệm vụ: Phân tích danh sách thuốc của bệnh nhân và đưa ra đánh giá an toàn toàn diện.

NGUYÊN TẮC BẮT BUỘC:
1. LUÔN trả về JSON hợp lệ theo đúng schema được yêu cầu
2. Phân tích dựa trên Evidence-based Medicine (EBM)
3. Phân loại mức độ: HIGH (nguy hiểm tính mạng), MEDIUM (cần theo dõi/chỉnh sửa), LOW (tham khảo)
4. Nêu rõ bằng chứng (evidence level) nếu có: A (RCT), B (Cohort), C (Case-control), D (Expert opinion)
5. LUÔN khuyến nghị tham vấn bác sĩ/dược sĩ chuyên khoa
6. KHÔNG bao giờ kê đơn hoặc thay đổi liều thuốc trực tiếp
7. Ưu tiên an toàn bệnh nhân trên hết

ĐỊNH DẠNG TRẢ VỀ (JSON):
{
  "drug_drug_interactions": [...],
  "drug_condition_interactions": [...],
  "overdose_duplication_alerts": [...],
  "clinical_recommendations": [...],
  "monitoring_parameters": [...]
}
"""

    def _build_user_prompt(self, drugs: list[DrugItem], user_profile: Optional[UserProfile]) -> str:
        # Chuẩn bị dữ liệu thuốc
        drug_lines = []
        for i, drug in enumerate(drugs, 1):
            parts = [f"{i}. {drug.brand_name}"]
            if drug.active_ingredient:
                parts.append(f"Hoạt chất: {drug.active_ingredient}")
            if drug.strength:
                parts.append(f"Hàm lượng: {drug.strength}")
            if drug.dosage_instruction:
                parts.append(f"Liều dùng: {drug.dosage_instruction}")
            if drug.category:
                parts.append(f"Nhóm: {drug.category}")
            if drug.max_daily_dosage:
                parts.append(f"Liều tối đa/ngày: {drug.max_daily_dosage}")
            if drug.warnings:
                parts.append(f"Cảnh báo DB: {', '.join(drug.warnings)}")
            drug_lines.append(" | ".join(parts))

        drugs_text = "\n".join(drug_lines)

        # Profile
        profile_text = "Không có thông tin bệnh nền/dị ứng."
        if user_profile:
            profile_parts = []
            if user_profile.age:
                profile_parts.append(f"Tuổi: {user_profile.age}")
            if user_profile.conditions:
                profile_parts.append(f"Bệnh nền: {', '.join(user_profile.conditions)}")
            if user_profile.allergies:
                profile_parts.append(f"Dị ứng: {', '.join(user_profile.allergies)}")
            if profile_parts:
                profile_text = "; ".join(profile_parts)

        return f"""
DANH SÁCH THUỐC CẦN ĐÁNH GIÁ:
{drugs_text}

THÔNG TIN BỆNH NHÂN:
{profile_text}

HÃY PHÂN TÍCH VÀ TRẢ VỀ JSON THEO SCHEMA:
1. drug_drug_interactions: Tương tác giữa các cặp thuốc trong danh sách
2. drug_condition_interactions: Chống chỉ định thuốc với bệnh nền/dị ứng
3. overdose_duplication_alerts: Quá liều, trùng lặp hoạt chất (tính tổng liều/ngày nếu có dosage_instruction)
4. clinical_recommendations: Khuyến cáo lâm sàng cụ thể, hành động ưu tiên
5. monitoring_parameters: Chỉ số cần theo dõi (VD: INR, creatinine, K+, LFTs, huyết áp...)
"""

    # ─────────────────────────────────────────────────────────────────────────
    # LLM Calls
    # ─────────────────────────────────────────────────────────────────────────

    async def _call_local_llm(self, prompt: str) -> Optional[str]:
        """Gọi LLM local qua Ollama API."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {
                    "model": self.local_llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_ctx": 4096,
                    },
                }
                resp = await client.post(f"{self.local_llm_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
        except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError) as e:
            # [P3/F3.5] Ollama local gọi qua httpx — RequestError bao trùm
            # TimeoutException/ConnectError; tách khỏi lỗi parse JSON ở assess().
            logger.warning("Local LLM call failed (%s): %s", type(e).__name__, e)
            return None

    async def _call_openai(self, prompt: str) -> Optional[str]:
        """Gọi OpenAI API (fallback text-only).

        [P3/F3.9] Model đọc từ Settings (OPENAI_FALLBACK_MODEL), không hardcode.
        [P3/F3.5] Bắt riêng các lỗi SDK openai thay vì except Exception mù quáng."""
        if not self.openai_api_key:
            return None
        try:
            from openai import (
                AsyncOpenAI,
                APIConnectionError,
                APIStatusError,
                APITimeoutError,
                RateLimitError,
            )
        except ImportError:
            logger.error("Thư viện 'openai' chưa được cài — bỏ qua fallback LLM ngoài.")
            return None

        try:
            client = AsyncOpenAI(api_key=self.openai_api_key)
            resp = await client.chat.completions.create(
                model=self.openai_fallback_model,  # [F3.9] từ Settings
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=3000,
            )
            content = resp.choices[0].message.content
            return content or None
        except (APITimeoutError, APIConnectionError) as e:
            logger.warning(
                "OpenAI fallback lỗi kết nối/timeout (%s): %s", type(e).__name__, e
            )
            return None
        except RateLimitError as e:
            logger.warning("OpenAI fallback bị rate-limit: %s", e)
            return None
        except APIStatusError as e:
            logger.warning("OpenAI fallback trả lỗi HTTP status: %s", e)
            return None

    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Thử local LLM trước, fallback OpenAI."""
        if self.use_local_llm:
            result = await self._call_local_llm(prompt)
            if result:
                return result
            logger.warning("Local LLM failed, trying OpenAI fallback...")
        if self.openai_api_key:
            return await self._call_openai(prompt)
        logger.error("No LLM available (no local LLM, no OpenAI key)")
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Fallback Rule-based (khi LLM không khả dụng)
    # ─────────────────────────────────────────────────────────────────────────

    def _fallback_assessment(
        self, drugs: list[DrugItem], user_profile: Optional[UserProfile]
    ) -> ClinicalAssessmentResponse:
        """Fallback rule-based assessment khi LLM down."""
        from app.services.evaluation_service import evaluation_service

        # Dùng evaluation_service cũ cho compatibility
        eval_response = evaluation_service.evaluate_medications(drugs, user_profile)

        # Convert sang format mới
        dd_interactions = []
        dc_interactions = []
        od_alerts = []

        for alert in eval_response.alerts:
            if "trùng lặp" in alert.title.lower() or "quá liều" in alert.title.lower():
                od_alerts.append(OverdoseAlert(
                    severity=alert.severity,
                    title=alert.title,
                    description=alert.description,
                    recommendation=alert.recommendation,
                    ingredient="",  # parse từ description nếu cần
                    total_daily_mg=0.0,
                ))
            elif user_profile and any(c in alert.description.lower() for c in [c.lower() for c in user_profile.conditions]):
                dc_interactions.append(DrugConditionAlert(
                    severity=alert.severity,
                    title=alert.title,
                    description=alert.description,
                    recommendation=alert.recommendation,
                    drug_name="",
                    condition="",
                ))
            else:
                dd_interactions.append(DrugInteractionAlert(
                    severity=alert.severity,
                    title=alert.title,
                    description=alert.description,
                    recommendation=alert.recommendation,
                    interacting_drugs=[],
                ))

        return ClinicalAssessmentResponse(
            drug_drug_interactions=dd_interactions,
            drug_condition_interactions=dc_interactions,
            overdose_duplication_alerts=od_alerts,
            clinical_recommendations=eval_response.schedule_suggestions,
            monitoring_parameters=[],
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    async def assess(self, request: ClinicalAssessmentRequest) -> ClinicalAssessmentResponse:
        """Entry point chính: đánh giá lâm sàng toàn diện."""
        prompt = self._build_system_prompt() + "\n\n" + self._build_user_prompt(
            request.drugs, request.user_profile
        )

        llm_response = await self._call_llm(prompt)

        if llm_response:
            try:
                parsed = json.loads(llm_response)
            except json.JSONDecodeError as e:
                # [P3/F3.5] JSON hỏng → rơi xuống fallback rule-based NGAY
                # (khác bản chất với lỗi kết nối — connection do _call_* xử lý).
                logger.error("LLM trả nội dung không phải JSON hợp lệ: %s", e)
                logger.debug("Raw LLM response: %s", llm_response[:500])
            else:
                try:
                    return ClinicalAssessmentResponse(**parsed)
                except ValidationError as e:
                    # [P3/F3.5] JSON hợp lệ nhưng sai schema → fallback rule-based,
                    # không để ValidationError làm chết pipeline.
                    logger.error(
                        "LLM JSON sai schema ClinicalAssessmentResponse: %s",
                        e.errors()[:3],
                    )
                    logger.debug("Raw LLM response: %s", llm_response[:500])

        # Fallback
        logger.warning("Using fallback rule-based assessment")
        return self._fallback_assessment(request.drugs, request.user_profile)


clinical_service = ClinicalService()