"""Add source column to Entity

Revision ID: a6d2e17ecfb1
Revises:
Create Date: 2024-10-27 18:43:22.039866

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import Column, String

from timelink.migrations import column_exists


# revision identifiers, used by Alembic.
revision: str = 'a6d2e17ecfb1'
down_revision: Union[str, None] = "89f407c298c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not column_exists('entities', 'the_source', op):
        op.add_column('entities', Column('the_source', String, nullable=True))


def downgrade() -> None:
    if column_exists('entities', 'the_source', op):
        op.drop_column('entities', 'the_source')
