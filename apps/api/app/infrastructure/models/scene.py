from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base
from app.infrastructure.models.character import MediaAssetRecord


class SceneRecord(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    scene_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    fixed_environment_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    spatial_layout_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_style_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_environment: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    states: Mapped[list["SceneStateRecord"]] = relationship(
        "SceneStateRecord",
        back_populates="scene",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class SceneStateRecord(Base):
    __tablename__ = "scene_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scene_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scenes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_of_day: Mapped[str] = mapped_column(String(32), nullable=False)
    weather: Mapped[str] = mapped_column(String(32), nullable=False)
    custom_weather: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lighting: Mapped[str] = mapped_column(String(32), nullable=False)
    custom_lighting: Mapped[str | None] = mapped_column(String(120), nullable=True)
    season: Mapped[str] = mapped_column(String(32), nullable=False)
    environment_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    crowd_level: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    scene: Mapped[SceneRecord] = relationship("SceneRecord", back_populates="states")
    references: Mapped[list["SceneReferenceRecord"]] = relationship(
        "SceneReferenceRecord",
        back_populates="state",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class SceneReferenceRecord(Base):
    __tablename__ = "scene_references"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    state_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scene_states.id", ondelete="CASCADE"), index=True, nullable=False
    )
    media_asset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        index=True,
        unique=True,
        nullable=False,
    )
    shot_scale: Mapped[str] = mapped_column(String(40), nullable=False)
    camera_position: Mapped[str] = mapped_column(String(40), nullable=False)
    custom_camera_position: Mapped[str | None] = mapped_column(String(120), nullable=True)
    view_direction: Mapped[str] = mapped_column(String(40), nullable=False)
    custom_view_direction: Mapped[str | None] = mapped_column(String(120), nullable=True)
    composition_type: Mapped[str] = mapped_column(String(40), nullable=False)
    custom_composition: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_empty_plate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_spatial_anchor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tags: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_status: Mapped[str] = mapped_column(String(32), nullable=False)
    suggestion_review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    analysis_suggestions: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    state: Mapped[SceneStateRecord] = relationship("SceneStateRecord", back_populates="references")
    media_asset: Mapped[MediaAssetRecord] = relationship(
        "MediaAssetRecord", back_populates="scene_references"
    )
