"""Add extra_info to Entity

Revision ID: 48dd68d06c60
Revises: a6d2e17ecfb1
Create Date: 2024-10-27 18:51:35.393732

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import Column, JSON

# revision identifiers, used by Alembic.
revision: str = '48dd68d06c60'
down_revision: Union[str, None] = 'a6d2e17ecfb1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('entities', Column('extra_info', JSON, nullable=True))


def downgrade() -> None:
    op.drop_column('entities', 'extra_info')
