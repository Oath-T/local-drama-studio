"""create projects table

Revision ID: 20260627_2301
Revises:
Create Date: 2026-06-27 23:01:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260627_2301"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("aspect_ratio", sa.String(length=8), nullable=False),
        sa.Column("default_style", sa.String(length=200), nullable=True),
        sa.Column("default_language", sa.String(length=16), nullable=False),
        sa.Column("default_fps", sa.Integer(), nullable=False),
        sa.Column("cover_image_path", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_projects_updated_created_id",
        "projects",
        ["updated_at", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_projects_updated_created_id", table_name="projects")
    op.drop_table("projects")
