from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.domain.video_generation import ACTIVE_VIDEO_RUN_STATUSES
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.keyframe_generation import KeyframeGenerationOutputRecord
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.shot import ShotRecord
from app.infrastructure.models.video_generation import (
    VideoGenerationOutputRecord,
    VideoGenerationRunRecord,
    VideoGenerationTaskRecord,
)


@dataclass(frozen=True)
class VideoTaskListData:
    tasks: list[VideoGenerationTaskRecord]
    media_assets_by_id: dict[str, MediaAssetRecord]
    latest_run_status_by_task_id: dict[str, str]
    selected_outputs_by_task_id: dict[str, VideoGenerationOutputRecord]
    selected_media_assets_by_id: dict[str, MediaAssetRecord]
    total: int


@dataclass(frozen=True)
class VideoRunListData:
    runs: list[VideoGenerationRunRecord]
    outputs_by_run_id: dict[str, list[VideoGenerationOutputRecord]]
    media_assets_by_id: dict[str, MediaAssetRecord]
    total: int


class VideoGenerationRepository:
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

    def get_media_asset(self, project_id: str, media_asset_id: str) -> MediaAssetRecord | None:
        return self.session.scalars(
            select(MediaAssetRecord).where(
                MediaAssetRecord.project_id == project_id,
                MediaAssetRecord.id == media_asset_id,
            )
        ).first()

    def get_keyframe_output_media_asset(
        self, project_id: str, output_id: str
    ) -> MediaAssetRecord | None:
        output = self.session.scalars(
            select(KeyframeGenerationOutputRecord).where(
                KeyframeGenerationOutputRecord.project_id == project_id,
                KeyframeGenerationOutputRecord.id == output_id,
            )
        ).first()
        if output is None:
            return None
        return self.get_media_asset(project_id, output.media_asset_id)

    def create_task(self, task: VideoGenerationTaskRecord) -> VideoGenerationTaskRecord:
        try:
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)
            return task
        except Exception:
            self.session.rollback()
            raise

    def update_task(
        self,
        task: VideoGenerationTaskRecord,
        values: dict[str, object],
    ) -> VideoGenerationTaskRecord:
        try:
            for key, value in values.items():
                setattr(task, key, value)
            self.session.commit()
            self.session.refresh(task)
            return task
        except Exception:
            self.session.rollback()
            raise

    def delete_task(self, task: VideoGenerationTaskRecord) -> None:
        try:
            self.session.delete(task)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def get_task(self, project_id: str, task_id: str) -> VideoGenerationTaskRecord | None:
        return self.session.scalars(
            select(VideoGenerationTaskRecord).where(
                VideoGenerationTaskRecord.project_id == project_id,
                VideoGenerationTaskRecord.id == task_id,
            )
        ).first()

    def list_tasks_for_shot(self, project_id: str, shot_id: str) -> VideoTaskListData:
        tasks = list(
            self.session.scalars(
                select(VideoGenerationTaskRecord)
                .where(
                    VideoGenerationTaskRecord.project_id == project_id,
                    VideoGenerationTaskRecord.shot_id == shot_id,
                )
                .order_by(
                    VideoGenerationTaskRecord.updated_at.desc(),
                    VideoGenerationTaskRecord.created_at.desc(),
                    VideoGenerationTaskRecord.id.asc(),
                )
            ).all()
        )
        total = (
            self.session.scalar(
                select(func.count())
                .select_from(VideoGenerationTaskRecord)
                .where(
                    VideoGenerationTaskRecord.project_id == project_id,
                    VideoGenerationTaskRecord.shot_id == shot_id,
                )
            )
            or 0
        )
        media_assets_by_id = self.get_media_assets_by_ids(
            sorted({task.input_media_asset_id for task in tasks if task.input_media_asset_id})
        )
        task_ids = [task.id for task in tasks]
        latest_run_status = self.latest_run_status_by_task_ids(task_ids)
        selected_outputs = self.selected_outputs_by_task_ids(task_ids)
        selected_media_assets = self.get_media_assets_by_ids(
            sorted({output.media_asset_id for output in selected_outputs.values()})
        )
        return VideoTaskListData(
            tasks=tasks,
            media_assets_by_id=media_assets_by_id,
            latest_run_status_by_task_id=latest_run_status,
            selected_outputs_by_task_id=selected_outputs,
            selected_media_assets_by_id=selected_media_assets,
            total=total,
        )

    def get_media_assets_by_ids(self, ids: list[str]) -> dict[str, MediaAssetRecord]:
        if not ids:
            return {}
        return {
            record.id: record
            for record in self.session.scalars(
                select(MediaAssetRecord).where(MediaAssetRecord.id.in_(ids))
            ).all()
        }

    def latest_run_status_by_task_ids(self, task_ids: list[str]) -> dict[str, str]:
        if not task_ids:
            return {}
        runs = list(
            self.session.scalars(
                select(VideoGenerationRunRecord)
                .where(VideoGenerationRunRecord.video_task_id.in_(task_ids))
                .order_by(
                    VideoGenerationRunRecord.video_task_id.asc(),
                    VideoGenerationRunRecord.run_number.desc(),
                    VideoGenerationRunRecord.created_at.desc(),
                    VideoGenerationRunRecord.id.desc(),
                )
            ).all()
        )
        statuses: dict[str, str] = {}
        for run in runs:
            statuses.setdefault(run.video_task_id, run.status)
        return statuses

    def selected_outputs_by_task_ids(
        self, task_ids: list[str]
    ) -> dict[str, VideoGenerationOutputRecord]:
        if not task_ids:
            return {}
        rows = list(
            self.session.execute(
                select(VideoGenerationRunRecord.video_task_id, VideoGenerationOutputRecord)
                .join(
                    VideoGenerationOutputRecord,
                    VideoGenerationOutputRecord.run_id == VideoGenerationRunRecord.id,
                )
                .where(
                    VideoGenerationRunRecord.video_task_id.in_(task_ids),
                    VideoGenerationOutputRecord.is_selected.is_(True),
                )
            ).all()
        )
        return {task_id: output for task_id, output in rows}

    def get_active_run_for_task(self, task_id: str) -> VideoGenerationRunRecord | None:
        return self.session.scalars(
            select(VideoGenerationRunRecord)
            .where(
                VideoGenerationRunRecord.video_task_id == task_id,
                VideoGenerationRunRecord.status.in_(ACTIVE_VIDEO_RUN_STATUSES),
            )
            .order_by(
                VideoGenerationRunRecord.created_at.asc(),
                VideoGenerationRunRecord.id.asc(),
            )
        ).first()

    def next_run_number(self, task_id: str) -> int:
        current = self.session.scalar(
            select(func.max(VideoGenerationRunRecord.run_number)).where(
                VideoGenerationRunRecord.video_task_id == task_id
            )
        )
        return int(current or 0) + 1

    def create_run(self, run: VideoGenerationRunRecord) -> VideoGenerationRunRecord:
        try:
            self.session.add(run)
            self.session.commit()
            self.session.refresh(run)
            return run
        except Exception:
            self.session.rollback()
            raise

    def update_run(self, run: VideoGenerationRunRecord, values: dict[str, object]) -> None:
        try:
            for key, value in values.items():
                setattr(run, key, value)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def get_run(self, project_id: str, run_id: str) -> VideoGenerationRunRecord | None:
        return self.session.scalars(
            select(VideoGenerationRunRecord).where(
                VideoGenerationRunRecord.project_id == project_id,
                VideoGenerationRunRecord.id == run_id,
            )
        ).first()

    def get_run_by_id(self, run_id: str) -> VideoGenerationRunRecord | None:
        return self.session.get(VideoGenerationRunRecord, run_id)

    def list_runs_for_task(self, project_id: str, task_id: str) -> VideoRunListData:
        runs = list(
            self.session.scalars(
                select(VideoGenerationRunRecord)
                .where(
                    VideoGenerationRunRecord.project_id == project_id,
                    VideoGenerationRunRecord.video_task_id == task_id,
                )
                .order_by(
                    VideoGenerationRunRecord.run_number.desc(),
                    VideoGenerationRunRecord.created_at.desc(),
                    VideoGenerationRunRecord.id.desc(),
                )
            ).all()
        )
        total = (
            self.session.scalar(
                select(func.count())
                .select_from(VideoGenerationRunRecord)
                .where(
                    VideoGenerationRunRecord.project_id == project_id,
                    VideoGenerationRunRecord.video_task_id == task_id,
                )
            )
            or 0
        )
        outputs_by_run_id = self.list_outputs_for_runs([run.id for run in runs])
        media_assets = self.get_media_assets_by_ids(
            sorted(
                {
                    output.media_asset_id
                    for outputs in outputs_by_run_id.values()
                    for output in outputs
                }
            )
        )
        return VideoRunListData(
            runs=runs,
            outputs_by_run_id=outputs_by_run_id,
            media_assets_by_id=media_assets,
            total=total,
        )

    def list_outputs_for_runs(
        self, run_ids: list[str]
    ) -> dict[str, list[VideoGenerationOutputRecord]]:
        if not run_ids:
            return {}
        outputs = list(
            self.session.scalars(
                select(VideoGenerationOutputRecord)
                .where(VideoGenerationOutputRecord.run_id.in_(run_ids))
                .order_by(
                    VideoGenerationOutputRecord.run_id.asc(),
                    VideoGenerationOutputRecord.output_index.asc(),
                    VideoGenerationOutputRecord.id.asc(),
                )
            ).all()
        )
        grouped: dict[str, list[VideoGenerationOutputRecord]] = {run_id: [] for run_id in run_ids}
        for output in outputs:
            grouped.setdefault(output.run_id, []).append(output)
        return grouped

    def output_exists(
        self,
        run_id: str,
        provider_filename: str,
        provider_subfolder: str,
        provider_type: str,
        output_index: int,
    ) -> bool:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(VideoGenerationOutputRecord)
                .where(
                    VideoGenerationOutputRecord.run_id == run_id,
                    VideoGenerationOutputRecord.provider_filename == provider_filename,
                    VideoGenerationOutputRecord.provider_subfolder == provider_subfolder,
                    VideoGenerationOutputRecord.provider_type == provider_type,
                    VideoGenerationOutputRecord.output_index == output_index,
                )
            )
            or 0
        ) > 0

    def create_output_with_media(
        self,
        media_asset: MediaAssetRecord,
        output: VideoGenerationOutputRecord,
    ) -> None:
        try:
            self.session.add(media_asset)
            self.session.add(output)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def get_output(self, project_id: str, output_id: str) -> VideoGenerationOutputRecord | None:
        return self.session.scalars(
            select(VideoGenerationOutputRecord).where(
                VideoGenerationOutputRecord.project_id == project_id,
                VideoGenerationOutputRecord.id == output_id,
            )
        ).first()

    def media_asset_for_output(
        self, output: VideoGenerationOutputRecord
    ) -> MediaAssetRecord | None:
        return self.session.get(MediaAssetRecord, output.media_asset_id)

    def select_output(self, output: VideoGenerationOutputRecord) -> None:
        try:
            run = self.session.get(VideoGenerationRunRecord, output.run_id)
            if run is None:
                return
            task_run_ids = list(
                self.session.scalars(
                    select(VideoGenerationRunRecord.id).where(
                        VideoGenerationRunRecord.video_task_id == run.video_task_id
                    )
                ).all()
            )
            if task_run_ids:
                for record in self.session.scalars(
                    select(VideoGenerationOutputRecord).where(
                        VideoGenerationOutputRecord.run_id.in_(task_run_ids)
                    )
                ):
                    record.is_selected = False
            output.is_selected = True
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def unselect_output(self, output: VideoGenerationOutputRecord) -> None:
        try:
            output.is_selected = False
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def list_active_runs(self) -> list[VideoGenerationRunRecord]:
        try:
            return list(
                self.session.scalars(
                    select(VideoGenerationRunRecord)
                    .where(VideoGenerationRunRecord.status.in_(ACTIVE_VIDEO_RUN_STATUSES))
                    .order_by(
                        VideoGenerationRunRecord.created_at.asc(),
                        VideoGenerationRunRecord.id.asc(),
                    )
                ).all()
            )
        except SQLAlchemyError:
            self.session.rollback()
            return []

    def create_media_asset(self, media_asset: MediaAssetRecord) -> MediaAssetRecord:
        try:
            self.session.add(media_asset)
            self.session.commit()
            self.session.refresh(media_asset)
            return media_asset
        except Exception:
            self.session.rollback()
            raise
