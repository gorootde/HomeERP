"""add entry_unit_key / entry_quantity to stock_entries

Revision ID: e6a1c9d4f207
Revises: d8e9f1a2b3c4
Create Date: 2026-09-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e6a1c9d4f207'
down_revision: Union[str, None] = 'd8e9f1a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('stock_entries') as batch_op:
        batch_op.add_column(sa.Column('entry_unit_key', sa.String(64), nullable=True))
        batch_op.add_column(sa.Column('entry_quantity', sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('stock_entries') as batch_op:
        batch_op.drop_column('entry_quantity')
        batch_op.drop_column('entry_unit_key')
