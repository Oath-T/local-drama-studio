from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.shot import ShotRecord
from app.infrastructure.models.video_generation import (
    VideoGenerationOutputRecord,
    VideoGenerationRunRecord,
    VideoGenerationTaskRecord,
)


@dataclass(frozen=True)
class SelectedVideoOutputData:
    shot_id: str
    output: VideoGenerationOutputRecord
    media_asset: MediaAssetRecord | None


@dataclass(frozen=True)
class ProjectTimelineData:
    project: ProjectRecord
    shots: list[ShotRecord]
    selected_outputs_by_shot_id: dict[str, SelectedVideoOutputData]


class ProjectTimelineRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def load_project_timeline(self, project_id: str) -> ProjectTimelineData | None:
        project = self.session.get(ProjectRecord, project_id)
        if project is None:
            return None
        shots = list(
            self.session.scalars(
                select(ShotRecord)
                .where(ShotRecord.project_id == project_id)
                .order_by(
                    ShotRecord.order_index.asc(),
                    ShotRecord.created_at.asc(),
                    ShotRecord.id.asc(),
                )
            ).all()
        )
        selected_outputs = self._selected_outputs(project_id)
        media_assets = self._media_assets([item.output.media_asset_id for item in selected_outputs])
        return ProjectTimelineData(
            project=project,
            shots=shots,
            selected_outputs_by_shot_id={
                item.shot_id: SelectedVideoOutputData(
                    shot_id=item.shot_id,
                    output=item.output,
                    media_asset=media_assets.get(item.output.media_asset_id),
                )
                for item in selected_outputs
            },
        )

    def _selected_outputs(self, project_id: str) -> list[SelectedVideoOutputData]:
        rows = list(
            self.session.execute(
                select(VideoGenerationTaskRecord.shot_id, VideoGenerationOutputRecord)
                .join(
                    VideoGenerationRunRecord,
                    VideoGenerationRunRecord.video_task_id == VideoGenerationTaskRecord.id,
                )
                .join(
                    VideoGenerationOutputRecord,
                    VideoGenerationOutputRecord.run_id == VideoGenerationRunRecord.id,
                )
                .where(
                    VideoGenerationTaskRecord.project_id == project_id,
                    VideoGenerationOutputRecord.project_id == project_id,
                    VideoGenerationRunRecord.status == "completed",
                    VideoGenerationOutputRecord.is_selected.is_(True),
                )
                .order_by(
                    VideoGenerationOutputRecord.created_at.desc(),
                    VideoGenerationOutputRecord.id.desc(),
                )
            ).all()
        )
        selected_by_shot: dict[str, VideoGenerationOutputRecord] = {}
        for shot_id, output in rows:
            selected_by_shot.setdefault(shot_id, output)
        return [
            SelectedVideoOutputData(shot_id=shot_id, output=output, media_asset=None)
            for shot_id, output in selected_by_shot.items()
        ]

    def _media_assets(self, media_asset_ids: list[str]) -> dict[str, MediaAssetRecord]:
        if not media_asset_ids:
            return {}
        records = list(
            self.session.scalars(
                select(MediaAssetRecord).where(
                    MediaAssetRecord.id.in_(sorted(set(media_asset_ids)))
                )
            ).all()
        )
        return {record.id: record for record in records}
