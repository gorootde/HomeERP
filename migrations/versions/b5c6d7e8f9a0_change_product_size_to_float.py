"""change product size to float

Revision ID: b5c6d7e8f9a0
Revises: a1b2c3d4e5f6
Create Date: 2026-04-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b5c6d7e8f9a0'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('products') as batch_op:
        batch_op.alter_column(
            'size',
            existing_type=sa.String(64),
            type_=sa.Float(),
            nullable=True,
            postgresql_using='size::double precision',
        )


def downgrade() -> None:
    with op.batch_alter_table('products') as batch_op:
        batch_op.alter_column(
            'size',
            existing_type=sa.Float(),
            type_=sa.String(64),
            nullable=False,
            server_default='0',
        )
