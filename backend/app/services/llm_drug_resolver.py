# LLM Medical Knowledge Resolver Service (Stage 17)
# Suy luận tri thức dược học mở rộng cho thuốc lạ và Thực phẩm bảo vệ sức khỏe (TPCN)
# Hỗ trợ: Google Gemini Flash, OpenAI, Local Ollama.
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMDrugResolution(BaseModel):
    """Cấu trúc dữ liệu chuẩn hóa kết quả suy luận từ LLM."""
    is_health_product: bool = False
    brand_name: str
    is_supplement: bool = False
    active_ingredient: Optional[str] = None
    strength: Optional[str] = None
    category: Optional[str] = None
    confidence_score: float = Field(default=0.75, ge=0.0, le=1.0)
    notes: Optional[str] = None
    contraindications: list[str] = Field(default_factory=list)


class LLMDrugResolver:
    """Tầng 4 Fallback: Suy luận hoạt chất thuốc/TPCN lạ từ Text LLM."""

    def __init__(self) -> None:
        self.enabled = settings.ENABLE_LLM_DRUG_RESOLVER
        self.gemini_api_key = settings.GEMINI_API_KEY.strip()
        self.gemini_model = settings.GEMINI_MODEL
        self.groq_api_key = settings.GROQ_API_KEY.strip()
        self.groq_model = settings.GROQ_MODEL
        self.openai_api_key = settings.OPENAI_API_KEY.strip()
        self.openai_model = settings.OPENAI_FALLBACK_MODEL
        self.local_llm_url = settings.LOCAL_LLM_BASE_URL.rstrip("/")
        self.local_llm_model = settings.LOCAL_LLM_MODEL

    def _build_system_prompt(self) -> str:
        return (
            "Bạn là Chuyên gia Dược học Lâm sàng (Clinical Pharmacist AI) của Mediscan AI.\n"
            "Nhiệm vụ của bạn là nhận diện chính xác thành phần hoạt chất gốc (Active Ingredients / INN) "
            "hoặc thành phần sinh học của các loại thuốc, biệt dược đặc thù, hoặc THỰC PHẨM CHỨC NĂNG / "
            "THỰC PHẨM BẢO VỆ SỨC KHỎE (Dietary Supplements / Nutraceuticals) phổ biến tại thị trường.\n\n"
            "QUY TẮC BẮT BUỘC:\n"
            "1. Phân loại rõ ràng:\n"
            "   - Nếu là Hóa dược kê đơn / OTC: is_supplement = false, active_ingredient là tên hoạt chất INN "
            "     (VD: 'Aciloc 150' -> 'Ranitidine', 'Oricox' -> 'Etoricoxib').\n"
            "   - Nếu là Thực phẩm chức năng / Bổ sung dinh dưỡng / Thảo dược: is_supplement = true, "
            "     active_ingredient là các thành phần sinh học chính (VD: 'Tendoactive' -> "
            "     'Mucopolysaccharides / Collagen Type I / Vitamin C', 'Glucosamine Orihiro' -> 'Glucosamine').\n"
            "2. Nếu từ đầu vào là từ vô nghĩa, rác OCR, hoặc không phải sản phẩm sức khỏe (VD: 'asdfgh', 'carton', '12345'):\n"
            "   BẮT BUỘC trả về: {\"is_health_product\": false, \"brand_name\": \"...\", \"active_ingredient\": null}.\n"
            "   TUYỆT ĐỐI KHÔNG ẢO GIÁC HOẶC BỊA ĐẶT THÀNH PHẦN (ZERO HALLUCINATION).\n"
            "3. BẮT BUỘC chỉ trả về 1 JSON object duy nhất theo định dạng:\n"
            "{\n"
            '  "is_health_product": true/false,\n'
            '  "brand_name": "Tên sản phẩm chuẩn hóa",\n'
            '  "is_supplement": true/false,\n'
            '  "active_ingredient": "Hoạt chất 1 / Hoạt chất 2",\n'
            '  "strength": "Hàm lượng chuẩn (nếu có, VD: 500mg, hoặc null)",\n'
            '  "category": "Nhóm tác dụng (VD: Hỗ trợ gân khớp, Giảm đau, Tiêu hóa)",\n'
            '  "confidence_score": 0.75,\n'
            '  "notes": "Mô tả ngắn gọn công dụng",\n'
            '  "contraindications": ["Chống chỉ định 1", "Chống chỉ định 2"]\n'
            "}"
        )

    def _build_user_prompt(self, brand_name: str, context: Optional[str] = None) -> str:
        prompt = f"Phân tích sản phẩm dược/TPCN có tên thương mại: '{brand_name}'."
        if context:
            prompt += f"\nNgữ cảnh trích xuất thêm từ bao bì: {context}"
        return prompt

    async def resolve_drug_with_llm(
        self, brand_name: str, context: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """
        Gọi LLM để phân giải hoạt chất thuốc lạ hoặc TPCN.
        Thứ tự thử nghiệm: Gemini API -> Groq Cloud API -> Local Ollama -> OpenAI API.
        """
        if not self.enabled or not brand_name or not brand_name.strip():
            return None

        clean_brand = brand_name.strip()
        # Bỏ qua nếu từ quá ngắn hoặc chỉ toàn ký tự đặc biệt
        if len(clean_brand) < 2 or not re.search(r"[a-zA-Z0-9À-ỹ]", clean_brand):
            return None

        # 1. Thử gọi Google Gemini (ưu tiên số 1: siêu nhanh, chi phí thấp, tối ưu y tế đa ngôn ngữ)
        if self.gemini_api_key:
            res = await self._call_gemini(clean_brand, context)
            if res:
                return res

        # 2. Thử gọi Groq Cloud API (ưu tiên số 2: siêu tốc 500+ tokens/s, miễn phí)
        if self.groq_api_key:
            res = await self._call_groq(clean_brand, context)
            if res:
                return res

        # 3. Thử gọi Local Ollama (ưu tiên số 3: offline on-premise trên máy)
        if self.local_llm_url:
            res = await self._call_local_llm(clean_brand, context)
            if res:
                return res

        # 4. Thử gọi OpenAI (fallback dự phòng cuối cùng)
        if self.openai_api_key:
            res = await self._call_openai(clean_brand, context)
            if res:
                return res

        return None

    async def _call_gemini(self, brand_name: str, context: Optional[str]) -> Optional[dict[str, Any]]:
        """Gọi Google Gemini REST API."""
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.gemini_model}:generateContent?key={self.gemini_api_key}"
        )
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": f"{self._build_system_prompt()}\n\n{self._build_user_prompt(brand_name, context)}"}
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        content_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        return self._parse_and_validate_json(content_part, brand_name)
                else:
                    logger.warning(
                        "[llm_drug_resolver] Gemini API returned status %d: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
        except Exception as e:
            logger.warning("[llm_drug_resolver] Gemini call failed (%s): %s", type(e).__name__, e)

        return None

    async def _call_groq(self, brand_name: str, context: Optional[str]) -> Optional[dict[str, Any]]:
        """Gọi Groq Cloud API (LPU siêu tốc 500+ tokens/giây, OpenAI-compatible)."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.groq_model,
            "messages": [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": self._build_user_prompt(brand_name, context)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 600,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        return self._parse_and_validate_json(content, brand_name)
                else:
                    logger.warning(
                        "[llm_drug_resolver] Groq API returned status %d: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
        except Exception as e:
            logger.warning("[llm_drug_resolver] Groq call failed (%s): %s", type(e).__name__, e)

        return None

    async def _call_openai(self, brand_name: str, context: Optional[str]) -> Optional[dict[str, Any]]:
        """Gọi OpenAI Chat Completions API."""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.openai_api_key)
            resp = await client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": self._build_user_prompt(brand_name, context)},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=600,
            )
            content = resp.choices[0].message.content
            if content:
                return self._parse_and_validate_json(content, brand_name)
        except Exception as e:
            logger.warning("[llm_drug_resolver] OpenAI call failed (%s): %s", type(e).__name__, e)

        return None

    async def _call_local_llm(self, brand_name: str, context: Optional[str]) -> Optional[dict[str, Any]]:
        """Gọi Local Ollama API."""
        url = f"{self.local_llm_url}/v1/chat/completions"
        payload = {
            "model": self.local_llm_model,
            "messages": [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": self._build_user_prompt(brand_name, context)},
            ],
            "temperature": 0.1,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        return self._parse_and_validate_json(content, brand_name)
        except Exception as e:
            logger.debug("[llm_drug_resolver] Local LLM call failed (%s): %s", type(e).__name__, e)

        return None

    def _parse_and_validate_json(self, text: str, original_query: str) -> Optional[dict[str, Any]]:
        """Phân tích cú pháp JSON, kiểm tra an toàn y tế và ép kiểu cấu trúc."""
        if not text:
            return None

        # Làm sạch markdown fence nếu có (vd: ```json ... ```)
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            raw_json = json.loads(cleaned)
            if not isinstance(raw_json, dict):
                return None

            # Kiểm tra xem có phải sản phẩm y tế/sức khỏe không
            is_health_product = raw_json.get("is_health_product", True)
            if not is_health_product:
                logger.info("[llm_drug_resolver] LLM rejected non-health term: %s", original_query)
                return None

            active_ing = raw_json.get("active_ingredient")
            if not active_ing or not str(active_ing).strip():
                return None

            # Chuẩn hóa tên hoạt chất
            active_clean = str(active_ing).strip()
            # Trần confidence an toàn y tế cho nguồn LLM: 0.75
            conf = min(0.75, float(raw_json.get("confidence_score", 0.75)))

            brand_result = raw_json.get("brand_name") or original_query

            return {
                "brand_name": brand_result,
                "is_supplement": bool(raw_json.get("is_supplement", False)),
                "active_ingredient": active_clean,
                "strength": raw_json.get("strength"),
                "category": raw_json.get("category") or "Sản phẩm hỗ trợ sức khỏe",
                "confidence_score": round(conf, 2),
                "notes": raw_json.get("notes"),
                "contraindications": raw_json.get("contraindications", []),
                "match_method": "ai_llm_inference",
                "source": "ai_llm_knowledge",
            }
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning("[llm_drug_resolver] Failed to parse LLM JSON (%s): %s", type(e).__name__, e)
            return None


# Singleton instance
llm_drug_resolver = LLMDrugResolver()
