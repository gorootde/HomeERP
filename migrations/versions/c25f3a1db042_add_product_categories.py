"""add product categories

Revision ID: c25f3a1db042
Revises: b14d2e8fa901
Create Date: 2026-03-23 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c25f3a1db042'
down_revision: Union[str, None] = 'b14d2e8fa901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'product_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('min_stock_quantity', sa.Float(), nullable=True),
        sa.Column('min_stock_unit_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['min_stock_unit_id'], ['units.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_product_categories_id', 'product_categories', ['id'])

    with op.batch_alter_table('products') as batch_op:
        batch_op.add_column(sa.Column('category_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_products_category_id', 'product_categories', ['category_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('products') as batch_op:
        batch_op.drop_constraint('fk_products_category_id', type_='foreignkey')
        batch_op.drop_column('category_id')

    op.drop_index('ix_product_categories_id', 'product_categories')
    op.drop_table('product_categories')
