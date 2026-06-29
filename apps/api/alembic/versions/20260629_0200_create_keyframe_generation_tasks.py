"""create keyframe generation tasks

Revision ID: 20260629_0200
Revises: 20260629_0100
Create Date: 2026-06-29 02:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260629_0200"
down_revision: str | None = "20260629_0100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "keyframe_generation_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("shot_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("shot_snapshot", sa.Text(), nullable=False),
        sa.Column("source_shot_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prompt_zh", sa.Text(), nullable=True),
        sa.Column("prompt_en", sa.Text(), nullable=True),
        sa.Column("negative_prompt", sa.Text(), nullable=True),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("steps", sa.Integer(), nullable=False),
        sa.Column("guidance_scale", sa.Float(), nullable=False),
        sa.Column("sampler_name", sa.String(length=120), nullable=True),
        sa.Column("scheduler_name", sa.String(length=120), nullable=True),
        sa.Column("model_provider", sa.String(length=120), nullable=True),
        sa.Column("model_name", sa.String(length=200), nullable=True),
        sa.Column("model_version", sa.String(length=120), nullable=True),
        sa.Column("output_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'ready')",
            name="ck_keyframe_generation_tasks_status",
        ),
        sa.CheckConstraint(
            "aspect_ratio IN ('16:9', '9:16', '1:1', '4:3', '3:4', 'custom')",
            name="ck_keyframe_generation_tasks_aspect_ratio",
        ),
        sa.CheckConstraint(
            "width BETWEEN 256 AND 4096 AND width % 8 = 0",
            name="ck_keyframe_generation_tasks_width",
        ),
        sa.CheckConstraint(
            "height BETWEEN 256 AND 4096 AND height % 8 = 0",
            name="ck_keyframe_generation_tasks_height",
        ),
        sa.CheckConstraint(
            "seed IS NULL OR seed >= 0",
            name="ck_keyframe_generation_tasks_seed",
        ),
        sa.CheckConstraint(
            "steps BETWEEN 1 AND 150",
            name="ck_keyframe_generation_tasks_steps",
        ),
        sa.CheckConstraint(
            "guidance_scale BETWEEN 0 AND 30",
            name="ck_keyframe_generation_tasks_guidance",
        ),
        sa.CheckConstraint(
            "output_count BETWEEN 1 AND 8",
            name="ck_keyframe_generation_tasks_output_count",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shot_id"], ["shots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_keyframe_generation_tasks_project_id",
        "keyframe_generation_tasks",
        ["project_id"],
    )
    op.create_index(
        "ix_keyframe_generation_tasks_shot_id",
        "keyframe_generation_tasks",
        ["shot_id"],
    )
    op.create_index(
        "ix_keyframe_generation_tasks_status",
        "keyframe_generation_tasks",
        ["status"],
    )
    op.create_index(
        "ix_keyframe_generation_tasks_shot_created",
        "keyframe_generation_tasks",
        ["shot_id", "created_at", "id"],
    )

    op.create_table(
        "keyframe_generation_task_references",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("reference_type", sa.String(length=24), nullable=False),
        sa.Column("shot_reference_id", sa.String(length=36), nullable=True),
        sa.Column("character_reference_id", sa.String(length=36), nullable=True),
        sa.Column("scene_reference_id", sa.String(length=36), nullable=True),
        sa.Column("media_asset_id", sa.String(length=36), nullable=False),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("source_shot_character_id", sa.String(length=36), nullable=True),
        sa.Column("source_character_id", sa.String(length=36), nullable=True),
        sa.Column("source_look_id", sa.String(length=36), nullable=True),
        sa.Column("source_scene_id", sa.String(length=36), nullable=True),
        sa.Column("source_scene_state_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "reference_type IN ('character', 'scene')",
            name="ck_keyframe_generation_task_references_type",
        ),
        sa.CheckConstraint(
            "("
            "reference_type = 'character' "
            "AND scene_reference_id IS NULL "
            "AND source_scene_id IS NULL "
            "AND source_scene_state_id IS NULL"
            ") OR ("
            "reference_type = 'scene' "
            "AND character_reference_id IS NULL "
            "AND source_shot_character_id IS NULL "
            "AND source_character_id IS NULL "
            "AND source_look_id IS NULL"
            ")",
            name="ck_keyframe_generation_task_references_type_target",
        ),
        sa.CheckConstraint(
            "order_index >= 0",
            name="ck_keyframe_generation_task_references_order",
        ),
        sa.ForeignKeyConstraint(
            ["character_reference_id"],
            ["character_references.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["media_asset_id"],
            ["media_assets.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["scene_reference_id"],
            ["scene_references.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["shot_reference_id"],
            ["shot_references.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["keyframe_generation_tasks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "order_index", name="uq_keyframe_task_refs_order"),
    )
    op.create_index(
        "ix_keyframe_task_refs_task_id",
        "keyframe_generation_task_references",
        ["task_id"],
    )
    op.create_index(
        "ix_keyframe_task_refs_shot_reference_id",
        "keyframe_generation_task_references",
        ["shot_reference_id"],
    )
    op.create_index(
        "ix_keyframe_task_refs_character_reference_id",
        "keyframe_generation_task_references",
        ["character_reference_id"],
    )
    op.create_index(
        "ix_keyframe_task_refs_scene_reference_id",
        "keyframe_generation_task_references",
        ["scene_reference_id"],
    )
    op.create_index(
        "ix_keyframe_task_refs_media_asset_id",
        "keyframe_generation_task_references",
        ["media_asset_id"],
    )
    op.create_index(
        "ix_keyframe_task_refs_lookup",
        "keyframe_generation_task_references",
        [
            "task_id",
            "reference_type",
            "character_reference_id",
            "scene_reference_id",
            "purpose",
            "source_shot_character_id",
        ],
    )
    op.create_index(
        "ix_keyframe_task_refs_task_order",
        "keyframe_generation_task_references",
        ["task_id", "order_index", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_keyframe_task_refs_task_order",
        table_name="keyframe_generation_task_references",
    )
    op.drop_index(
        "ix_keyframe_task_refs_lookup",
        table_name="keyframe_generation_task_references",
    )
    op.drop_index(
        "ix_keyframe_task_refs_media_asset_id",
        table_name="keyframe_generation_task_references",
    )
    op.drop_index(
        "ix_keyframe_task_refs_scene_reference_id",
        table_name="keyframe_generation_task_references",
    )
    op.drop_index(
        "ix_keyframe_task_refs_character_reference_id",
        table_name="keyframe_generation_task_references",
    )
    op.drop_index(
        "ix_keyframe_task_refs_shot_reference_id",
        table_name="keyframe_generation_task_references",
    )
    op.drop_index("ix_keyframe_task_refs_task_id", table_name="keyframe_generation_task_references")
    op.drop_table("keyframe_generation_task_references")

    op.drop_index(
        "ix_keyframe_generation_tasks_shot_created",
        table_name="keyframe_generation_tasks",
    )
    op.drop_index("ix_keyframe_generation_tasks_status", table_name="keyframe_generation_tasks")
    op.drop_index("ix_keyframe_generation_tasks_shot_id", table_name="keyframe_generation_tasks")
    op.drop_index("ix_keyframe_generation_tasks_project_id", table_name="keyframe_generation_tasks")
    op.drop_table("keyframe_generation_tasks")
