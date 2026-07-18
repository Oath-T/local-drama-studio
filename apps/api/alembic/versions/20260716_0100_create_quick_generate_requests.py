"""create quick generate requests

Revision ID: 20260716_0100
Revises: 20260715_0200
Create Date: 2026-07-16 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260716_0100"
down_revision: str | None = "20260715_0200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quick_generate_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("shot_id", sa.String(length=36), nullable=False),
        sa.Column("mode", sa.String(length=24), nullable=False),
        sa.Column("request_id", sa.String(length=120), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("run_id", sa.String(length=36), nullable=True),
        sa.Column("run_type", sa.String(length=24), nullable=True),
        sa.Column("response_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "mode IN ('first_frame', 'end_frame', 'video')",
            name="ck_quick_generate_requests_mode",
        ),
        sa.CheckConstraint(
            "run_type IS NULL OR run_type IN ('keyframe', 'video')",
            name="ck_quick_generate_requests_run_type",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shot_id"], ["shots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "shot_id",
            "mode",
            "request_id",
            name="uq_quick_generate_requests_request",
        ),
    )
    op.create_index(
        "ix_quick_generate_requests_project_id",
        "quick_generate_requests",
        ["project_id"],
    )
    op.create_index(
        "ix_quick_generate_requests_shot_id",
        "quick_generate_requests",
        ["shot_id"],
    )
    op.create_index(
        "ix_quick_generate_requests_run_id",
        "quick_generate_requests",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_quick_generate_requests_run_id", table_name="quick_generate_requests")
    op.drop_index("ix_quick_generate_requests_shot_id", table_name="quick_generate_requests")
    op.drop_index("ix_quick_generate_requests_project_id", table_name="quick_generate_requests")
    op.drop_table("quick_generate_requests")
