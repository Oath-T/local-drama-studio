"""create scene asset tables

Revision ID: 20260628_0200
Revises: 20260628_0100
Create Date: 2026-06-28 02:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260628_0200"
down_revision: str | None = "20260628_0100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scenes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("scene_type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("fixed_environment_description", sa.Text(), nullable=True),
        sa.Column("spatial_layout_description", sa.Text(), nullable=True),
        sa.Column("visual_style_description", sa.Text(), nullable=True),
        sa.Column("prompt_environment", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scenes_project_id", "scenes", ["project_id"])
    op.create_index(
        "ix_scenes_project_updated",
        "scenes",
        ["project_id", "updated_at", "created_at", "id"],
    )

    op.create_table(
        "scene_states",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("scene_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("time_of_day", sa.String(length=32), nullable=False),
        sa.Column("weather", sa.String(length=32), nullable=False),
        sa.Column("custom_weather", sa.String(length=120), nullable=True),
        sa.Column("lighting", sa.String(length=32), nullable=False),
        sa.Column("custom_lighting", sa.String(length=120), nullable=True),
        sa.Column("season", sa.String(length=32), nullable=False),
        sa.Column("environment_condition", sa.Text(), nullable=True),
        sa.Column("crowd_level", sa.String(length=32), nullable=False),
        sa.Column("prompt_state", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scene_states_scene_id", "scene_states", ["scene_id"])
    op.create_index(
        "ix_scene_states_scene_default",
        "scene_states",
        ["scene_id", "is_default"],
    )
    op.create_index(
        "ix_scene_states_scene_created",
        "scene_states",
        ["scene_id", "created_at", "id"],
    )

    op.create_table(
        "scene_references",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("state_id", sa.String(length=36), nullable=False),
        sa.Column("media_asset_id", sa.String(length=36), nullable=False),
        sa.Column("shot_scale", sa.String(length=40), nullable=False),
        sa.Column("camera_position", sa.String(length=40), nullable=False),
        sa.Column("custom_camera_position", sa.String(length=120), nullable=True),
        sa.Column("view_direction", sa.String(length=40), nullable=False),
        sa.Column("custom_view_direction", sa.String(length=120), nullable=True),
        sa.Column("composition_type", sa.String(length=40), nullable=False),
        sa.Column("custom_composition", sa.String(length=120), nullable=True),
        sa.Column("is_empty_plate", sa.Boolean(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("is_spatial_anchor", sa.Boolean(), nullable=False),
        sa.Column("tags", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("analysis_status", sa.String(length=32), nullable=False),
        sa.Column("suggestion_review_status", sa.String(length=32), nullable=False),
        sa.Column("analysis_suggestions", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["state_id"], ["scene_states.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("media_asset_id", name="uq_scene_references_media_asset_id"),
    )
    op.create_index("ix_scene_references_state_id", "scene_references", ["state_id"])
    op.create_index(
        "ix_scene_references_state_primary",
        "scene_references",
        ["state_id", "is_primary"],
    )
    op.create_index(
        "ix_scene_references_state_created",
        "scene_references",
        ["state_id", "created_at", "id"],
    )
    op.create_index(
        "ix_scene_references_media_asset_id",
        "scene_references",
        ["media_asset_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_scene_references_media_asset_id", table_name="scene_references")
    op.drop_index("ix_scene_references_state_created", table_name="scene_references")
    op.drop_index("ix_scene_references_state_primary", table_name="scene_references")
    op.drop_index("ix_scene_references_state_id", table_name="scene_references")
    op.drop_table("scene_references")

    op.drop_index("ix_scene_states_scene_created", table_name="scene_states")
    op.drop_index("ix_scene_states_scene_default", table_name="scene_states")
    op.drop_index("ix_scene_states_scene_id", table_name="scene_states")
    op.drop_table("scene_states")

    op.drop_index("ix_scenes_project_updated", table_name="scenes")
    op.drop_index("ix_scenes_project_id", table_name="scenes")
    op.drop_table("scenes")
