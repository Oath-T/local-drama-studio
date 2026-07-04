from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.infrastructure.models.scene import SceneReferenceRecord


class CharacterRecord(Base):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    aliases: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    appearance_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    personality_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_identity: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    looks: Mapped[list["CharacterLookRecord"]] = relationship(
        "CharacterLookRecord",
        back_populates="character",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CharacterLookRecord(Base):
    __tablename__ = "character_looks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    character_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("characters.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    costume_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    hair_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    makeup_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_appearance: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    character: Mapped[CharacterRecord] = relationship("CharacterRecord", back_populates="looks")
    references: Mapped[list["CharacterReferenceRecord"]] = relationship(
        "CharacterReferenceRecord",
        back_populates="look",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class MediaAssetRecord(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    media_type: Mapped[str] = mapped_column(String(24), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(800), nullable=False)
    thumbnail_relative_path: Mapped[str | None] = mapped_column(String(800), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    extension: Mapped[str] = mapped_column(String(16), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    references: Mapped[list["CharacterReferenceRecord"]] = relationship(
        "CharacterReferenceRecord",
        back_populates="media_asset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    scene_references: Mapped[list["SceneReferenceRecord"]] = relationship(
        "SceneReferenceRecord",
        back_populates="media_asset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CharacterReferenceRecord(Base):
    __tablename__ = "character_references"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    look_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("character_looks.id", ondelete="CASCADE"), index=True, nullable=False
    )
    media_asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("media_assets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    shot_type: Mapped[str] = mapped_column(String(40), nullable=False)
    view_angle: Mapped[str] = mapped_column(String(40), nullable=False)
    expression: Mapped[str] = mapped_column(String(40), nullable=False)
    pose_type: Mapped[str] = mapped_column(String(40), nullable=False)
    custom_expression: Mapped[str | None] = mapped_column(String(100), nullable=True)
    custom_pose: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_identity_anchor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    analysis_status: Mapped[str] = mapped_column(String(32), nullable=False)
    suggestion_review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    analysis_suggestions: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    look: Mapped[CharacterLookRecord] = relationship(
        "CharacterLookRecord", back_populates="references"
    )
    media_asset: Mapped[MediaAssetRecord] = relationship(
        "MediaAssetRecord", back_populates="references"
    )
