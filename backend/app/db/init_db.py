"""
Khởi tạo cấu trúc Database (Auto create tables nếu chưa tồn tại).
"""

import logging
from app.db.base import Base
from app.db.session import engine
import app.models  # noqa: F401 - ensure models are registered on Base.metadata

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Tự động tạo các bảng cơ sở dữ liệu trong sự kiện startup / lifespan."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Khởi tạo Database Schema thành công.")
    except Exception as exc:
        logger.error("Lỗi khi khởi tạo Database Schema: %s", exc)
