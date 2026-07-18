from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.keyframe_generation import ACTIVE_RUN_STATUSES
from app.domain.video_generation import ACTIVE_VIDEO_RUN_STATUSES
from app.infrastructure.models.keyframe_generation import (
    KeyframeGenerationOutputRecord,
    KeyframeGenerationRunRecord,
)
from app.infrastructure.models.keyframe_task import KeyframeGenerationTaskRecord
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.quick_generate import QuickGenerateRequestRecord
from app.infrastructure.models.shot import ShotRecord
from app.infrastructure.models.video_generation import (
    VideoGenerationRunRecord,
    VideoGenerationTaskRecord,
)


class QuickGenerateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def project_exists(self, project_id: str) -> bool:
        return self.session.get(ProjectRecord, project_id) is not None

    def get_shot(self, project_id: str, shot_id: str) -> ShotRecord | None:
        return self.session.scalars(
            select(ShotRecord).where(
                ShotRecord.project_id == project_id,
                ShotRecord.id == shot_id,
            )
        ).first()

    def get_request(
        self,
        project_id: str,
        shot_id: str,
        mode: str,
        request_id: str,
    ) -> QuickGenerateRequestRecord | None:
        return self.session.scalars(
            select(QuickGenerateRequestRecord).where(
                QuickGenerateRequestRecord.project_id == project_id,
                QuickGenerateRequestRecord.shot_id == shot_id,
                QuickGenerateRequestRecord.mode == mode,
                QuickGenerateRequestRecord.request_id == request_id,
            )
        ).first()

    def create_request(self, record: QuickGenerateRequestRecord) -> QuickGenerateRequestRecord:
        try:
            self.session.add(record)
            self.session.commit()
            self.session.refresh(record)
            return record
        except Exception:
            self.session.rollback()
            raise

    def update_request(
        self,
        record: QuickGenerateRequestRecord,
        values: dict[str, object],
    ) -> QuickGenerateRequestRecord:
        try:
            for key, value in values.items():
                setattr(record, key, value)
            self.session.commit()
            self.session.refresh(record)
            return record
        except Exception:
            self.session.rollback()
            raise

    def get_keyframe_task_by_purpose(
        self,
        project_id: str,
        shot_id: str,
        purpose: str,
    ) -> KeyframeGenerationTaskRecord | None:
        return self.session.scalars(
            select(KeyframeGenerationTaskRecord)
            .where(
                KeyframeGenerationTaskRecord.project_id == project_id,
                KeyframeGenerationTaskRecord.shot_id == shot_id,
                KeyframeGenerationTaskRecord.purpose == purpose,
            )
            .order_by(
                KeyframeGenerationTaskRecord.updated_at.desc(),
                KeyframeGenerationTaskRecord.created_at.desc(),
                KeyframeGenerationTaskRecord.id.desc(),
            )
        ).first()

    def get_video_task(self, project_id: str, shot_id: str) -> VideoGenerationTaskRecord | None:
        return self.session.scalars(
            select(VideoGenerationTaskRecord)
            .where(
                VideoGenerationTaskRecord.project_id == project_id,
                VideoGenerationTaskRecord.shot_id == shot_id,
            )
            .order_by(
                VideoGenerationTaskRecord.updated_at.desc(),
                VideoGenerationTaskRecord.created_at.desc(),
                VideoGenerationTaskRecord.id.desc(),
            )
        ).first()

    def get_active_keyframe_run_for_purpose(
        self,
        project_id: str,
        shot_id: str,
        purpose: str,
    ) -> KeyframeGenerationRunRecord | None:
        return self.session.scalars(
            select(KeyframeGenerationRunRecord)
            .join(
                KeyframeGenerationTaskRecord,
                KeyframeGenerationTaskRecord.id == KeyframeGenerationRunRecord.keyframe_task_id,
            )
            .where(
                KeyframeGenerationRunRecord.project_id == project_id,
                KeyframeGenerationTaskRecord.shot_id == shot_id,
                KeyframeGenerationTaskRecord.purpose == purpose,
                KeyframeGenerationRunRecord.status.in_(ACTIVE_RUN_STATUSES),
            )
            .order_by(
                KeyframeGenerationRunRecord.created_at.asc(),
                KeyframeGenerationRunRecord.id.asc(),
            )
        ).first()

    def get_active_video_run(
        self,
        project_id: str,
        shot_id: str,
    ) -> VideoGenerationRunRecord | None:
        return self.session.scalars(
            select(VideoGenerationRunRecord)
            .join(
                VideoGenerationTaskRecord,
                VideoGenerationTaskRecord.id == VideoGenerationRunRecord.video_task_id,
            )
            .where(
                VideoGenerationRunRecord.project_id == project_id,
                VideoGenerationTaskRecord.shot_id == shot_id,
                VideoGenerationRunRecord.status.in_(ACTIVE_VIDEO_RUN_STATUSES),
            )
            .order_by(
                VideoGenerationRunRecord.created_at.asc(),
                VideoGenerationRunRecord.id.asc(),
            )
        ).first()

    def get_selected_keyframe_output(
        self,
        project_id: str,
        shot_id: str,
        purpose: str,
    ) -> KeyframeGenerationOutputRecord | None:
        return self.session.scalars(
            select(KeyframeGenerationOutputRecord)
            .join(
                KeyframeGenerationRunRecord,
                KeyframeGenerationRunRecord.id == KeyframeGenerationOutputRecord.run_id,
            )
            .join(
                KeyframeGenerationTaskRecord,
                KeyframeGenerationTaskRecord.id == KeyframeGenerationRunRecord.keyframe_task_id,
            )
            .where(
                KeyframeGenerationOutputRecord.project_id == project_id,
                KeyframeGenerationTaskRecord.shot_id == shot_id,
                KeyframeGenerationTaskRecord.purpose == purpose,
                KeyframeGenerationOutputRecord.is_selected.is_(True),
            )
            .order_by(
                KeyframeGenerationOutputRecord.created_at.desc(),
                KeyframeGenerationOutputRecord.id.desc(),
            )
        ).first()
