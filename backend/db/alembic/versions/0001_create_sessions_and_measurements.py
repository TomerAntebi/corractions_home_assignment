from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0001_sessions_measurements"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("vehicle_id", sa.String(length=255), nullable=False),
        sa.Column("driver_id", sa.String(length=255), nullable=False),
        sa.Column("recording_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_session_id", "sessions", ["session_id"], unique=True)

    op.create_table(
        "measurements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("speed", sa.Float(), nullable=True),
        sa.Column("wheel_angle", sa.Float(), nullable=True),
        sa.Column("reverse_state", sa.Boolean(), nullable=True),
        sa.Column("raw_timestamp", sa.String(), nullable=True),
        sa.Column("raw_speed", sa.String(), nullable=True),
        sa.Column("raw_wheel_angle", sa.String(), nullable=True),
        sa.Column("raw_reverse_state", sa.String(), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.Column(
            "validation_errors",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_outlier", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_measurements_session_id", "measurements", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_measurements_session_id", table_name="measurements")
    op.drop_table("measurements")
    op.drop_index("ix_sessions_session_id", table_name="sessions")
    op.drop_table("sessions")
