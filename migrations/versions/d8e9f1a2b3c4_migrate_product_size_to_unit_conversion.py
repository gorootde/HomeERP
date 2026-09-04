"""migrate product size to named unit conversion

Backfills each Product.size value into a product_unit_conversions row named
"Stück" (skipping products without a unit_id, since base_unit_id is NOT NULL
on that table), repoints entry_unit_key from the old 'stueck' sentinel to the
new 'puc_<id>', then drops the now-unused products.size column.

Revision ID: d8e9f1a2b3c4
Revises: c7f2a9e1b3d4
Create Date: 2026-09-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd8e9f1a2b3c4'
down_revision: Union[str, None] = 'c7f2a9e1b3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PIECE_UNIT_NAME = 'Stück'


def upgrade() -> None:
    bind = op.get_bind()
    meta = sa.MetaData()
    products = sa.Table('products', meta, autoload_with=bind)
    conversions = sa.Table('product_unit_conversions', meta, autoload_with=bind)

    rows = bind.execute(
        sa.select(products.c.id, products.c.size, products.c.unit_id, products.c.entry_unit_key)
        .where(products.c.size.isnot(None))
    ).fetchall()

    for row in rows:
        if row.unit_id is None:
            continue

        existing = bind.execute(
            sa.select(conversions.c.id)
            .where(conversions.c.product_id == row.id)
            .where(conversions.c.unit_name == PIECE_UNIT_NAME)
        ).fetchone()

        if existing is not None:
            new_conv_id = existing.id
        else:
            result = bind.execute(
                conversions.insert().values(
                    product_id=row.id,
                    unit_name=PIECE_UNIT_NAME,
                    base_unit_id=row.unit_id,
                    factor=row.size,
                )
            )
            new_conv_id = result.inserted_primary_key[0]

        if row.entry_unit_key == 'stueck':
            bind.execute(
                products.update()
                .where(products.c.id == row.id)
                .values(entry_unit_key=f'puc_{new_conv_id}')
            )

    with op.batch_alter_table('products') as batch_op:
        batch_op.drop_column('size')


def downgrade() -> None:
    bind = op.get_bind()
    meta = sa.MetaData()

    with op.batch_alter_table('products') as batch_op:
        batch_op.add_column(sa.Column('size', sa.Float(), nullable=True))

    meta.clear()
    products = sa.Table('products', meta, autoload_with=bind)
    conversions = sa.Table('product_unit_conversions', meta, autoload_with=bind)

    piece_convs = bind.execute(
        sa.select(conversions.c.id, conversions.c.product_id, conversions.c.factor)
        .where(conversions.c.unit_name == PIECE_UNIT_NAME)
    ).fetchall()

    for conv in piece_convs:
        bind.execute(
            products.update()
            .where(products.c.id == conv.product_id)
            .where(products.c.entry_unit_key == f'puc_{conv.id}')
            .values(entry_unit_key='stueck')
        )
        bind.execute(
            products.update()
            .where(products.c.id == conv.product_id)
            .values(size=conv.factor)
        )
