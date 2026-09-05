"""
Pytest configuration & Async Database Fixtures cho Mediscan AI test suite.
Sử dụng in-memory SQLite (aiosqlite) để đảm bảo 100% test độc lập, chạy tức thì không cần Postgres.
"""

import asyncio
from typing import AsyncGenerator
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
import app.models  # noqa: F401

import os
import tempfile
from pathlib import Path
from sqlalchemy.pool import StaticPool

_temp_test_db = tempfile.NamedTemporaryFile(suffix="_mediscan_test.db", delete=False)
_temp_test_db.close()
_temp_db_path = _temp_test_db.name.replace("\\", "/")

TEST_DATABASE_URL = f"sqlite+aiosqlite:///{_temp_db_path}"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Khởi tạo database schema cho toàn bộ test session."""
    async def _init_models():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init_models())
    asyncio.run(test_engine.dispose())

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestingSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    import app.db.session
    original_session_local = app.db.session.AsyncSessionLocal
    app.db.session.AsyncSessionLocal = TestingSessionLocal
    fastapi_app.dependency_overrides[get_db] = _override_get_db
    yield
    app.db.session.AsyncSessionLocal = original_session_local
    fastapi_app.dependency_overrides.clear()
    try:
        if os.path.exists(_temp_db_path):
            os.remove(_temp_db_path)
    except Exception:
        pass
