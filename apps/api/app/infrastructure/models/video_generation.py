from datetime import datetime

from sqlalchemy import (
    Boolean,
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


class VideoGenerationTaskRecord(Base):
    __tablename__ = "video_generation_tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'ready')",
            name="ck_video_generation_tasks_status",
        ),
        CheckConstraint(
            "duration_seconds > 0",
            name="ck_video_generation_tasks_duration",
        ),
        CheckConstraint("fps > 0", name="ck_video_generation_tasks_fps"),
        CheckConstraint(
            "width BETWEEN 256 AND 2048 AND width % 8 = 0",
            name="ck_video_generation_tasks_width",
        ),
        CheckConstraint(
            "height BETWEEN 256 AND 2048 AND height % 8 = 0",
            name="ck_video_generation_tasks_height",
        ),
        CheckConstraint("seed IS NULL OR seed >= 0", name="ck_video_generation_tasks_seed"),
        CheckConstraint(
            "motion_strength IS NULL OR (motion_strength >= 0 AND motion_strength <= 1)",
            name="ck_video_generation_tasks_motion_strength",
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
    input_media_asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("media_assets.id", ondelete="SET NULL"), index=True, nullable=True
    )
    source_keyframe_output_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("keyframe_generation_outputs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    source_keyframe_task_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("keyframe_generation_tasks.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    fps: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    motion_strength: Mapped[float | None] = mapped_column(Float, nullable=True)
    camera_motion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    workflow_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    runs: Mapped[list["VideoGenerationRunRecord"]] = relationship(
        "VideoGenerationRunRecord",
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    inputs: Mapped[list["VideoGenerationTaskInputRecord"]] = relationship(
        "VideoGenerationTaskInputRecord",
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class VideoGenerationTaskInputRecord(Base):
    __tablename__ = "video_generation_task_inputs"
    __table_args__ = (
        CheckConstraint(
            "role IN ('start_frame', 'end_frame')",
            name="ck_video_generation_task_inputs_role",
        ),
        CheckConstraint("sort_order >= 1", name="ck_video_generation_task_inputs_sort_order"),
        UniqueConstraint("task_id", "role", name="uq_video_generation_task_inputs_task_role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("video_generation_tasks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    media_asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("media_assets.id", ondelete="SET NULL"), index=True, nullable=True
    )
    source_keyframe_output_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("keyframe_generation_outputs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    source_keyframe_task_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("keyframe_generation_tasks.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    task: Mapped[VideoGenerationTaskRecord] = relationship(
        "VideoGenerationTaskRecord",
        back_populates="inputs",
    )


class VideoGenerationRunRecord(Base):
    __tablename__ = "video_generation_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'interrupted')",
            name="ck_video_generation_runs_status",
        ),
        CheckConstraint("run_number >= 1", name="ck_video_generation_runs_run_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    video_task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("video_generation_tasks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String(60), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(120), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    provider_job_id: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    submitted_payload_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message_safe: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    task: Mapped[VideoGenerationTaskRecord] = relationship(
        "VideoGenerationTaskRecord",
        back_populates="runs",
    )
    outputs: Mapped[list["VideoGenerationOutputRecord"]] = relationship(
        "VideoGenerationOutputRecord",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class VideoGenerationOutputRecord(Base):
    __tablename__ = "video_generation_outputs"
    __table_args__ = (
        CheckConstraint("output_index >= 1", name="ck_video_generation_outputs_index"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("video_generation_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    media_asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("media_assets.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    output_index: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_subfolder: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    provider_type: Mapped[str] = mapped_column(String(40), nullable=False, default="output")
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    fps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    run: Mapped[VideoGenerationRunRecord] = relationship(
        "VideoGenerationRunRecord",
        back_populates="outputs",
    )
