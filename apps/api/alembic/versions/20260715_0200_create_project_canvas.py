"""create project canvas

Revision ID: 20260715_0200
Revises: 20260715_0100
Create Date: 2026-07-15 02:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260715_0200"
down_revision: str | None = "20260715_0100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_canvases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("view_mode", sa.String(length=24), nullable=False),
        sa.Column("viewport_json", sa.Text(), nullable=False),
        sa.Column("layout_version", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "view_mode IN ('workflow', 'storyboard')",
            name="ck_project_canvases_view_mode",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_project_canvases_revision"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="uq_project_canvases_project_id"),
    )
    op.create_index("ix_project_canvases_project_id", "project_canvases", ["project_id"])

    op.create_table(
        "project_canvas_nodes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("canvas_id", sa.String(length=36), nullable=False),
        sa.Column("node_type", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("position_x", sa.Float(), nullable=False),
        sa.Column("position_y", sa.Float(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("z_index", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=True),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("data_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "node_type IN ('text', 'character', 'scene', 'shot', 'image', 'video', 'export')",
            name="ck_project_canvas_nodes_type",
        ),
        sa.ForeignKeyConstraint(["canvas_id"], ["project_canvases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_canvas_nodes_canvas_id", "project_canvas_nodes", ["canvas_id"])
    op.create_index("ix_project_canvas_nodes_node_type", "project_canvas_nodes", ["node_type"])
    op.create_index("ix_project_canvas_nodes_entity_type", "project_canvas_nodes", ["entity_type"])
    op.create_index("ix_project_canvas_nodes_entity_id", "project_canvas_nodes", ["entity_id"])

    op.create_table(
        "project_canvas_edges",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("canvas_id", sa.String(length=36), nullable=False),
        sa.Column("source_node_id", sa.String(length=36), nullable=False),
        sa.Column("target_node_id", sa.String(length=36), nullable=False),
        sa.Column("source_handle", sa.String(length=80), nullable=True),
        sa.Column("target_handle", sa.String(length=80), nullable=True),
        sa.Column("semantic_type", sa.String(length=40), nullable=False),
        sa.Column("data_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "semantic_type IN ('uses_character', 'uses_scene', 'identity_reference', "
            "'look_reference', 'scene_reference', 'pose_reference', 'start_frame', "
            "'end_frame', 'continuity_from', 'generated_from', 'included_in_export')",
            name="ck_project_canvas_edges_semantic_type",
        ),
        sa.ForeignKeyConstraint(["canvas_id"], ["project_canvases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_node_id"], ["project_canvas_nodes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_node_id"], ["project_canvas_nodes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_canvas_edges_canvas_id", "project_canvas_edges", ["canvas_id"])
    op.create_index(
        "ix_project_canvas_edges_source_node_id",
        "project_canvas_edges",
        ["source_node_id"],
    )
    op.create_index(
        "ix_project_canvas_edges_target_node_id",
        "project_canvas_edges",
        ["target_node_id"],
    )
    op.create_index(
        "ix_project_canvas_edges_semantic_type",
        "project_canvas_edges",
        ["semantic_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_canvas_edges_semantic_type", table_name="project_canvas_edges")
    op.drop_index("ix_project_canvas_edges_target_node_id", table_name="project_canvas_edges")
    op.drop_index("ix_project_canvas_edges_source_node_id", table_name="project_canvas_edges")
    op.drop_index("ix_project_canvas_edges_canvas_id", table_name="project_canvas_edges")
    op.drop_table("project_canvas_edges")

    op.drop_index("ix_project_canvas_nodes_entity_id", table_name="project_canvas_nodes")
    op.drop_index("ix_project_canvas_nodes_entity_type", table_name="project_canvas_nodes")
    op.drop_index("ix_project_canvas_nodes_node_type", table_name="project_canvas_nodes")
    op.drop_index("ix_project_canvas_nodes_canvas_id", table_name="project_canvas_nodes")
    op.drop_table("project_canvas_nodes")

    op.drop_index("ix_project_canvases_project_id", table_name="project_canvases")
    op.drop_table("project_canvases")
