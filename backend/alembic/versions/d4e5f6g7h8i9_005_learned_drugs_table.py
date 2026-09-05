"""005_learned_drugs_table

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-09-05 10:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Tạo bảng learned_drugs (Stage 18)."""
    op.create_table(
        'learned_drugs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('brand_name', sa.String(length=255), nullable=False),
        sa.Column('brand_name_normalized', sa.String(length=255), nullable=False),
        sa.Column('active_ingredient', sa.String(length=500), nullable=True),
        sa.Column('strength', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=255), nullable=True),
        sa.Column('is_supplement', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default=sa.text('0.75')),
        sa.Column('verification_status', sa.String(length=50), nullable=False, server_default='PENDING_REVIEW'),
        sa.Column('hit_count', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('verified_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('contraindications', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('source', sa.String(length=100), nullable=False, server_default='ai_llm_inference'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_learned_drugs_id'), 'learned_drugs', ['id'], unique=False)
    op.create_index(op.f('ix_learned_drugs_brand_name_normalized'), 'learned_drugs', ['brand_name_normalized'], unique=True)
    op.create_index(op.f('ix_learned_drugs_verification_status'), 'learned_drugs', ['verification_status'], unique=False)


def downgrade() -> None:
    """Xóa bảng learned_drugs khi rollback."""
    op.drop_index(op.f('ix_learned_drugs_verification_status'), table_name='learned_drugs')
    op.drop_index(op.f('ix_learned_drugs_brand_name_normalized'), table_name='learned_drugs')
    op.drop_index(op.f('ix_learned_drugs_id'), table_name='learned_drugs')
    op.drop_table('learned_drugs')
