"""add stock movements audit log

Revision ID: c7f2a9e1b3d4
Revises: b5c6d7e8f9a0
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7f2a9e1b3d4'
down_revision: Union[str, None] = 'b5c6d7e8f9a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'stock_movements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stock_entry_id', sa.Integer(), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('vault_id', sa.Integer(), nullable=True),
        sa.Column('delta', sa.Float(), nullable=False),
        sa.Column('quantity_before', sa.Float(), nullable=False),
        sa.Column('quantity_after', sa.Float(), nullable=False),
        sa.Column('reason', sa.String(length=32), nullable=False),
        sa.Column('note', sa.String(length=255), nullable=True),
        sa.Column('entry_snapshot', sa.JSON(), nullable=True),
        sa.Column('undone', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['stock_entry_id'], ['stock_entries.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['vault_id'], ['vaults.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_stock_movements_id', 'stock_movements', ['id'])
    op.create_index('ix_stock_movements_stock_entry_id', 'stock_movements', ['stock_entry_id'])
    op.create_index('ix_stock_movements_product_id', 'stock_movements', ['product_id'])
    op.create_index('ix_stock_movements_created_at', 'stock_movements', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_stock_movements_created_at', 'stock_movements')
    op.drop_index('ix_stock_movements_product_id', 'stock_movements')
    op.drop_index('ix_stock_movements_stock_entry_id', 'stock_movements')
    op.drop_index('ix_stock_movements_id', 'stock_movements')
    op.drop_table('stock_movements')
