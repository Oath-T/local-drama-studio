"""create character asset tables

Revision ID: 20260628_0100
Revises: 20260627_2301
Create Date: 2026-06-28 01:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260628_0100"
down_revision: str | None = "20260627_2301"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "characters",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("aliases", sa.String(length=200), nullable=True),
        sa.Column("role_type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("appearance_description", sa.Text(), nullable=True),
        sa.Column("personality_description", sa.Text(), nullable=True),
        sa.Column("prompt_identity", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_characters_project_id", "characters", ["project_id"])
    op.create_index(
        "ix_characters_project_updated",
        "characters",
        ["project_id", "updated_at", "created_at", "id"],
    )

    op.create_table(
        "media_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("media_type", sa.String(length=24), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("relative_path", sa.String(length=800), nullable=False),
        sa.Column("thumbnail_relative_path", sa.String(length=800), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("extension", sa.String(length=16), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_assets_project_id", "media_assets", ["project_id"])
    op.create_index("ix_media_assets_sha256", "media_assets", ["sha256"])

    op.create_table(
        "character_looks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("character_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("costume_description", sa.Text(), nullable=True),
        sa.Column("hair_description", sa.Text(), nullable=True),
        sa.Column("makeup_description", sa.Text(), nullable=True),
        sa.Column("condition_description", sa.Text(), nullable=True),
        sa.Column("prompt_appearance", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_character_looks_character_id", "character_looks", ["character_id"])
    op.create_index(
        "ix_character_looks_character_default",
        "character_looks",
        ["character_id", "is_default"],
    )

    op.create_table(
        "character_references",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("look_id", sa.String(length=36), nullable=False),
        sa.Column("media_asset_id", sa.String(length=36), nullable=False),
        sa.Column("shot_type", sa.String(length=40), nullable=False),
        sa.Column("view_angle", sa.String(length=40), nullable=False),
        sa.Column("expression", sa.String(length=40), nullable=False),
        sa.Column("pose_type", sa.String(length=40), nullable=False),
        sa.Column("custom_expression", sa.String(length=100), nullable=True),
        sa.Column("custom_pose", sa.String(length=100), nullable=True),
        sa.Column("tags", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("is_identity_anchor", sa.Boolean(), nullable=False),
        sa.Column("analysis_status", sa.String(length=32), nullable=False),
        sa.Column("suggestion_review_status", sa.String(length=32), nullable=False),
        sa.Column("analysis_suggestions", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["look_id"], ["character_looks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_character_references_look_id", "character_references", ["look_id"])
    op.create_index(
        "ix_character_references_look_primary",
        "character_references",
        ["look_id", "is_primary"],
    )
    op.create_index(
        "ix_character_references_media_asset_id",
        "character_references",
        ["media_asset_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_character_references_media_asset_id", table_name="character_references")
    op.drop_index("ix_character_references_look_primary", table_name="character_references")
    op.drop_index("ix_character_references_look_id", table_name="character_references")
    op.drop_table("character_references")

    op.drop_index("ix_character_looks_character_default", table_name="character_looks")
    op.drop_index("ix_character_looks_character_id", table_name="character_looks")
    op.drop_table("character_looks")

    op.drop_index("ix_media_assets_sha256", table_name="media_assets")
    op.drop_index("ix_media_assets_project_id", table_name="media_assets")
    op.drop_table("media_assets")

    op.drop_index("ix_characters_project_updated", table_name="characters")
    op.drop_index("ix_characters_project_id", table_name="characters")
    op.drop_table("characters")
