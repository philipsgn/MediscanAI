"""
Rate Limiter Configuration — slowapi.
Bảo vệ các endpoints xác thực nhạy cảm (/auth/login, /auth/register) chống tấn công Brute-force.

LƯU Ý VỀ GIỚI HẠN IN-MEMORY BACKEND:
Hiện tại hệ thống sử dụng in-memory backend của slowapi (đủ dùng cho 1 instance container).
Nếu sau này scale ngang hệ thống (horizontal scaling) với nhiều backend worker / container,
cần chuyển sang Redis backend (ví dụ: storage_uri="redis://redis:6379/1") để đồng bộ
quota rate-limit giữa các instances. Đây là giới hạn đã biết của in-memory backend.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    headers_enabled=False,
)


def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler khi vượt quá ngưỡng Rate Limit.
    Trả về mã HTTP 429 Too Many Requests kèm thông điệp tiếng Việt và header Retry-After.
    """
    # Trích xuất thời gian retry từ exception nếu có
    retry_after = "60"
    if hasattr(exc, "detail") and exc.detail:
        # slowapi mặc định format exc.detail chứa limit info
        pass

    response = JSONResponse(
        status_code=429,
        content={
            "detail": "Quá nhiều yêu cầu đăng nhập hoặc đăng ký từ địa chỉ của bạn. Vui lòng thử lại sau ít phút.",
            "error": "RATE_LIMIT_EXCEEDED",
        },
        headers={
            "Retry-After": retry_after,
        },
    )
    return response
