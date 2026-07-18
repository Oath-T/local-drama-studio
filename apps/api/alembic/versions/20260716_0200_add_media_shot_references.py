"""add media shot references

Revision ID: 20260716_0200
Revises: 20260716_0100
Create Date: 2026-07-16 02:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260716_0200"
down_revision: str | None = "20260716_0100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SHOT_REFERENCE_TARGET_CHECK = (
    "("
    "reference_type = 'character' "
    "AND character_reference_id IS NOT NULL "
    "AND scene_reference_id IS NULL "
    "AND media_asset_id IS NULL"
    ") OR ("
    "reference_type = 'scene' "
    "AND scene_reference_id IS NOT NULL "
    "AND character_reference_id IS NULL "
    "AND media_asset_id IS NULL "
    "AND shot_character_id IS NULL"
    ") OR ("
    "reference_type = 'media' "
    "AND media_asset_id IS NOT NULL "
    "AND character_reference_id IS NULL "
    "AND scene_reference_id IS NULL "
    "AND shot_character_id IS NULL"
    ")"
)

KEYFRAME_REFERENCE_TYPE_CHECK = "reference_type IN ('character', 'scene', 'media')"

KEYFRAME_REFERENCE_TARGET_CHECK = (
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
    ") OR ("
    "reference_type = 'media' "
    "AND character_reference_id IS NULL "
    "AND scene_reference_id IS NULL "
    "AND source_shot_character_id IS NULL "
    "AND source_character_id IS NULL "
    "AND source_look_id IS NULL "
    "AND source_scene_id IS NULL "
    "AND source_scene_state_id IS NULL"
    ")"
)

CANVAS_EDGE_TYPE_CHECK = (
    "semantic_type IN ('uses_character', 'uses_scene', 'shot_reference', "
    "'identity_reference', 'look_reference', 'scene_reference', 'pose_reference', "
    "'start_frame', 'end_frame', 'continuity_from', 'generated_from', "
    "'included_in_export')"
)


def upgrade() -> None:
    with op.batch_alter_table("shot_references", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("media_asset_id", sa.String(length=36), nullable=True))
        batch_op.drop_constraint("ck_shot_references_type_target", type_="check")
        batch_op.create_check_constraint(
            "ck_shot_references_type_target",
            SHOT_REFERENCE_TARGET_CHECK,
        )
        batch_op.create_foreign_key(
            "fk_shot_references_media_asset_id_media_assets",
            "media_assets",
            ["media_asset_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index("ix_shot_references_media_asset_id", ["media_asset_id"])

    op.drop_index("ix_shot_references_lookup", table_name="shot_references")
    op.create_index(
        "ix_shot_references_lookup",
        "shot_references",
        [
            "shot_id",
            "reference_type",
            "character_reference_id",
            "scene_reference_id",
            "media_asset_id",
            "purpose",
            "shot_character_id",
        ],
    )

    with op.batch_alter_table("keyframe_generation_task_references", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_keyframe_generation_task_references_type", type_="check")
        batch_op.drop_constraint(
            "ck_keyframe_generation_task_references_type_target",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_keyframe_generation_task_references_type",
            KEYFRAME_REFERENCE_TYPE_CHECK,
        )
        batch_op.create_check_constraint(
            "ck_keyframe_generation_task_references_type_target",
            KEYFRAME_REFERENCE_TARGET_CHECK,
        )

    with op.batch_alter_table("project_canvas_edges", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_project_canvas_edges_semantic_type", type_="check")
        batch_op.create_check_constraint(
            "ck_project_canvas_edges_semantic_type",
            CANVAS_EDGE_TYPE_CHECK,
        )


def downgrade() -> None:
    with op.batch_alter_table("project_canvas_edges", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_project_canvas_edges_semantic_type", type_="check")
        batch_op.create_check_constraint(
            "ck_project_canvas_edges_semantic_type",
            "semantic_type IN ('uses_character', 'uses_scene', 'identity_reference', "
            "'look_reference', 'scene_reference', 'pose_reference', 'start_frame', "
            "'end_frame', 'continuity_from', 'generated_from', 'included_in_export')",
        )

    with op.batch_alter_table("keyframe_generation_task_references", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_keyframe_generation_task_references_type", type_="check")
        batch_op.drop_constraint(
            "ck_keyframe_generation_task_references_type_target",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_keyframe_generation_task_references_type",
            "reference_type IN ('character', 'scene')",
        )
        batch_op.create_check_constraint(
            "ck_keyframe_generation_task_references_type_target",
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
        )

    op.drop_index("ix_shot_references_lookup", table_name="shot_references")
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

    with op.batch_alter_table("shot_references", recreate="always") as batch_op:
        batch_op.drop_index("ix_shot_references_media_asset_id")
        batch_op.drop_constraint(
            "fk_shot_references_media_asset_id_media_assets",
            type_="foreignkey",
        )
        batch_op.drop_constraint("ck_shot_references_type_target", type_="check")
        batch_op.create_check_constraint(
            "ck_shot_references_type_target",
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
        )
        batch_op.drop_column("media_asset_id")
