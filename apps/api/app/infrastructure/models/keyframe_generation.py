from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class KeyframeGenerationRunRecord(Base):
    __tablename__ = "keyframe_generation_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled', 'interrupted')",
            name="ck_keyframe_generation_runs_status",
        ),
        CheckConstraint("run_number >= 1", name="ck_keyframe_generation_runs_run_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    keyframe_task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("keyframe_generation_tasks.id", ondelete="CASCADE"),
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    outputs: Mapped[list["KeyframeGenerationOutputRecord"]] = relationship(
        "KeyframeGenerationOutputRecord",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class KeyframeGenerationOutputRecord(Base):
    __tablename__ = "keyframe_generation_outputs"
    __table_args__ = (
        CheckConstraint("output_index >= 1", name="ck_keyframe_generation_outputs_index"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("keyframe_generation_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    media_asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("media_assets.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    output_index: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_subfolder: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    run: Mapped[KeyframeGenerationRunRecord] = relationship(
        "KeyframeGenerationRunRecord",
        back_populates="outputs",
    )
