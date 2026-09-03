"""003_user_medications_and_reminder_link

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-31 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_medications table and add medication_id to reminders."""
    op.create_table(
        'user_medications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('brand_name', sa.String(length=255), nullable=False),
        sa.Column('active_ingredient', sa.String(length=255), nullable=True),
        sa.Column('strength', sa.String(length=100), nullable=True),
        sa.Column('dosage_instruction', sa.String(length=255), nullable=True),
        sa.Column('duration_days', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_user_medications_id'), 'user_medications', ['id'], unique=False)
    op.create_index(op.f('ix_user_medications_user_id'), 'user_medications', ['user_id'], unique=False)

    # Thêm medication_id vào reminders (hỗ trợ cả SQLite batch mode và PostgreSQL)
    with op.batch_alter_table('reminders') as batch_op:
        batch_op.add_column(sa.Column('medication_id', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            'fk_reminders_medication_id',
            'user_medications',
            ['medication_id'],
            ['id'],
            ondelete='CASCADE',
        )
        batch_op.create_index(op.f('ix_reminders_medication_id'), ['medication_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('reminders') as batch_op:
        batch_op.drop_index(op.f('ix_reminders_medication_id'))
        batch_op.drop_constraint('fk_reminders_medication_id', type_='foreignkey')
        batch_op.drop_column('medication_id')

    op.drop_index(op.f('ix_user_medications_user_id'), table_name='user_medications')
    op.drop_index(op.f('ix_user_medications_id'), table_name='user_medications')
    op.drop_table('user_medications')
