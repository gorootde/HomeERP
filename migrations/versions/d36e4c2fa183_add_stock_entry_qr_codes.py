"""add stock entry qr codes

Revision ID: d36e4c2fa183
Revises: c25f3a1db042
Create Date: 2026-03-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd36e4c2fa183'
down_revision: Union[str, None] = 'c25f3a1db042'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'stock_entry_qr_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=512), nullable=False),
        sa.Column('stock_entry_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['stock_entry_id'], ['stock_entries.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_stock_entry_qr_codes_id', 'stock_entry_qr_codes', ['id'])
    op.create_index('ix_stock_entry_qr_codes_code', 'stock_entry_qr_codes', ['code'])


def downgrade() -> None:
    op.drop_index('ix_stock_entry_qr_codes_code', 'stock_entry_qr_codes')
    op.drop_index('ix_stock_entry_qr_codes_id', 'stock_entry_qr_codes')
    op.drop_table('stock_entry_qr_codes')
