"""
Unit Tests for Stage 17: LLM Medical Knowledge Fallback & Dynamic Learning Cache.
Kiểm tra:
1. JSON Parser & Medical Guardrails của LLMDrugResolver.
2. Từ chối chuỗi rác, không tạo ảo giác y khoa (Zero-Hallucination).
3. Cơ chế Dynamic Learning Cache: Ghi vào cache và tra cứu lại đạt O(1) < 1ms.
4. Tích hợp Tier 4 Fallback trong NormalizationService.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.schemas import DrugItem
from app.services.drug_database import drug_database
from app.services.llm_drug_resolver import llm_drug_resolver
from app.services.normalization_service import normalization_service


def test_llm_resolver_parse_valid_supplement():
    """Kiểm tra parse JSON hợp lệ cho Thực phẩm bảo vệ sức khỏe (Tendoactive)."""
    raw_response = """
    ```json
    {
      "is_health_product": true,
      "brand_name": "Tendoactive",
      "is_supplement": true,
      "active_ingredient": "Mucopolysaccharides / Collagen Type I / Vitamin C",
      "strength": "430mg / 40mg / 20mg",
      "category": "Thực phẩm bảo vệ sức khỏe - Hỗ trợ gân khớp",
      "confidence_score": 0.85,
      "notes": "Chế phẩm Bioiberica hỗ trợ phục hồi cấu trúc gân",
      "contraindications": ["Dị ứng thành phần collagen"]
    }
    ```
    """
    res = llm_drug_resolver._parse_and_validate_json(raw_response, "tendoactive")
    assert res is not None
    assert res["brand_name"] == "Tendoactive"
    assert res["is_supplement"] is True
    assert res["active_ingredient"] == "Mucopolysaccharides / Collagen Type I / Vitamin C"
    # An toàn y tế: trần confidence score tối đa 0.75
    assert res["confidence_score"] <= 0.75
    assert res["match_method"] == "ai_llm_inference"
    assert "Dị ứng thành phần collagen" in res["contraindications"]


def test_llm_resolver_rejects_non_health_and_garbage():
    """Kiểm tra từ chối chuỗi không phải sản phẩm sức khỏe (Zero Hallucination)."""
    # 1. LLM phản hồi is_health_product: false
    negative_response = '{"is_health_product": false, "brand_name": "thùng carton", "active_ingredient": null}'
    res1 = llm_drug_resolver._parse_and_validate_json(negative_response, "thùng carton")
    assert res1 is None

    # 2. Phản hồi thiếu active_ingredient
    empty_ing = '{"is_health_product": true, "brand_name": "Test", "active_ingredient": ""}'
    res2 = llm_drug_resolver._parse_and_validate_json(empty_ing, "Test")
    assert res2 is None

    # 3. Phản hồi JSON lỗi cú pháp
    res3 = llm_drug_resolver._parse_and_validate_json("not valid json at all", "invalid")
    assert res3 is None


def test_dynamic_learning_cache_write_and_retrieve():
    """Kiểm tra cơ chế lưu trữ Dynamic Cache và truy vấn tức thời O(1)."""
    test_drug = {
        "brand_name": "Tendoactive Test",
        "active_ingredient": "Mucopolysaccharides / Collagen Type I",
        "strength": "430mg",
        "category": "Thực phẩm bảo vệ sức khỏe",
        "is_supplement": True,
        "notes": "Test cache entry",
        "warnings": [],
        "source": "ai_llm_knowledge",
    }

    # Lưu vào cache
    drug_database.save_learned_drug(test_drug)

    # 1. Truy vấn chính xác tên đầy đủ
    found_exact = drug_database.find_by_brand_exact("tendoactive test")
    assert found_exact is not None
    assert found_exact["active_ingredient"] == "Mucopolysaccharides / Collagen Type I"
    assert found_exact["is_supplement"] is True

    # 2. Truy vấn theo base brand (loại bỏ hàm lượng kèm theo)
    found_with_strength = drug_database.find_by_brand_exact("Tendoactive Test 430mg")
    assert found_with_strength is not None
    assert found_with_strength["active_ingredient"] == "Mucopolysaccharides / Collagen Type I"

    # 3. Truy vấn fuzzy
    found_fuzzy = drug_database.find_by_brand_fuzzy("tendoactive tes")
    assert found_fuzzy is not None


@pytest.mark.asyncio
async def test_normalization_tier4_llm_fallback_end_to_end():
    """Kiểm tra end-to-end: Thuốc lạ/TPCN MISS ở Tier 1-3 -> gọi Tier 4 LLM -> lưu Cache."""
    test_brand = "Tendoactive Special Formula"
    # Đảm bảo thương hiệu chưa nằm trong cache trước khi test
    drug_database.learned_brand_to_drug.pop(test_brand.lower(), None)
    drug_database.learned_brand_to_drug.pop("tendoactive special", None)

    mock_llm_result = {
        "brand_name": test_brand,
        "is_supplement": True,
        "active_ingredient": "Mucopolysaccharides / Collagen Type I / Vitamin C",
        "strength": "430mg / 40mg / 20mg",
        "category": "Thực phẩm bảo vệ sức khỏe - Khớp",
        "confidence_score": 0.75,
        "notes": "Hỗ trợ phục hồi cấu trúc gân",
        "contraindications": ["Dị ứng thành phần collagen"],
        "match_method": "ai_llm_inference",
        "source": "ai_llm_knowledge",
    }

    raw_item = DrugItem(
        brand_name=test_brand,
        strength="430mg",
        confidence_score=0.6,
    )

    try:
        with patch.object(llm_drug_resolver, "resolve_drug_with_llm", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.return_value = mock_llm_result

            normalized = await normalization_service.normalize_drug_item_full(raw_item)

            # Khẳng định phân giải thành công từ Tier 4
            assert normalized.match_method == "ai_llm_inference"
            assert normalized.active_ingredient == "Mucopolysaccharides / Collagen Type I / Vitamin C"
            assert normalized.is_supplement is True
            assert normalized.confidence_score <= 0.75
            assert normalized.is_verified is False  # Bắt buộc qua bước HITL

            # Xác nhận đã tự động lưu vào Dynamic Learning Cache
            cached = drug_database.find_by_brand_exact(test_brand)
            assert cached is not None
            assert cached["active_ingredient"] == "Mucopolysaccharides / Collagen Type I / Vitamin C"

            # Lần gọi tiếp theo: normalize_drug_item chạy sync O(1) trúng ngay Cache Tier 2.5
            second_item = DrugItem(brand_name=test_brand)
            second_normalized = normalization_service.normalize_drug_item(second_item)
            assert second_normalized.active_ingredient == "Mucopolysaccharides / Collagen Type I / Vitamin C"
    finally:
        # Dọn dẹp cache sau khi test
        drug_database.learned_brand_to_drug.pop(test_brand.lower(), None)
        drug_database.learned_brand_to_drug.pop("tendoactive special", None)


