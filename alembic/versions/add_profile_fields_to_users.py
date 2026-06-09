"""add profile fields to users

Revision ID: d7e2f3a4b5c6
Revises: c3f1a2b4d5e6
Create Date: 2026-06-09 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd7e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c3f1a2b4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('phone', sa.String(length=30), nullable=True))
    op.add_column('users', sa.Column('location', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('department', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('bio', sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'bio')
    op.drop_column('users', 'department')
    op.drop_column('users', 'location')
    op.drop_column('users', 'phone')
