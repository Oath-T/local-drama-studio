"""create video generation tasks

Revision ID: 20260704_0400
Revises: 20260629_0300
Create Date: 2026-07-04 04:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260704_0400"
down_revision: str | None = "20260629_0300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("media_assets") as batch_op:
        batch_op.alter_column(
            "thumbnail_relative_path",
            existing_type=sa.String(length=800),
            nullable=True,
        )

    op.create_table(
        "video_generation_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("shot_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("input_media_asset_id", sa.String(length=36), nullable=True),
        sa.Column("source_keyframe_output_id", sa.String(length=36), nullable=True),
        sa.Column("source_keyframe_task_id", sa.String(length=36), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("negative_prompt", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("fps", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("motion_strength", sa.Float(), nullable=True),
        sa.Column("camera_motion", sa.String(length=200), nullable=True),
        sa.Column("workflow_id", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'ready')", name="ck_video_generation_tasks_status"),
        sa.CheckConstraint("duration_seconds > 0", name="ck_video_generation_tasks_duration"),
        sa.CheckConstraint("fps > 0", name="ck_video_generation_tasks_fps"),
        sa.CheckConstraint(
            "width BETWEEN 256 AND 2048 AND width % 8 = 0",
            name="ck_video_generation_tasks_width",
        ),
        sa.CheckConstraint(
            "height BETWEEN 256 AND 2048 AND height % 8 = 0",
            name="ck_video_generation_tasks_height",
        ),
        sa.CheckConstraint("seed IS NULL OR seed >= 0", name="ck_video_generation_tasks_seed"),
        sa.CheckConstraint(
            "motion_strength IS NULL OR (motion_strength >= 0 AND motion_strength <= 1)",
            name="ck_video_generation_tasks_motion_strength",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shot_id"], ["shots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["input_media_asset_id"], ["media_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["source_keyframe_output_id"],
            ["keyframe_generation_outputs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_keyframe_task_id"],
            ["keyframe_generation_tasks.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_video_generation_tasks_project_id",
        "video_generation_tasks",
        ["project_id"],
    )
    op.create_index("ix_video_generation_tasks_shot_id", "video_generation_tasks", ["shot_id"])
    op.create_index(
        "ix_video_generation_tasks_input_media_asset_id",
        "video_generation_tasks",
        ["input_media_asset_id"],
    )
    op.create_index(
        "ix_video_generation_tasks_source_keyframe_output_id",
        "video_generation_tasks",
        ["source_keyframe_output_id"],
    )
    op.create_index(
        "ix_video_generation_tasks_source_keyframe_task_id",
        "video_generation_tasks",
        ["source_keyframe_task_id"],
    )

    op.create_table(
        "video_generation_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("video_task_id", sa.String(length=36), nullable=False),
        sa.Column("run_number", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=60), nullable=False),
        sa.Column("workflow_id", sa.String(length=120), nullable=False),
        sa.Column("workflow_version", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("provider_job_id", sa.String(length=120), nullable=True),
        sa.Column("submitted_payload_snapshot", sa.Text(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message_safe", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'interrupted')",
            name="ck_video_generation_runs_status",
        ),
        sa.CheckConstraint("run_number >= 1", name="ck_video_generation_runs_run_number"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["video_task_id"],
            ["video_generation_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "video_task_id",
            "run_number",
            name="uq_video_generation_runs_task_run_number",
        ),
    )
    op.create_index("ix_video_generation_runs_project_id", "video_generation_runs", ["project_id"])
    op.create_index(
        "ix_video_generation_runs_video_task_id",
        "video_generation_runs",
        ["video_task_id"],
    )
    op.create_index("ix_video_generation_runs_status", "video_generation_runs", ["status"])
    op.create_index(
        "ix_video_generation_runs_provider_job_id",
        "video_generation_runs",
        ["provider_job_id"],
    )
    op.create_index(
        "ix_video_generation_runs_project_status_created",
        "video_generation_runs",
        ["project_id", "status", "created_at"],
    )

    op.create_table(
        "video_generation_outputs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("media_asset_id", sa.String(length=36), nullable=False),
        sa.Column("output_index", sa.Integer(), nullable=False),
        sa.Column("provider_filename", sa.String(length=255), nullable=False),
        sa.Column("provider_subfolder", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("provider_type", sa.String(length=40), nullable=False, server_default="output"),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("fps", sa.Integer(), nullable=True),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("output_index >= 1", name="ck_video_generation_outputs_index"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["video_generation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "provider_filename",
            "provider_subfolder",
            "provider_type",
            "output_index",
            name="uq_video_generation_outputs_provider_output",
        ),
    )
    op.create_index(
        "ix_video_generation_outputs_project_id",
        "video_generation_outputs",
        ["project_id"],
    )
    op.create_index("ix_video_generation_outputs_run_id", "video_generation_outputs", ["run_id"])
    op.create_index(
        "ix_video_generation_outputs_media_asset_id",
        "video_generation_outputs",
        ["media_asset_id"],
    )
    op.create_index(
        "ix_video_generation_outputs_run_selected",
        "video_generation_outputs",
        ["run_id", "is_selected"],
    )


def downgrade() -> None:
    op.drop_index("ix_video_generation_outputs_run_selected", table_name="video_generation_outputs")
    op.drop_index(
        "ix_video_generation_outputs_media_asset_id",
        table_name="video_generation_outputs",
    )
    op.drop_index("ix_video_generation_outputs_run_id", table_name="video_generation_outputs")
    op.drop_index("ix_video_generation_outputs_project_id", table_name="video_generation_outputs")
    op.drop_table("video_generation_outputs")

    op.drop_index(
        "ix_video_generation_runs_project_status_created",
        table_name="video_generation_runs",
    )
    op.drop_index("ix_video_generation_runs_provider_job_id", table_name="video_generation_runs")
    op.drop_index("ix_video_generation_runs_status", table_name="video_generation_runs")
    op.drop_index("ix_video_generation_runs_video_task_id", table_name="video_generation_runs")
    op.drop_index("ix_video_generation_runs_project_id", table_name="video_generation_runs")
    op.drop_table("video_generation_runs")

    op.drop_index(
        "ix_video_generation_tasks_source_keyframe_task_id",
        table_name="video_generation_tasks",
    )
    op.drop_index(
        "ix_video_generation_tasks_source_keyframe_output_id",
        table_name="video_generation_tasks",
    )
    op.drop_index(
        "ix_video_generation_tasks_input_media_asset_id",
        table_name="video_generation_tasks",
    )
    op.drop_index("ix_video_generation_tasks_shot_id", table_name="video_generation_tasks")
    op.drop_index("ix_video_generation_tasks_project_id", table_name="video_generation_tasks")
    op.drop_table("video_generation_tasks")

    with op.batch_alter_table("media_assets") as batch_op:
        batch_op.alter_column(
            "thumbnail_relative_path",
            existing_type=sa.String(length=800),
            nullable=False,
        )
