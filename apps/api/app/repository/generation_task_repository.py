from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models.keyframe_generation import (
    KeyframeGenerationOutputRecord,
    KeyframeGenerationRunRecord,
)
from app.infrastructure.models.keyframe_task import KeyframeGenerationTaskRecord
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.shot import ShotRecord
from app.infrastructure.models.video_generation import (
    VideoGenerationOutputRecord,
    VideoGenerationRunRecord,
    VideoGenerationTaskRecord,
)


@dataclass(frozen=True)
class GenerationTaskSummaryData:
    task_type: str
    project_id: str
    task_id: str
    task_name: str
    task_status: str
    readiness_status: str | None
    shot_id: str
    shot_name: str
    workflow_id: str | None
    latest_run_id: str | None
    latest_run_number: int | None
    latest_run_status: str | None
    run_count: int
    output_count: int
    has_selected_output: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class _RunSummary:
    latest_run_id: str | None
    latest_run_number: int | None
    latest_run_status: str | None
    latest_workflow_id: str | None
    run_count: int


class GenerationTaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def project_exists(self, project_id: str) -> bool:
        return self.session.get(ProjectRecord, project_id) is not None

    def list_project_generation_tasks(self, project_id: str) -> list[GenerationTaskSummaryData]:
        keyframe_tasks = self._list_keyframe_tasks(project_id)
        video_tasks = self._list_video_tasks(project_id)
        items = [*keyframe_tasks, *video_tasks]
        return sorted(
            items,
            key=lambda item: (item.updated_at, item.created_at, item.task_id),
            reverse=True,
        )

    def _list_keyframe_tasks(self, project_id: str) -> list[GenerationTaskSummaryData]:
        rows = list(
            self.session.execute(
                select(KeyframeGenerationTaskRecord, ShotRecord.name)
                .join(ShotRecord, ShotRecord.id == KeyframeGenerationTaskRecord.shot_id)
                .where(KeyframeGenerationTaskRecord.project_id == project_id)
            ).all()
        )
        task_ids = [task.id for task, _shot_name in rows]
        runs_by_task_id = self._keyframe_run_summaries(task_ids)
        outputs_by_task_id = self._keyframe_output_summaries(task_ids)
        return [
            GenerationTaskSummaryData(
                task_type="keyframe",
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                task_status=task.status,
                readiness_status=None,
                shot_id=task.shot_id,
                shot_name=shot_name,
                workflow_id=runs_by_task_id.get(task.id, _empty_run_summary()).latest_workflow_id,
                latest_run_id=runs_by_task_id.get(task.id, _empty_run_summary()).latest_run_id,
                latest_run_number=runs_by_task_id.get(
                    task.id, _empty_run_summary()
                ).latest_run_number,
                latest_run_status=runs_by_task_id.get(
                    task.id, _empty_run_summary()
                ).latest_run_status,
                run_count=runs_by_task_id.get(task.id, _empty_run_summary()).run_count,
                output_count=outputs_by_task_id.get(task.id, (0, False))[0],
                has_selected_output=outputs_by_task_id.get(task.id, (0, False))[1],
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
            for task, shot_name in rows
        ]

    def _list_video_tasks(self, project_id: str) -> list[GenerationTaskSummaryData]:
        rows = list(
            self.session.execute(
                select(VideoGenerationTaskRecord, ShotRecord.name)
                .join(ShotRecord, ShotRecord.id == VideoGenerationTaskRecord.shot_id)
                .where(VideoGenerationTaskRecord.project_id == project_id)
            ).all()
        )
        task_ids = [task.id for task, _shot_name in rows]
        runs_by_task_id = self._video_run_summaries(task_ids)
        outputs_by_task_id = self._video_output_summaries(task_ids)
        return [
            GenerationTaskSummaryData(
                task_type="video",
                project_id=task.project_id,
                task_id=task.id,
                task_name=task.name,
                task_status=task.status,
                readiness_status=None,
                shot_id=task.shot_id,
                shot_name=shot_name,
                workflow_id=task.workflow_id,
                latest_run_id=runs_by_task_id.get(task.id, _empty_run_summary()).latest_run_id,
                latest_run_number=runs_by_task_id.get(
                    task.id, _empty_run_summary()
                ).latest_run_number,
                latest_run_status=runs_by_task_id.get(
                    task.id, _empty_run_summary()
                ).latest_run_status,
                run_count=runs_by_task_id.get(task.id, _empty_run_summary()).run_count,
                output_count=outputs_by_task_id.get(task.id, (0, False))[0],
                has_selected_output=outputs_by_task_id.get(task.id, (0, False))[1],
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
            for task, shot_name in rows
        ]

    def _keyframe_run_summaries(self, task_ids: list[str]) -> dict[str, _RunSummary]:
        if not task_ids:
            return {}
        runs = list(
            self.session.scalars(
                select(KeyframeGenerationRunRecord)
                .where(KeyframeGenerationRunRecord.keyframe_task_id.in_(task_ids))
                .order_by(
                    KeyframeGenerationRunRecord.keyframe_task_id.asc(),
                    KeyframeGenerationRunRecord.run_number.desc(),
                    KeyframeGenerationRunRecord.created_at.desc(),
                    KeyframeGenerationRunRecord.id.desc(),
                )
            ).all()
        )
        return _summarize_runs(runs, "keyframe_task_id")

    def _video_run_summaries(self, task_ids: list[str]) -> dict[str, _RunSummary]:
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
        return _summarize_runs(runs, "video_task_id")

    def _keyframe_output_summaries(self, task_ids: list[str]) -> dict[str, tuple[int, bool]]:
        if not task_ids:
            return {}
        rows = list(
            self.session.execute(
                select(
                    KeyframeGenerationRunRecord.keyframe_task_id,
                    KeyframeGenerationOutputRecord.is_selected,
                )
                .join(
                    KeyframeGenerationOutputRecord,
                    KeyframeGenerationOutputRecord.run_id == KeyframeGenerationRunRecord.id,
                )
                .where(KeyframeGenerationRunRecord.keyframe_task_id.in_(task_ids))
            ).all()
        )
        return _summarize_outputs(rows)

    def _video_output_summaries(self, task_ids: list[str]) -> dict[str, tuple[int, bool]]:
        if not task_ids:
            return {}
        rows = list(
            self.session.execute(
                select(
                    VideoGenerationRunRecord.video_task_id,
                    VideoGenerationOutputRecord.is_selected,
                )
                .join(
                    VideoGenerationOutputRecord,
                    VideoGenerationOutputRecord.run_id == VideoGenerationRunRecord.id,
                )
                .where(VideoGenerationRunRecord.video_task_id.in_(task_ids))
            ).all()
        )
        return _summarize_outputs(rows)


def _empty_run_summary() -> _RunSummary:
    return _RunSummary(
        latest_run_id=None,
        latest_run_number=None,
        latest_run_status=None,
        latest_workflow_id=None,
        run_count=0,
    )


def _summarize_runs(runs: list[object], task_id_attr: str) -> dict[str, _RunSummary]:
    grouped: dict[str, list[object]] = {}
    for run in runs:
        grouped.setdefault(str(getattr(run, task_id_attr)), []).append(run)
    summaries: dict[str, _RunSummary] = {}
    for task_id, task_runs in grouped.items():
        latest = task_runs[0]
        summaries[task_id] = _RunSummary(
            latest_run_id=str(latest.id),
            latest_run_number=int(latest.run_number),
            latest_run_status=str(latest.status),
            latest_workflow_id=str(latest.workflow_id),
            run_count=len(task_runs),
        )
    return summaries


def _summarize_outputs(rows: list[tuple[str, bool]]) -> dict[str, tuple[int, bool]]:
    summaries: dict[str, tuple[int, bool]] = {}
    for task_id, is_selected in rows:
        count, selected = summaries.get(task_id, (0, False))
        summaries[task_id] = (count + 1, selected or bool(is_selected))
    return summaries
