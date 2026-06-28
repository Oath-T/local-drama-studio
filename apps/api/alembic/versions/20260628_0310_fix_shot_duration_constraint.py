"""fix shot duration positive constraint

Revision ID: 20260628_0310
Revises: 20260628_0300
Create Date: 2026-06-28 03:10:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260628_0310"
down_revision: str | None = "20260628_0300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE shots SET duration_seconds = NULL WHERE duration_seconds <= 0")
    with op.batch_alter_table("shots") as batch_op:
        batch_op.create_check_constraint(
            "ck_shots_duration_seconds_positive",
            "duration_seconds IS NULL OR duration_seconds > 0",
        )


def downgrade() -> None:
    with op.batch_alter_table("shots") as batch_op:
        batch_op.drop_constraint("ck_shots_duration_seconds_positive", type_="check")
