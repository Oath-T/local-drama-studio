"""create keyframe generation runs

Revision ID: 20260629_0300
Revises: 20260629_0200
Create Date: 2026-06-29 03:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260629_0300"
down_revision: str | None = "20260629_0200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "keyframe_generation_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("keyframe_task_id", sa.String(length=36), nullable=False),
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
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled', 'interrupted')",
            name="ck_keyframe_generation_runs_status",
        ),
        sa.CheckConstraint("run_number >= 1", name="ck_keyframe_generation_runs_run_number"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["keyframe_task_id"],
            ["keyframe_generation_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "keyframe_task_id",
            "run_number",
            name="uq_keyframe_generation_runs_task_run_number",
        ),
    )
    op.create_index(
        "ix_keyframe_generation_runs_project_id",
        "keyframe_generation_runs",
        ["project_id"],
    )
    op.create_index(
        "ix_keyframe_generation_runs_task_id",
        "keyframe_generation_runs",
        ["keyframe_task_id"],
    )
    op.create_index(
        "ix_keyframe_generation_runs_status",
        "keyframe_generation_runs",
        ["status"],
    )
    op.create_index(
        "ix_keyframe_generation_runs_provider_job_id",
        "keyframe_generation_runs",
        ["provider_job_id"],
    )
    op.create_index(
        "ix_keyframe_generation_runs_created_at",
        "keyframe_generation_runs",
        ["created_at"],
    )
    op.create_index(
        "ix_keyframe_generation_runs_project_status_created",
        "keyframe_generation_runs",
        ["project_id", "status", "created_at"],
    )

    op.create_table(
        "keyframe_generation_outputs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("media_asset_id", sa.String(length=36), nullable=False),
        sa.Column("output_index", sa.Integer(), nullable=False),
        sa.Column("provider_filename", sa.String(length=255), nullable=False),
        sa.Column("provider_subfolder", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("output_index >= 1", name="ck_keyframe_generation_outputs_index"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["keyframe_generation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "provider_filename",
            "provider_subfolder",
            "output_index",
            name="uq_keyframe_generation_outputs_provider_output",
        ),
    )
    op.create_index(
        "ix_keyframe_generation_outputs_project_id",
        "keyframe_generation_outputs",
        ["project_id"],
    )
    op.create_index(
        "ix_keyframe_generation_outputs_run_id",
        "keyframe_generation_outputs",
        ["run_id"],
    )
    op.create_index(
        "ix_keyframe_generation_outputs_media_asset_id",
        "keyframe_generation_outputs",
        ["media_asset_id"],
    )
    op.create_index(
        "ix_keyframe_generation_outputs_run_selected",
        "keyframe_generation_outputs",
        ["run_id", "is_selected"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_keyframe_generation_outputs_run_selected",
        table_name="keyframe_generation_outputs",
    )
    op.drop_index(
        "ix_keyframe_generation_outputs_media_asset_id",
        table_name="keyframe_generation_outputs",
    )
    op.drop_index(
        "ix_keyframe_generation_outputs_run_id",
        table_name="keyframe_generation_outputs",
    )
    op.drop_index(
        "ix_keyframe_generation_outputs_project_id",
        table_name="keyframe_generation_outputs",
    )
    op.drop_table("keyframe_generation_outputs")

    op.drop_index(
        "ix_keyframe_generation_runs_project_status_created",
        table_name="keyframe_generation_runs",
    )
    op.drop_index(
        "ix_keyframe_generation_runs_created_at",
        table_name="keyframe_generation_runs",
    )
    op.drop_index(
        "ix_keyframe_generation_runs_provider_job_id",
        table_name="keyframe_generation_runs",
    )
    op.drop_index(
        "ix_keyframe_generation_runs_status",
        table_name="keyframe_generation_runs",
    )
    op.drop_index(
        "ix_keyframe_generation_runs_task_id",
        table_name="keyframe_generation_runs",
    )
    op.drop_index(
        "ix_keyframe_generation_runs_project_id",
        table_name="keyframe_generation_runs",
    )
    op.drop_table("keyframe_generation_runs")
