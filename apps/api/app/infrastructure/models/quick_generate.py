from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class QuickGenerateRequestRecord(Base):
    __tablename__ = "quick_generate_requests"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('first_frame', 'end_frame', 'video')",
            name="ck_quick_generate_requests_mode",
        ),
        CheckConstraint(
            "run_type IS NULL OR run_type IN ('keyframe', 'video')",
            name="ck_quick_generate_requests_run_type",
        ),
        UniqueConstraint(
            "project_id",
            "shot_id",
            "mode",
            "request_id",
            name="uq_quick_generate_requests_request",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    shot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("shots.id", ondelete="CASCADE"), index=True, nullable=False
    )
    mode: Mapped[str] = mapped_column(String(24), nullable=False)
    request_id: Mapped[str] = mapped_column(String(120), nullable=False)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    run_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    run_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    response_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
