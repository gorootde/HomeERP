"""add entry_unit_key to products

Revision ID: a1b2c3d4e5f6
Revises: f58b6e4db392
Create Date: 2026-03-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f58b6e4db392'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('products', sa.Column('entry_unit_key', sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column('products', 'entry_unit_key')
