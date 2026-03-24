"""add settings table

Revision ID: e47b5d3ca291
Revises: d36e4c2fa183
Create Date: 2026-03-24 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e47b5d3ca291'
down_revision: Union[str, None] = 'd36e4c2fa183'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'settings',
        sa.Column('key',   sa.String(length=128),  nullable=False),
        sa.Column('value', sa.String(length=1024), nullable=False),
        sa.PrimaryKeyConstraint('key'),
    )


def downgrade() -> None:
    op.drop_table('settings')
