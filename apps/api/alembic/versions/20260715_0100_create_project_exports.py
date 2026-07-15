"""create project exports

Revision ID: 20260715_0100
Revises: 20260714_0100
Create Date: 2026-07-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260715_0100"
down_revision: str | None = "20260714_0100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_exports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("current_stage", sa.String(length=120), nullable=False),
        sa.Column("clip_count", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("target_width", sa.Integer(), nullable=False),
        sa.Column("target_height", sa.Integer(), nullable=False),
        sa.Column("target_fps", sa.Integer(), nullable=False),
        sa.Column("video_codec", sa.String(length=40), nullable=False),
        sa.Column("output_format", sa.String(length=16), nullable=False),
        sa.Column("snapshot", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("output_media_asset_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft', 'ready', 'queued', 'running', 'completed', 'failed')",
            name="ck_project_exports_status",
        ),
        sa.CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="ck_project_exports_progress",
        ),
        sa.CheckConstraint("clip_count >= 0", name="ck_project_exports_clip_count"),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_project_exports_duration",
        ),
        sa.CheckConstraint(
            "target_width BETWEEN 256 AND 3840 AND target_width % 2 = 0",
            name="ck_project_exports_width",
        ),
        sa.CheckConstraint(
            "target_height BETWEEN 256 AND 3840 AND target_height % 2 = 0",
            name="ck_project_exports_height",
        ),
        sa.CheckConstraint("target_fps BETWEEN 1 AND 60", name="ck_project_exports_fps"),
        sa.CheckConstraint("video_codec IN ('libx264')", name="ck_project_exports_codec"),
        sa.CheckConstraint("output_format IN ('mp4')", name="ck_project_exports_format"),
        sa.ForeignKeyConstraint(
            ["output_media_asset_id"],
            ["media_assets.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_exports_project_id", "project_exports", ["project_id"])
    op.create_index("ix_project_exports_status", "project_exports", ["status"])
    op.create_index(
        "ix_project_exports_output_media_asset_id",
        "project_exports",
        ["output_media_asset_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_exports_output_media_asset_id", table_name="project_exports")
    op.drop_index("ix_project_exports_status", table_name="project_exports")
    op.drop_index("ix_project_exports_project_id", table_name="project_exports")
    op.drop_table("project_exports")
