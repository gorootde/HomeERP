"""add unit_id to products

Revision ID: b14d2e8fa901
Revises: a03c4b9cf623
Create Date: 2026-03-23 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b14d2e8fa901'
down_revision: Union[str, None] = 'a03c4b9cf623'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('products') as batch_op:
        batch_op.add_column(sa.Column('unit_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_products_unit_id', 'units', ['unit_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('products') as batch_op:
        batch_op.drop_constraint('fk_products_unit_id', type_='foreignkey')
        batch_op.drop_column('unit_id')
