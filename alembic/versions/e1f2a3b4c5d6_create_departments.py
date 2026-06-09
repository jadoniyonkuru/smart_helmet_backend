"""create departments table and add department_id to workers

Revision ID: e1f2a3b4c5d6
Revises: d7e2f3a4b5c6
Create Date: 2026-06-09 01:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd7e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'departments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_departments_name', 'departments', ['name'])

    op.add_column('workers', sa.Column(
        'department_id',
        UUID(as_uuid=True),
        sa.ForeignKey('departments.id', ondelete='SET NULL'),
        nullable=True,
    ))


def downgrade() -> None:
    op.drop_column('workers', 'department_id')
    op.drop_index('ix_departments_name', table_name='departments')
    op.drop_table('departments')
