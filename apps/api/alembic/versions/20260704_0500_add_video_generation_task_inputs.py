"""add video generation task inputs

Revision ID: 20260704_0500
Revises: 20260704_0400
Create Date: 2026-07-04 05:00:00
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "20260704_0500"
down_revision: str | None = "20260704_0400"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "video_generation_task_inputs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("media_asset_id", sa.String(length=36), nullable=True),
        sa.Column("source_keyframe_output_id", sa.String(length=36), nullable=True),
        sa.Column("source_keyframe_task_id", sa.String(length=36), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('start_frame', 'end_frame')",
            name="ck_video_generation_task_inputs_role",
        ),
        sa.CheckConstraint(
            "sort_order >= 1",
            name="ck_video_generation_task_inputs_sort_order",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["video_generation_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="SET NULL"),
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
        sa.UniqueConstraint(
            "task_id",
            "role",
            name="uq_video_generation_task_inputs_task_role",
        ),
    )
    op.create_index(
        "ix_video_generation_task_inputs_project_id",
        "video_generation_task_inputs",
        ["project_id"],
    )
    op.create_index(
        "ix_video_generation_task_inputs_task_id",
        "video_generation_task_inputs",
        ["task_id"],
    )
    op.create_index(
        "ix_video_generation_task_inputs_role",
        "video_generation_task_inputs",
        ["role"],
    )
    op.create_index(
        "ix_video_generation_task_inputs_media_asset_id",
        "video_generation_task_inputs",
        ["media_asset_id"],
    )
    op.create_index(
        "ix_video_generation_task_inputs_source_keyframe_output_id",
        "video_generation_task_inputs",
        ["source_keyframe_output_id"],
    )
    op.create_index(
        "ix_video_generation_task_inputs_source_keyframe_task_id",
        "video_generation_task_inputs",
        ["source_keyframe_task_id"],
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, project_id, input_media_asset_id, source_keyframe_output_id,
                   source_keyframe_task_id, created_at, updated_at
            FROM video_generation_tasks
            WHERE input_media_asset_id IS NOT NULL
            """
        )
    ).mappings()
    for row in rows:
        bind.execute(
            sa.text(
                """
                INSERT INTO video_generation_task_inputs (
                    id, project_id, task_id, role, media_asset_id,
                    source_keyframe_output_id, source_keyframe_task_id,
                    sort_order, created_at, updated_at
                )
                VALUES (
                    :id, :project_id, :task_id, 'start_frame', :media_asset_id,
                    :source_keyframe_output_id, :source_keyframe_task_id,
                    1, :created_at, :updated_at
                )
                """
            ),
            {
                "id": str(uuid4()),
                "project_id": row["project_id"],
                "task_id": row["id"],
                "media_asset_id": row["input_media_asset_id"],
                "source_keyframe_output_id": row["source_keyframe_output_id"],
                "source_keyframe_task_id": row["source_keyframe_task_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            },
        )


def downgrade() -> None:
    op.drop_index(
        "ix_video_generation_task_inputs_source_keyframe_task_id",
        table_name="video_generation_task_inputs",
    )
    op.drop_index(
        "ix_video_generation_task_inputs_source_keyframe_output_id",
        table_name="video_generation_task_inputs",
    )
    op.drop_index(
        "ix_video_generation_task_inputs_media_asset_id",
        table_name="video_generation_task_inputs",
    )
    op.drop_index("ix_video_generation_task_inputs_role", table_name="video_generation_task_inputs")
    op.drop_index(
        "ix_video_generation_task_inputs_task_id",
        table_name="video_generation_task_inputs",
    )
    op.drop_index(
        "ix_video_generation_task_inputs_project_id",
        table_name="video_generation_task_inputs",
    )
    op.drop_table("video_generation_task_inputs")
