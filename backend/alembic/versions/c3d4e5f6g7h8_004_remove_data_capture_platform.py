"""004_remove_data_capture_platform

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-09-01 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop scan_records table and its indexes (Remove Data Platform for Zero Image Persistence)."""
    # Drop indexes if table exists
    op.drop_index(op.f('ix_scan_records_user_id'), table_name='scan_records', if_exists=True)
    op.drop_index(op.f('ix_scan_records_dataset_version'), table_name='scan_records', if_exists=True)
    op.drop_index(op.f('ix_scan_records_is_dataset_candidate'), table_name='scan_records', if_exists=True)
    op.drop_index(op.f('ix_scan_records_status'), table_name='scan_records', if_exists=True)
    op.drop_index(op.f('ix_scan_records_image_sha256'), table_name='scan_records', if_exists=True)
    op.drop_index(op.f('ix_scan_records_request_id'), table_name='scan_records', if_exists=True)
    op.drop_index(op.f('ix_scan_records_id'), table_name='scan_records', if_exists=True)
    op.drop_table('scan_records', if_exists=True)


def downgrade() -> None:
    """Recreate scan_records table on rollback."""
    op.create_table(
        'scan_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('request_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('image_sha256', sa.String(length=64), nullable=False, server_default=''),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('quality_score', sa.Float(), nullable=False),
        sa.Column('quality_flags', sa.JSON(), nullable=False),
        sa.Column('raw_ocr_result', sa.JSON(), nullable=False),
        sa.Column('normalized_result', sa.JSON(), nullable=False),
        sa.Column('clinical_result', sa.JSON(), nullable=True),
        sa.Column('corrected_payload', sa.JSON(), nullable=True),
        sa.Column('is_dataset_candidate', sa.Boolean(), nullable=False),
        sa.Column('dataset_version', sa.String(length=50), nullable=True),
        sa.Column('dataset_tag', sa.String(length=100), nullable=True),
        sa.Column('version_metadata', sa.JSON(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('reviewed_by', sa.String(length=36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scan_records_id'), 'scan_records', ['id'], unique=False)
    op.create_index(op.f('ix_scan_records_request_id'), 'scan_records', ['request_id'], unique=False)
    op.create_index(op.f('ix_scan_records_image_sha256'), 'scan_records', ['image_sha256'], unique=False)
    op.create_index(op.f('ix_scan_records_status'), 'scan_records', ['status'], unique=False)
    op.create_index(op.f('ix_scan_records_is_dataset_candidate'), 'scan_records', ['is_dataset_candidate'], unique=False)
    op.create_index(op.f('ix_scan_records_dataset_version'), 'scan_records', ['dataset_version'], unique=False)
    op.create_index(op.f('ix_scan_records_user_id'), 'scan_records', ['user_id'], unique=False)
