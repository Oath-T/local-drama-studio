from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.models.character import CharacterRecord, MediaAssetRecord
from app.infrastructure.models.keyframe_generation import (
    KeyframeGenerationOutputRecord,
    KeyframeGenerationRunRecord,
)
from app.infrastructure.models.keyframe_task import KeyframeGenerationTaskRecord
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.scene import SceneRecord, SceneStateRecord
from app.infrastructure.models.shot import ShotCharacterRecord, ShotRecord, ShotReferenceRecord
from app.infrastructure.models.video_generation import (
    VideoGenerationOutputRecord,
    VideoGenerationRunRecord,
    VideoGenerationTaskInputRecord,
    VideoGenerationTaskRecord,
)


@dataclass(frozen=True)
class ProductionStatusData:
    shots: list[ShotRecord]
    shot_character_counts: dict[str, int]
    shot_reference_counts: dict[str, int]
    primary_subject_counts: dict[str, int]
    character_names_by_shot: dict[str, list[str]]
    scenes: dict[str, SceneRecord]
    scene_states: dict[str, SceneStateRecord]
    keyframe_tasks_by_shot: dict[str, list[KeyframeGenerationTaskRecord]]
    keyframe_runs_by_task: dict[str, list[KeyframeGenerationRunRecord]]
    keyframe_outputs_by_task: dict[str, list[KeyframeGenerationOutputRecord]]
    video_tasks_by_shot: dict[str, list[VideoGenerationTaskRecord]]
    video_runs_by_task: dict[str, list[VideoGenerationRunRecord]]
    video_outputs_by_task: dict[str, list[VideoGenerationOutputRecord]]
    video_inputs_by_task: dict[str, list[VideoGenerationTaskInputRecord]]
    media_assets: dict[str, MediaAssetRecord]


class ProductionStatusRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def project_exists(self, project_id: str) -> bool:
        return self.session.get(ProjectRecord, project_id) is not None

    def load_project(self, project_id: str) -> ProductionStatusData:
        shots = list(
            self.session.scalars(
                select(ShotRecord)
                .where(ShotRecord.project_id == project_id)
                .order_by(
                    ShotRecord.order_index.asc(), ShotRecord.created_at.asc(), ShotRecord.id.asc()
                )
            ).all()
        )
        return self._load_for_shots(project_id, shots)

    def load_shot(self, project_id: str, shot_id: str) -> ProductionStatusData | None:
        shot = self.session.scalars(
            select(ShotRecord).where(ShotRecord.project_id == project_id, ShotRecord.id == shot_id)
        ).first()
        if shot is None:
            return None
        all_shots = list(
            self.session.scalars(
                select(ShotRecord)
                .where(ShotRecord.project_id == project_id)
                .order_by(
                    ShotRecord.order_index.asc(), ShotRecord.created_at.asc(), ShotRecord.id.asc()
                )
            ).all()
        )
        return self._load_for_shots(project_id, all_shots)

    def _load_for_shots(self, project_id: str, shots: list[ShotRecord]) -> ProductionStatusData:
        shot_ids = [shot.id for shot in shots]
        if not shot_ids:
            return ProductionStatusData(
                shots=[],
                shot_character_counts={},
                shot_reference_counts={},
                primary_subject_counts={},
                character_names_by_shot={},
                scenes={},
                scene_states={},
                keyframe_tasks_by_shot={},
                keyframe_runs_by_task={},
                keyframe_outputs_by_task={},
                video_tasks_by_shot={},
                video_runs_by_task={},
                video_outputs_by_task={},
                video_inputs_by_task={},
                media_assets={},
            )

        shot_character_counts = self._count_by_shot(ShotCharacterRecord.shot_id, shot_ids)
        shot_reference_counts = self._count_by_shot(ShotReferenceRecord.shot_id, shot_ids)
        primary_subject_counts = dict(
            self.session.execute(
                select(ShotCharacterRecord.shot_id, func.count(ShotCharacterRecord.id))
                .where(
                    ShotCharacterRecord.shot_id.in_(shot_ids),
                    ShotCharacterRecord.is_primary_subject.is_(True),
                )
                .group_by(ShotCharacterRecord.shot_id)
            ).all()
        )
        character_names_by_shot = self._character_names_by_shot(shot_ids)
        scene_ids = sorted({shot.scene_id for shot in shots if shot.scene_id})
        state_ids = sorted({shot.scene_state_id for shot in shots if shot.scene_state_id})
        scenes = self._records_by_id(SceneRecord, scene_ids)
        scene_states = self._records_by_id(SceneStateRecord, state_ids)
        keyframe_tasks = self._list_keyframe_tasks(project_id, shot_ids)
        video_tasks = self._list_video_tasks(project_id, shot_ids)
        keyframe_task_ids = [task.id for task in keyframe_tasks]
        video_task_ids = [task.id for task in video_tasks]
        keyframe_runs = self._list_keyframe_runs(keyframe_task_ids)
        video_runs = self._list_video_runs(video_task_ids)
        keyframe_outputs = self._list_keyframe_outputs([run.id for run in keyframe_runs])
        video_outputs = self._list_video_outputs([run.id for run in video_runs])
        video_inputs = self._list_video_inputs(video_task_ids)
        media_ids = {
            output.media_asset_id
            for output in [*keyframe_outputs, *video_outputs]
            if output.media_asset_id
        }
        media_assets = self._records_by_id(MediaAssetRecord, sorted(media_ids))
        return ProductionStatusData(
            shots=shots,
            shot_character_counts={key: int(value) for key, value in shot_character_counts.items()},
            shot_reference_counts={key: int(value) for key, value in shot_reference_counts.items()},
            primary_subject_counts={
                key: int(value) for key, value in primary_subject_counts.items()
            },
            character_names_by_shot=character_names_by_shot,
            scenes=scenes,
            scene_states=scene_states,
            keyframe_tasks_by_shot=_group_by(keyframe_tasks, "shot_id"),
            keyframe_runs_by_task=_group_by(keyframe_runs, "keyframe_task_id"),
            keyframe_outputs_by_task=self._keyframe_outputs_by_task(
                keyframe_outputs, keyframe_runs
            ),
            video_tasks_by_shot=_group_by(video_tasks, "shot_id"),
            video_runs_by_task=_group_by(video_runs, "video_task_id"),
            video_outputs_by_task=self._video_outputs_by_task(video_outputs, video_runs),
            video_inputs_by_task=_group_by(video_inputs, "task_id"),
            media_assets=media_assets,
        )

    def _count_by_shot(self, column, shot_ids: list[str]) -> dict[str, int]:
        return dict(
            self.session.execute(
                select(column, func.count()).where(column.in_(shot_ids)).group_by(column)
            ).all()
        )

    def _character_names_by_shot(self, shot_ids: list[str]) -> dict[str, list[str]]:
        rows = list(
            self.session.execute(
                select(ShotCharacterRecord.shot_id, CharacterRecord.name)
                .join(CharacterRecord, CharacterRecord.id == ShotCharacterRecord.character_id)
                .where(ShotCharacterRecord.shot_id.in_(shot_ids))
                .order_by(ShotCharacterRecord.order_index.asc(), ShotCharacterRecord.id.asc())
            ).all()
        )
        grouped: dict[str, list[str]] = {}
        for shot_id, name in rows:
            grouped.setdefault(str(shot_id), []).append(str(name))
        return grouped

    def _records_by_id(self, model, ids: list[str]) -> dict[str, object]:
        if not ids:
            return {}
        return {
            record.id: record
            for record in self.session.scalars(select(model).where(model.id.in_(ids))).all()
        }

    def _list_keyframe_tasks(
        self, project_id: str, shot_ids: list[str]
    ) -> list[KeyframeGenerationTaskRecord]:
        return list(
            self.session.scalars(
                select(KeyframeGenerationTaskRecord)
                .where(
                    KeyframeGenerationTaskRecord.project_id == project_id,
                    KeyframeGenerationTaskRecord.shot_id.in_(shot_ids),
                )
                .order_by(
                    KeyframeGenerationTaskRecord.created_at.desc(),
                    KeyframeGenerationTaskRecord.id.desc(),
                )
            ).all()
        )

    def _list_video_tasks(
        self, project_id: str, shot_ids: list[str]
    ) -> list[VideoGenerationTaskRecord]:
        return list(
            self.session.scalars(
                select(VideoGenerationTaskRecord)
                .where(
                    VideoGenerationTaskRecord.project_id == project_id,
                    VideoGenerationTaskRecord.shot_id.in_(shot_ids),
                )
                .order_by(
                    VideoGenerationTaskRecord.created_at.desc(),
                    VideoGenerationTaskRecord.id.desc(),
                )
            ).all()
        )

    def _list_keyframe_runs(self, task_ids: list[str]) -> list[KeyframeGenerationRunRecord]:
        if not task_ids:
            return []
        return list(
            self.session.scalars(
                select(KeyframeGenerationRunRecord)
                .where(KeyframeGenerationRunRecord.keyframe_task_id.in_(task_ids))
                .order_by(
                    KeyframeGenerationRunRecord.run_number.desc(),
                    KeyframeGenerationRunRecord.created_at.desc(),
                    KeyframeGenerationRunRecord.id.desc(),
                )
            ).all()
        )

    def _list_video_runs(self, task_ids: list[str]) -> list[VideoGenerationRunRecord]:
        if not task_ids:
            return []
        return list(
            self.session.scalars(
                select(VideoGenerationRunRecord)
                .where(VideoGenerationRunRecord.video_task_id.in_(task_ids))
                .order_by(
                    VideoGenerationRunRecord.run_number.desc(),
                    VideoGenerationRunRecord.created_at.desc(),
                    VideoGenerationRunRecord.id.desc(),
                )
            ).all()
        )

    def _list_keyframe_outputs(self, run_ids: list[str]) -> list[KeyframeGenerationOutputRecord]:
        if not run_ids:
            return []
        return list(
            self.session.scalars(
                select(KeyframeGenerationOutputRecord)
                .where(KeyframeGenerationOutputRecord.run_id.in_(run_ids))
                .order_by(
                    KeyframeGenerationOutputRecord.is_selected.desc(),
                    KeyframeGenerationOutputRecord.created_at.asc(),
                    KeyframeGenerationOutputRecord.id.asc(),
                )
            ).all()
        )

    def _list_video_outputs(self, run_ids: list[str]) -> list[VideoGenerationOutputRecord]:
        if not run_ids:
            return []
        return list(
            self.session.scalars(
                select(VideoGenerationOutputRecord)
                .where(VideoGenerationOutputRecord.run_id.in_(run_ids))
                .order_by(
                    VideoGenerationOutputRecord.is_selected.desc(),
                    VideoGenerationOutputRecord.created_at.asc(),
                    VideoGenerationOutputRecord.id.asc(),
                )
            ).all()
        )

    def _list_video_inputs(self, task_ids: list[str]) -> list[VideoGenerationTaskInputRecord]:
        if not task_ids:
            return []
        return list(
            self.session.scalars(
                select(VideoGenerationTaskInputRecord)
                .where(VideoGenerationTaskInputRecord.task_id.in_(task_ids))
                .order_by(
                    VideoGenerationTaskInputRecord.sort_order.asc(),
                    VideoGenerationTaskInputRecord.id.asc(),
                )
            ).all()
        )

    def _keyframe_outputs_by_task(
        self,
        outputs: list[KeyframeGenerationOutputRecord],
        runs: list[KeyframeGenerationRunRecord],
    ) -> dict[str, list[KeyframeGenerationOutputRecord]]:
        run_to_task = {run.id: run.keyframe_task_id for run in runs}
        grouped: dict[str, list[KeyframeGenerationOutputRecord]] = {}
        for output in outputs:
            grouped.setdefault(run_to_task[output.run_id], []).append(output)
        return grouped

    def _video_outputs_by_task(
        self,
        outputs: list[VideoGenerationOutputRecord],
        runs: list[VideoGenerationRunRecord],
    ) -> dict[str, list[VideoGenerationOutputRecord]]:
        run_to_task = {run.id: run.video_task_id for run in runs}
        grouped: dict[str, list[VideoGenerationOutputRecord]] = {}
        for output in outputs:
            grouped.setdefault(run_to_task[output.run_id], []).append(output)
        return grouped


def _group_by(records: list[object], attr: str) -> dict[str, list[object]]:
    grouped: dict[str, list[object]] = {}
    for record in records:
        grouped.setdefault(str(getattr(record, attr)), []).append(record)
    return grouped
