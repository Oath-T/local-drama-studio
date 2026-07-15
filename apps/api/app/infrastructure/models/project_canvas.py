from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class ProjectCanvasRecord(Base):
    __tablename__ = "project_canvases"
    __table_args__ = (
        CheckConstraint(
            "view_mode IN ('workflow', 'storyboard')", name="ck_project_canvases_view_mode"
        ),
        CheckConstraint("revision >= 1", name="ck_project_canvases_revision"),
        UniqueConstraint("project_id", name="uq_project_canvases_project_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    view_mode: Mapped[str] = mapped_column(String(24), nullable=False)
    viewport_json: Mapped[str] = mapped_column(Text, nullable=False)
    layout_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    nodes: Mapped[list["ProjectCanvasNodeRecord"]] = relationship(
        "ProjectCanvasNodeRecord",
        back_populates="canvas",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    edges: Mapped[list["ProjectCanvasEdgeRecord"]] = relationship(
        "ProjectCanvasEdgeRecord",
        back_populates="canvas",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ProjectCanvasNodeRecord(Base):
    __tablename__ = "project_canvas_nodes"
    __table_args__ = (
        CheckConstraint(
            "node_type IN ('text', 'character', 'scene', 'shot', 'image', 'video', 'export')",
            name="ck_project_canvas_nodes_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    canvas_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project_canvases.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    node_type: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    position_x: Mapped[float] = mapped_column(Float, nullable=False)
    position_y: Mapped[float] = mapped_column(Float, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)
    z_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entity_type: Mapped[str | None] = mapped_column(String(40), index=True, nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    data_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    canvas: Mapped[ProjectCanvasRecord] = relationship(
        "ProjectCanvasRecord", back_populates="nodes"
    )


class ProjectCanvasEdgeRecord(Base):
    __tablename__ = "project_canvas_edges"
    __table_args__ = (
        CheckConstraint(
            "semantic_type IN ('uses_character', 'uses_scene', 'identity_reference', "
            "'look_reference', "
            "'scene_reference', 'pose_reference', 'start_frame', 'end_frame', 'continuity_from', "
            "'generated_from', 'included_in_export')",
            name="ck_project_canvas_edges_semantic_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    canvas_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project_canvases.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_node_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project_canvas_nodes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    target_node_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project_canvas_nodes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_handle: Mapped[str | None] = mapped_column(String(80), nullable=True)
    target_handle: Mapped[str | None] = mapped_column(String(80), nullable=True)
    semantic_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    data_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    canvas: Mapped[ProjectCanvasRecord] = relationship(
        "ProjectCanvasRecord", back_populates="edges"
    )
