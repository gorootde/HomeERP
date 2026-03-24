"""add product_unit_conversions table

Revision ID: f58b6e4db392
Revises: e47b5d3ca291
Create Date: 2026-03-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f58b6e4db392'
down_revision: Union[str, None] = 'e47b5d3ca291'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'product_unit_conversions',
        sa.Column('id',           sa.Integer(),     nullable=False),
        sa.Column('product_id',   sa.Integer(),     nullable=False),
        sa.Column('unit_name',    sa.String(64),    nullable=False),
        sa.Column('base_unit_id', sa.Integer(),     nullable=False),
        sa.Column('factor',       sa.Float(),       nullable=False),
        sa.ForeignKeyConstraint(['product_id'],   ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['base_unit_id'], ['units.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id', 'unit_name', name='uq_product_unit_name'),
    )
    op.create_index('ix_product_unit_conversions_id', 'product_unit_conversions', ['id'])


def downgrade() -> None:
    op.drop_index('ix_product_unit_conversions_id', table_name='product_unit_conversions')
    op.drop_table('product_unit_conversions')
