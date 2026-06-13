"""add sensor AI and imu fields to sensor_data

Revision ID: e2b3c4d5addf
Revises: d7e2f3a4b5c6
Create Date: 2026-06-13 00:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "e2b3c4d5addf"
down_revision: Union[str, Sequence[str], None] = "d7e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sensor_data", sa.Column("gyro_x", sa.Float(), nullable=True))
    op.add_column("sensor_data", sa.Column("gyro_y", sa.Float(), nullable=True))
    op.add_column("sensor_data", sa.Column("gyro_z", sa.Float(), nullable=True))
    op.add_column("sensor_data", sa.Column("ir_value", sa.Integer(), nullable=True))
    op.add_column("sensor_data", sa.Column("step_count", sa.Integer(), nullable=True))
    op.add_column("sensor_data", sa.Column("heading_deg", sa.Float(), nullable=True))
    op.add_column(
        "sensor_data", sa.Column("est_zone", sa.String(length=100), nullable=True)
    )

    op.add_column(
        "sensor_data", sa.Column("ai_prediction", sa.String(length=16), nullable=True)
    )
    op.add_column("sensor_data", sa.Column("ai_confidence", sa.Float(), nullable=True))
    op.add_column(
        "sensor_data", sa.Column("ai_danger_votes", sa.Integer(), nullable=True)
    )
    op.add_column(
        "sensor_data", sa.Column("ai_if_vote", sa.String(length=16), nullable=True)
    )
    op.add_column(
        "sensor_data", sa.Column("ai_rf_vote", sa.String(length=16), nullable=True)
    )
    op.add_column(
        "sensor_data", sa.Column("ai_lstm_vote", sa.String(length=16), nullable=True)
    )
    op.add_column(
        "sensor_data", sa.Column("ai_svm_vote", sa.String(length=16), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("sensor_data", "ai_svm_vote")
    op.drop_column("sensor_data", "ai_lstm_vote")
    op.drop_column("sensor_data", "ai_rf_vote")
    op.drop_column("sensor_data", "ai_if_vote")
    op.drop_column("sensor_data", "ai_danger_votes")
    op.drop_column("sensor_data", "ai_confidence")
    op.drop_column("sensor_data", "ai_prediction")

    op.drop_column("sensor_data", "est_zone")
    op.drop_column("sensor_data", "heading_deg")
    op.drop_column("sensor_data", "step_count")
    op.drop_column("sensor_data", "ir_value")
    op.drop_column("sensor_data", "gyro_z")
    op.drop_column("sensor_data", "gyro_y")
    op.drop_column("sensor_data", "gyro_x")
