"""create vision analysis tasks

Revision ID: 20260629_0100
Revises: 20260628_0310
Create Date: 2026-06-29 01:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260629_0100"
down_revision: str | None = "20260628_0310"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vision_analysis_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=False),
        sa.Column("character_reference_id", sa.String(length=36), nullable=True),
        sa.Column("scene_reference_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message_safe", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            """
            (
                target_type = 'character_reference'
                AND character_reference_id IS NOT NULL
                AND scene_reference_id IS NULL
            )
            OR
            (
                target_type = 'scene_reference'
                AND scene_reference_id IS NOT NULL
                AND character_reference_id IS NULL
            )
            """,
            name="ck_vision_analysis_task_target",
        ),
        sa.ForeignKeyConstraint(
            ["character_reference_id"],
            ["character_references.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["scene_reference_id"],
            ["scene_references.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_vision_analysis_tasks_project_id",
        "vision_analysis_tasks",
        ["project_id"],
    )
    op.create_index(
        "ix_vision_analysis_tasks_character_active_lookup",
        "vision_analysis_tasks",
        ["project_id", "target_type", "character_reference_id", "status"],
    )
    op.create_index(
        "ix_vision_analysis_tasks_scene_active_lookup",
        "vision_analysis_tasks",
        ["project_id", "target_type", "scene_reference_id", "status"],
    )
    op.create_index(
        "ix_vision_analysis_tasks_latest_character",
        "vision_analysis_tasks",
        ["character_reference_id", "created_at", "id"],
    )
    op.create_index(
        "ix_vision_analysis_tasks_latest_scene",
        "vision_analysis_tasks",
        ["scene_reference_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_vision_analysis_tasks_latest_scene", table_name="vision_analysis_tasks")
    op.drop_index("ix_vision_analysis_tasks_latest_character", table_name="vision_analysis_tasks")
    op.drop_index(
        "ix_vision_analysis_tasks_scene_active_lookup",
        table_name="vision_analysis_tasks",
    )
    op.drop_index(
        "ix_vision_analysis_tasks_character_active_lookup",
        table_name="vision_analysis_tasks",
    )
    op.drop_index("ix_vision_analysis_tasks_project_id", table_name="vision_analysis_tasks")
    op.drop_table("vision_analysis_tasks")
