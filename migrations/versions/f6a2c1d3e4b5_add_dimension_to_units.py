"""add dimension to units

Revision ID: f6a2c1d3e4b5
Revises: e6a1c9d4f207
Create Date: 2026-09-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from backend.unit_inference import guess_dimension_from_abbr

revision: str = 'f6a2c1d3e4b5'
down_revision: Union[str, None] = 'e6a1c9d4f207'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('units') as batch_op:
        batch_op.add_column(sa.Column('dimension', sa.String(16), nullable=True))

    units = sa.table(
        'units',
        sa.column('id', sa.Integer),
        sa.column('abbreviation', sa.String),
        sa.column('dimension', sa.String),
    )
    conn = op.get_bind()
    for row in conn.execute(sa.select(units.c.id, units.c.abbreviation)):
        dim = guess_dimension_from_abbr(row.abbreviation or '')
        if dim:
            conn.execute(
                units.update().where(units.c.id == row.id).values(dimension=dim)
            )


def downgrade() -> None:
    with op.batch_alter_table('units') as batch_op:
        batch_op.drop_column('dimension')
