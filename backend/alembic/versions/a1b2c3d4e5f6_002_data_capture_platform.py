"""002_data_capture_platform

Revision ID: a1b2c3d4e5f6
Revises: cbaf82f604c3
Create Date: 2026-08-31 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'cbaf82f604c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to include scan_records for Data-Centric AI Platform."""
    op.create_table(
        'scan_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('request_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('image_ref', sa.String(length=255), nullable=False),
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
    op.create_index(op.f('ix_scan_records_image_ref'), 'scan_records', ['image_ref'], unique=False)
    op.create_index(op.f('ix_scan_records_status'), 'scan_records', ['status'], unique=False)
    op.create_index(op.f('ix_scan_records_is_dataset_candidate'), 'scan_records', ['is_dataset_candidate'], unique=False)
    op.create_index(op.f('ix_scan_records_dataset_version'), 'scan_records', ['dataset_version'], unique=False)
    op.create_index(op.f('ix_scan_records_user_id'), 'scan_records', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_scan_records_user_id'), table_name='scan_records')
    op.drop_index(op.f('ix_scan_records_dataset_version'), table_name='scan_records')
    op.drop_index(op.f('ix_scan_records_is_dataset_candidate'), table_name='scan_records')
    op.drop_index(op.f('ix_scan_records_status'), table_name='scan_records')
    op.drop_index(op.f('ix_scan_records_image_ref'), table_name='scan_records')
    op.drop_index(op.f('ix_scan_records_request_id'), table_name='scan_records')
    op.drop_index(op.f('ix_scan_records_id'), table_name='scan_records')
    op.drop_table('scan_records')
