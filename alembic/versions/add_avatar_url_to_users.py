"""add avatar_url to users

Revision ID: c3f1a2b4d5e6
Revises: 500ec7fd7048
Create Date: 2026-06-09 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c3f1a2b4d5e6'
down_revision: Union[str, Sequence[str], None] = '500ec7fd7048'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'avatar_url')
