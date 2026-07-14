"""add keyframe task purpose

Revision ID: 20260714_0100
Revises: 20260704_0500
Create Date: 2026-07-14 01:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260714_0100"
down_revision: str | None = "20260704_0500"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "keyframe_generation_tasks",
        sa.Column(
            "purpose",
            sa.String(length=24),
            nullable=False,
            server_default="concept",
        ),
    )
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE keyframe_generation_tasks
            SET purpose = 'first_frame'
            WHERE name LIKE '首帧草稿%'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE keyframe_generation_tasks
            SET purpose = 'end_frame'
            WHERE name LIKE '尾帧草稿%'
            """
        )
    )
    with op.batch_alter_table("keyframe_generation_tasks") as batch_op:
        batch_op.create_check_constraint(
            "ck_keyframe_generation_tasks_purpose",
            "purpose IN ('first_frame', 'end_frame', 'concept', 'reference')",
        )
        batch_op.create_index(
            "ix_keyframe_generation_tasks_shot_purpose",
            ["shot_id", "purpose", "created_at", "id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("keyframe_generation_tasks") as batch_op:
        batch_op.drop_index("ix_keyframe_generation_tasks_shot_purpose")
        batch_op.drop_constraint("ck_keyframe_generation_tasks_purpose", type_="check")
        batch_op.drop_column("purpose")
