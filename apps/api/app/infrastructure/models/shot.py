from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class ShotRecord(Base):
    __tablename__ = "shots"
    __table_args__ = (
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds > 0",
            name="ck_shots_duration_seconds_positive",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    story_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    dialogue: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    shot_scale: Mapped[str] = mapped_column(String(40), nullable=False)
    camera_height: Mapped[str] = mapped_column(String(40), nullable=False)
    custom_camera_height: Mapped[str | None] = mapped_column(String(120), nullable=True)
    camera_angle: Mapped[str] = mapped_column(String(40), nullable=False)
    custom_camera_angle: Mapped[str | None] = mapped_column(String(120), nullable=True)
    composition_type: Mapped[str] = mapped_column(String(40), nullable=False)
    custom_composition: Mapped[str | None] = mapped_column(String(120), nullable=True)
    camera_movement: Mapped[str] = mapped_column(String(40), nullable=False)
    custom_camera_movement: Mapped[str | None] = mapped_column(String(120), nullable=True)
    focal_subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mood_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scene_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("scenes.id", ondelete="SET NULL"), index=True, nullable=True
    )
    scene_state_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("scene_states.id", ondelete="SET NULL"), index=True, nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    characters: Mapped[list["ShotCharacterRecord"]] = relationship(
        "ShotCharacterRecord",
        back_populates="shot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    references: Mapped[list["ShotReferenceRecord"]] = relationship(
        "ShotReferenceRecord",
        back_populates="shot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ShotCharacterRecord(Base):
    __tablename__ = "shot_characters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    shot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("shots.id", ondelete="CASCADE"), index=True, nullable=False
    )
    character_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("characters.id", ondelete="CASCADE"), index=True, nullable=False
    )
    look_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("character_looks.id", ondelete="SET NULL"), index=True, nullable=True
    )
    action_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expression_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    position_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_primary_subject: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    shot: Mapped[ShotRecord] = relationship("ShotRecord", back_populates="characters")
    references: Mapped[list["ShotReferenceRecord"]] = relationship(
        "ShotReferenceRecord",
        back_populates="shot_character",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ShotReferenceRecord(Base):
    __tablename__ = "shot_references"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    shot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("shots.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reference_type: Mapped[str] = mapped_column(String(24), nullable=False)
    character_reference_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("character_references.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    scene_reference_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("scene_references.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    media_asset_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    shot_character_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("shot_characters.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    purpose: Mapped[str] = mapped_column(String(40), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    shot: Mapped[ShotRecord] = relationship("ShotRecord", back_populates="references")
    shot_character: Mapped[ShotCharacterRecord | None] = relationship(
        "ShotCharacterRecord", back_populates="references"
    )
