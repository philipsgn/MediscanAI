"""
Database Initialization & Alembic Migration Lifecycle Runner.
Tự động áp dụng Alembic migrations (upgrade head) khi khởi động backend.
Hỗ trợ tương thích ngược cho cả fresh database volume và existing database volume.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from app.db.session import engine
from app.db.base import Base
from app.core.config import settings
import app.models  # noqa: F401 - đảm bảo models được nạp vào metadata

logger = logging.getLogger(__name__)


def _inspect_tables(connection) -> List[str]:
    """Sync helper lấy danh sách bảng qua Connection."""
    return inspect(connection).get_table_names()


async def init_db() -> None:
    """Tự động kiểm tra và nâng cấp schema cơ sở dữ liệu qua Alembic trong sự kiện startup."""
    if "sqlite" in settings.DATABASE_URL and ":memory:" in settings.DATABASE_URL:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return

    backend_dir = Path(__file__).resolve().parent.parent.parent
    ini_candidates = [
        backend_dir / "alembic.ini",
        backend_dir.parent / "alembic.ini",
    ]
    ini_path: Optional[str] = None
    for cand in ini_candidates:
        if cand.exists():
            ini_path = str(cand)
            break

    if not ini_path:
        logger.warning("Không tìm thấy file alembic.ini -> Fallback sang create_all.")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return

    alembic_cfg = Config(ini_path)
    script_loc = backend_dir / "alembic"
    if script_loc.exists():
        alembic_cfg.set_main_option("script_location", str(script_loc))

    try:
        async with engine.connect() as conn:
            tables = await conn.run_sync(_inspect_tables)
            has_alembic_version = "alembic_version" in tables
            has_existing_tables = "users" in tables

        if not has_alembic_version and has_existing_tables:
            logger.info("Phát hiện Database đã có sẵn schema -> Đóng dấu Alembic stamp head...")
            await asyncio.to_thread(command.stamp, alembic_cfg, "head")
        else:
            logger.info("Thực thi Alembic upgrade head...")
            await asyncio.to_thread(command.upgrade, alembic_cfg, "head")

        logger.info("Alembic Database Migration hoàn tất thành công.")
    except Exception as exc:
        logger.error("Lỗi khi khởi tạo Database Schema qua Alembic: %s", exc)
