"""create shot workbench tables

Revision ID: 20260628_0300
Revises: 20260628_0200
Create Date: 2026-06-28 03:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260628_0300"
down_revision: str | None = "20260628_0200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("story_description", sa.Text(), nullable=True),
        sa.Column("visual_description", sa.Text(), nullable=True),
        sa.Column("dialogue", sa.Text(), nullable=True),
        sa.Column("action_summary", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("shot_scale", sa.String(length=40), nullable=False),
        sa.Column("camera_height", sa.String(length=40), nullable=False),
        sa.Column("custom_camera_height", sa.String(length=120), nullable=True),
        sa.Column("camera_angle", sa.String(length=40), nullable=False),
        sa.Column("custom_camera_angle", sa.String(length=120), nullable=True),
        sa.Column("composition_type", sa.String(length=40), nullable=False),
        sa.Column("custom_composition", sa.String(length=120), nullable=True),
        sa.Column("camera_movement", sa.String(length=40), nullable=False),
        sa.Column("custom_camera_movement", sa.String(length=120), nullable=True),
        sa.Column("focal_subject", sa.String(length=200), nullable=True),
        sa.Column("mood_description", sa.Text(), nullable=True),
        sa.Column("scene_id", sa.String(length=36), nullable=True),
        sa.Column("scene_state_id", sa.String(length=36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["scene_state_id"], ["scene_states.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "order_index", name="uq_shots_project_order"),
    )
    op.create_index("ix_shots_project_id", "shots", ["project_id"])
    op.create_index("ix_shots_scene_id", "shots", ["scene_id"])
    op.create_index("ix_shots_scene_state_id", "shots", ["scene_state_id"])
    op.create_index("ix_shots_project_order", "shots", ["project_id", "order_index", "id"])

    op.create_table(
        "shot_characters",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("shot_id", sa.String(length=36), nullable=False),
        sa.Column("character_id", sa.String(length=36), nullable=False),
        sa.Column("look_id", sa.String(length=36), nullable=True),
        sa.Column("action_description", sa.Text(), nullable=True),
        sa.Column("expression_description", sa.Text(), nullable=True),
        sa.Column("position_description", sa.Text(), nullable=True),
        sa.Column("is_primary_subject", sa.Boolean(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["look_id"], ["character_looks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shot_id"], ["shots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shot_id", "character_id", name="uq_shot_characters_shot_character"),
        sa.UniqueConstraint("shot_id", "order_index", name="uq_shot_characters_shot_order"),
    )
    op.create_index("ix_shot_characters_shot_id", "shot_characters", ["shot_id"])
    op.create_index("ix_shot_characters_character_id", "shot_characters", ["character_id"])
    op.create_index("ix_shot_characters_look_id", "shot_characters", ["look_id"])
    op.create_index(
        "ix_shot_characters_shot_order",
        "shot_characters",
        ["shot_id", "order_index", "id"],
    )

    op.create_table(
        "shot_references",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("shot_id", sa.String(length=36), nullable=False),
        sa.Column("reference_type", sa.String(length=24), nullable=False),
        sa.Column("character_reference_id", sa.String(length=36), nullable=True),
        sa.Column("scene_reference_id", sa.String(length=36), nullable=True),
        sa.Column("shot_character_id", sa.String(length=36), nullable=True),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "("
            "reference_type = 'character' "
            "AND character_reference_id IS NOT NULL "
            "AND scene_reference_id IS NULL"
            ") OR ("
            "reference_type = 'scene' "
            "AND scene_reference_id IS NOT NULL "
            "AND character_reference_id IS NULL "
            "AND shot_character_id IS NULL"
            ")",
            name="ck_shot_references_type_target",
        ),
        sa.ForeignKeyConstraint(
            ["character_reference_id"], ["character_references.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["scene_reference_id"], ["scene_references.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shot_character_id"], ["shot_characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shot_id"], ["shots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shot_id", "order_index", name="uq_shot_references_shot_order"),
    )
    op.create_index("ix_shot_references_shot_id", "shot_references", ["shot_id"])
    op.create_index(
        "ix_shot_references_character_reference_id",
        "shot_references",
        ["character_reference_id"],
    )
    op.create_index(
        "ix_shot_references_scene_reference_id",
        "shot_references",
        ["scene_reference_id"],
    )
    op.create_index(
        "ix_shot_references_shot_character_id",
        "shot_references",
        ["shot_character_id"],
    )
    op.create_index(
        "ix_shot_references_lookup",
        "shot_references",
        [
            "shot_id",
            "reference_type",
            "character_reference_id",
            "scene_reference_id",
            "purpose",
            "shot_character_id",
        ],
    )
    op.create_index(
        "ix_shot_references_shot_order",
        "shot_references",
        ["shot_id", "order_index", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_shot_references_shot_order", table_name="shot_references")
    op.drop_index("ix_shot_references_lookup", table_name="shot_references")
    op.drop_index("ix_shot_references_shot_character_id", table_name="shot_references")
    op.drop_index("ix_shot_references_scene_reference_id", table_name="shot_references")
    op.drop_index("ix_shot_references_character_reference_id", table_name="shot_references")
    op.drop_index("ix_shot_references_shot_id", table_name="shot_references")
    op.drop_table("shot_references")

    op.drop_index("ix_shot_characters_shot_order", table_name="shot_characters")
    op.drop_index("ix_shot_characters_look_id", table_name="shot_characters")
    op.drop_index("ix_shot_characters_character_id", table_name="shot_characters")
    op.drop_index("ix_shot_characters_shot_id", table_name="shot_characters")
    op.drop_table("shot_characters")

    op.drop_index("ix_shots_project_order", table_name="shots")
    op.drop_index("ix_shots_scene_state_id", table_name="shots")
    op.drop_index("ix_shots_scene_id", table_name="shots")
    op.drop_index("ix_shots_project_id", table_name="shots")
    op.drop_table("shots")
