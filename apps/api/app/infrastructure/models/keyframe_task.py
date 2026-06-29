from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class KeyframeGenerationTaskRecord(Base):
    __tablename__ = "keyframe_generation_tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'ready')",
            name="ck_keyframe_generation_tasks_status",
        ),
        CheckConstraint(
            "aspect_ratio IN ('16:9', '9:16', '1:1', '4:3', '3:4', 'custom')",
            name="ck_keyframe_generation_tasks_aspect_ratio",
        ),
        CheckConstraint(
            "width BETWEEN 256 AND 4096 AND width % 8 = 0",
            name="ck_keyframe_generation_tasks_width",
        ),
        CheckConstraint(
            "height BETWEEN 256 AND 4096 AND height % 8 = 0",
            name="ck_keyframe_generation_tasks_height",
        ),
        CheckConstraint(
            "seed IS NULL OR seed >= 0",
            name="ck_keyframe_generation_tasks_seed",
        ),
        CheckConstraint(
            "steps BETWEEN 1 AND 150",
            name="ck_keyframe_generation_tasks_steps",
        ),
        CheckConstraint(
            "guidance_scale BETWEEN 0 AND 30",
            name="ck_keyframe_generation_tasks_guidance",
        ),
        CheckConstraint(
            "output_count BETWEEN 1 AND 8",
            name="ck_keyframe_generation_tasks_output_count",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    shot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("shots.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    shot_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    source_shot_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    prompt_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    aspect_ratio: Mapped[str] = mapped_column(String(16), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    steps: Mapped[int] = mapped_column(Integer, nullable=False)
    guidance_scale: Mapped[float] = mapped_column(Float, nullable=False)
    sampler_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    scheduler_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_provider: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    output_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    references: Mapped[list["KeyframeGenerationTaskReferenceRecord"]] = relationship(
        "KeyframeGenerationTaskReferenceRecord",
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class KeyframeGenerationTaskReferenceRecord(Base):
    __tablename__ = "keyframe_generation_task_references"
    __table_args__ = (
        CheckConstraint(
            "reference_type IN ('character', 'scene')",
            name="ck_keyframe_generation_task_references_type",
        ),
        CheckConstraint(
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
            name="ck_keyframe_generation_task_references_type_target",
        ),
        CheckConstraint(
            "order_index >= 0",
            name="ck_keyframe_generation_task_references_order",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("keyframe_generation_tasks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    reference_type: Mapped[str] = mapped_column(String(24), nullable=False)
    shot_reference_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("shot_references.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    character_reference_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("character_references.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    scene_reference_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("scene_references.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    media_asset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    purpose: Mapped[str] = mapped_column(String(40), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    source_shot_character_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_character_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_look_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_scene_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_scene_state_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    task: Mapped[KeyframeGenerationTaskRecord] = relationship(
        "KeyframeGenerationTaskRecord",
        back_populates="references",
    )
