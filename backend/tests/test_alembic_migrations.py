"""
Unit Tests for Alembic Database Migrations (Stage 9/10).
Kiểm thử:
1. Fresh database volume: Alembic upgrade head tạo đủ 4 bảng (users, user_profiles, scan_histories, reminders) + alembic_version.
2. Existing database volume: Database đã có bảng sẵn từ trước được stamp head an toàn mà không gây lỗi 'already exists'.
3. Khả năng downgrade / upgrade schema mượt mà.
"""

import os
import tempfile
from pathlib import Path
import pytest
from sqlalchemy import inspect, Table, Column, String, MetaData
from sqlalchemy.ext.asyncio import create_async_engine
from alembic.config import Config
from alembic import command


@pytest.fixture
def temp_db_config():
    """Tạo file SQLite tạm thời và Alembic Config để kiểm thử migration cô lập."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_migration.db"
        db_url = f"sqlite+aiosqlite:///{db_file}"

        backend_dir = Path(__file__).resolve().parent.parent
        ini_path = backend_dir / "alembic.ini"

        alembic_cfg = Config(str(ini_path))
        alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        old_db_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = db_url

        yield alembic_cfg, db_url

        if old_db_url:
            os.environ["DATABASE_URL"] = old_db_url
        else:
            os.environ.pop("DATABASE_URL", None)


@pytest.mark.asyncio
async def test_alembic_fresh_database_upgrade_head(temp_db_config):
    """Test 1: Khởi tạo database mới hoàn toàn -> alembic upgrade head tạo đủ 4 bảng."""
    alembic_cfg, db_url = temp_db_config

    # 1. Chạy upgrade head
    command.upgrade(alembic_cfg, "head")

    # 2. Kiểm tra các bảng đã được tạo qua AsyncEngine
    engine = create_async_engine(db_url)
    try:
        def _get_tables(conn):
            return set(inspect(conn).get_table_names())

        def _get_columns(conn, table_name):
            return {c["name"] for c in inspect(conn).get_columns(table_name)}

        async with engine.connect() as conn:
            tables = await conn.run_sync(_get_tables)
            expected_tables = {"users", "user_profiles", "user_medications", "scan_histories", "reminders", "alembic_version"}
            assert expected_tables.issubset(tables), f"Thiếu bảng trong DB: {expected_tables - tables}"
            assert "scan_records" not in tables, "Bảng scan_records không được phép tồn tại trên head!"

            user_cols = await conn.run_sync(_get_columns, "users")
            assert {"id", "username", "email", "hashed_password", "is_profile_completed"}.issubset(user_cols)

            profile_cols = await conn.run_sync(_get_columns, "user_profiles")
            assert {"id", "user_id", "age", "conditions", "allergies"}.issubset(profile_cols)

            med_cols = await conn.run_sync(_get_columns, "user_medications")
            assert {"id", "user_id", "brand_name", "is_active"}.issubset(med_cols)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_alembic_existing_database_stamp_head(temp_db_config):
    """Test 2: Database đã có sẵn bảng users từ trước -> stamp head không gây lỗi conflict."""
    alembic_cfg, db_url = temp_db_config

    # Giả lập database cũ đã có bảng users (chưa có alembic_version)
    engine = create_async_engine(db_url)
    metadata = MetaData()
    legacy_users = Table(
        "users", metadata,
        Column("id", String(36), primary_key=True),
        Column("username", String(50), nullable=False),
        Column("email", String(255), nullable=False),
    )

    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

    try:
        def _get_tables(conn):
            return inspect(conn).get_table_names()

        async with engine.connect() as conn:
            tables_before = await conn.run_sync(_get_tables)
            assert "users" in tables_before
            assert "alembic_version" not in tables_before

        # Chạy stamp head
        command.stamp(alembic_cfg, "head")

        # Kiểm tra sau khi stamp
        async with engine.connect() as conn:
            tables_after = await conn.run_sync(_get_tables)
            assert "users" in tables_after
            assert "alembic_version" in tables_after
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_alembic_downgrade_and_upgrade_cycle(temp_db_config):
    """Test 3: Kiểm tra vòng lặp upgrade -> downgrade base -> upgrade head."""
    alembic_cfg, db_url = temp_db_config

    # 1. Upgrade
    command.upgrade(alembic_cfg, "head")

    # 2. Downgrade về base (xóa sạch bảng)
    command.downgrade(alembic_cfg, "base")

    engine = create_async_engine(db_url)
    try:
        def _get_tables(conn):
            return inspect(conn).get_table_names()

        async with engine.connect() as conn:
            tables = await conn.run_sync(_get_tables)
            assert "users" not in tables
            assert "user_profiles" not in tables

        # 3. Upgrade lại lên head
        command.upgrade(alembic_cfg, "head")
        async with engine.connect() as conn:
            tables_rebuilt = await conn.run_sync(_get_tables)
            assert "users" in tables_rebuilt
            assert "user_profiles" in tables_rebuilt
    finally:
        await engine.dispose()
