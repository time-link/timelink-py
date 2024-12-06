"""Add source column to Entity

Revision ID: a6d2e17ecfb1
Revises:
Create Date: 2024-10-27 18:43:22.039866

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import Column, String


# revision identifiers, used by Alembic.
revision: str = 'a6d2e17ecfb1'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('entities', Column('the_source', String, nullable=True))


def downgrade() -> None:
    op.drop_column('entities', 'the_source')
