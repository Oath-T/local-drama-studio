from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class VisionAnalysisTaskRecord(Base):
    __tablename__ = "vision_analysis_tasks"
    __table_args__ = (
        CheckConstraint(
            """
            (
                target_type = 'character_reference'
                AND character_reference_id IS NOT NULL
                AND scene_reference_id IS NULL
            )
            OR
            (
                target_type = 'scene_reference'
                AND scene_reference_id IS NOT NULL
                AND character_reference_id IS NULL
            )
            """,
            name="ck_vision_analysis_task_target",
        ),
        Index(
            "ix_vision_analysis_tasks_character_active_lookup",
            "project_id",
            "target_type",
            "character_reference_id",
            "status",
        ),
        Index(
            "ix_vision_analysis_tasks_scene_active_lookup",
            "project_id",
            "target_type",
            "scene_reference_id",
            "status",
        ),
        Index(
            "ix_vision_analysis_tasks_latest_character",
            "character_reference_id",
            "created_at",
            "id",
        ),
        Index(
            "ix_vision_analysis_tasks_latest_scene",
            "scene_reference_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    character_reference_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("character_references.id", ondelete="CASCADE"),
        nullable=True,
    )
    scene_reference_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("scene_references.id", ondelete="CASCADE"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message_safe: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
