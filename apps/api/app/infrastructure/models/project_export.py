from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class ProjectExportRecord(Base):
    __tablename__ = "project_exports"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'ready', 'queued', 'running', 'completed', 'failed')",
            name="ck_project_exports_status",
        ),
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="ck_project_exports_progress",
        ),
        CheckConstraint("clip_count >= 0", name="ck_project_exports_clip_count"),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_project_exports_duration",
        ),
        CheckConstraint(
            "target_width BETWEEN 256 AND 3840 AND target_width % 2 = 0",
            name="ck_project_exports_width",
        ),
        CheckConstraint(
            "target_height BETWEEN 256 AND 3840 AND target_height % 2 = 0",
            name="ck_project_exports_height",
        ),
        CheckConstraint("target_fps BETWEEN 1 AND 60", name="ck_project_exports_fps"),
        CheckConstraint("video_codec IN ('libx264')", name="ck_project_exports_codec"),
        CheckConstraint("output_format IN ('mp4')", name="ck_project_exports_format"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_stage: Mapped[str] = mapped_column(String(120), nullable=False, default="准备中")
    clip_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_width: Mapped[int] = mapped_column(Integer, nullable=False)
    target_height: Mapped[int] = mapped_column(Integer, nullable=False)
    target_fps: Mapped[int] = mapped_column(Integer, nullable=False)
    video_codec: Mapped[str] = mapped_column(String(40), nullable=False)
    output_format: Mapped[str] = mapped_column(String(16), nullable=False)
    snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_media_asset_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
