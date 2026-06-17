from collections.abc import Sequence


revision: str = "0002_add_analytics_report"
down_revision: str | None = "0001_sessions_measurements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
