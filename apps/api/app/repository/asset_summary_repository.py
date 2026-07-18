from dataclasses import dataclass

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session, joinedload

from app.infrastructure.models.character import (
    CharacterLookRecord,
    CharacterRecord,
    CharacterReferenceRecord,
    MediaAssetRecord,
)
from app.infrastructure.models.keyframe_generation import (
    KeyframeGenerationOutputRecord,
    KeyframeGenerationRunRecord,
)
from app.infrastructure.models.keyframe_task import KeyframeGenerationTaskRecord
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.scene import SceneRecord, SceneReferenceRecord, SceneStateRecord
from app.infrastructure.models.shot import (
    ShotCharacterRecord,
    ShotRecord,
    ShotReferenceRecord,
)
from app.infrastructure.models.video_generation import (
    VideoGenerationOutputRecord,
    VideoGenerationRunRecord,
    VideoGenerationTaskRecord,
)


@dataclass(frozen=True)
class CharacterAssetSummaryData:
    character: CharacterRecord
    looks: list[CharacterLookRecord]
    references: list[CharacterReferenceRecord]
    used_shot_count: int
    recent_shots: list[ShotRecord]


@dataclass(frozen=True)
class SceneAssetSummaryData:
    scene: SceneRecord
    states: list[SceneStateRecord]
    references: list[SceneReferenceRecord]
    used_shot_count: int
    recent_shots: list[ShotRecord]


@dataclass(frozen=True)
class ShotAssetSummaryData:
    shot: ShotRecord
    characters: list[ShotCharacterRecord]
    references: list[ShotReferenceRecord]
    scene: SceneRecord | None
    state: SceneStateRecord | None
    keyframe_task_count: int
    video_task_count: int
    selected_keyframe_output_count: int
    selected_video_output_count: int


class AssetSummaryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def project_exists(self, project_id: str) -> bool:
        return self.session.get(ProjectRecord, project_id) is not None

    def get_character_summary(
        self, project_id: str, character_id: str
    ) -> CharacterAssetSummaryData | None:
        character = self.session.scalars(
            select(CharacterRecord).where(
                CharacterRecord.project_id == project_id,
                CharacterRecord.id == character_id,
            )
        ).first()
        if character is None:
            return None

        looks = list(
            self.session.scalars(
                select(CharacterLookRecord)
                .where(CharacterLookRecord.character_id == character_id)
                .order_by(
                    CharacterLookRecord.is_default.desc(),
                    CharacterLookRecord.created_at.asc(),
                    CharacterLookRecord.id.asc(),
                )
            ).all()
        )
        look_ids = [look.id for look in looks]
        references = (
            list(
                self.session.scalars(
                    select(CharacterReferenceRecord)
                    .where(CharacterReferenceRecord.look_id.in_(look_ids))
                    .options(
                        joinedload(CharacterReferenceRecord.media_asset),
                        joinedload(CharacterReferenceRecord.look),
                    )
                    .order_by(
                        CharacterReferenceRecord.is_identity_anchor.desc(),
                        CharacterReferenceRecord.is_primary.desc(),
                        CharacterReferenceRecord.created_at.asc(),
                        CharacterReferenceRecord.id.asc(),
                    )
                ).all()
            )
            if look_ids
            else []
        )
        used_shot_count = int(
            self.session.scalar(
                select(func.count(distinct(ShotCharacterRecord.shot_id)))
                .join(ShotRecord, ShotRecord.id == ShotCharacterRecord.shot_id)
                .where(
                    ShotRecord.project_id == project_id,
                    ShotCharacterRecord.character_id == character_id,
                )
            )
            or 0
        )
        recent_shots = list(
            self.session.scalars(
                select(ShotRecord)
                .join(ShotCharacterRecord, ShotCharacterRecord.shot_id == ShotRecord.id)
                .where(
                    ShotRecord.project_id == project_id,
                    ShotCharacterRecord.character_id == character_id,
                )
                .order_by(
                    ShotRecord.updated_at.desc(),
                    ShotRecord.order_index.asc(),
                    ShotRecord.id.asc(),
                )
                .limit(5)
            ).all()
        )
        return CharacterAssetSummaryData(
            character=character,
            looks=looks,
            references=references,
            used_shot_count=used_shot_count,
            recent_shots=recent_shots,
        )

    def get_scene_summary(self, project_id: str, scene_id: str) -> SceneAssetSummaryData | None:
        scene = self.session.scalars(
            select(SceneRecord).where(
                SceneRecord.project_id == project_id,
                SceneRecord.id == scene_id,
            )
        ).first()
        if scene is None:
            return None

        states = list(
            self.session.scalars(
                select(SceneStateRecord)
                .where(SceneStateRecord.scene_id == scene_id)
                .order_by(
                    SceneStateRecord.is_default.desc(),
                    SceneStateRecord.created_at.asc(),
                    SceneStateRecord.id.asc(),
                )
            ).all()
        )
        state_ids = [state.id for state in states]
        references = (
            list(
                self.session.scalars(
                    select(SceneReferenceRecord)
                    .where(SceneReferenceRecord.state_id.in_(state_ids))
                    .options(
                        joinedload(SceneReferenceRecord.media_asset),
                        joinedload(SceneReferenceRecord.state),
                    )
                    .order_by(
                        SceneReferenceRecord.is_spatial_anchor.desc(),
                        SceneReferenceRecord.is_primary.desc(),
                        SceneReferenceRecord.created_at.asc(),
                        SceneReferenceRecord.id.asc(),
                    )
                ).all()
            )
            if state_ids
            else []
        )
        used_shot_count = int(
            self.session.scalar(
                select(func.count(distinct(ShotRecord.id))).where(
                    ShotRecord.project_id == project_id,
                    ShotRecord.scene_id == scene_id,
                )
            )
            or 0
        )
        recent_shots = list(
            self.session.scalars(
                select(ShotRecord)
                .where(ShotRecord.project_id == project_id, ShotRecord.scene_id == scene_id)
                .order_by(
                    ShotRecord.updated_at.desc(),
                    ShotRecord.order_index.asc(),
                    ShotRecord.id.asc(),
                )
                .limit(5)
            ).all()
        )
        return SceneAssetSummaryData(
            scene=scene,
            states=states,
            references=references,
            used_shot_count=used_shot_count,
            recent_shots=recent_shots,
        )

    def get_shot_summary(self, project_id: str, shot_id: str) -> ShotAssetSummaryData | None:
        shot = self.session.scalars(
            select(ShotRecord).where(ShotRecord.project_id == project_id, ShotRecord.id == shot_id)
        ).first()
        if shot is None:
            return None

        characters = list(
            self.session.scalars(
                select(ShotCharacterRecord)
                .where(ShotCharacterRecord.shot_id == shot_id)
                .order_by(
                    ShotCharacterRecord.order_index.asc(),
                    ShotCharacterRecord.created_at.asc(),
                    ShotCharacterRecord.id.asc(),
                )
            ).all()
        )
        references = list(
            self.session.scalars(
                select(ShotReferenceRecord)
                .where(ShotReferenceRecord.shot_id == shot_id)
                .order_by(
                    ShotReferenceRecord.order_index.asc(),
                    ShotReferenceRecord.created_at.asc(),
                    ShotReferenceRecord.id.asc(),
                )
            ).all()
        )
        scene = self.session.get(SceneRecord, shot.scene_id) if shot.scene_id else None
        state = (
            self.session.get(SceneStateRecord, shot.scene_state_id) if shot.scene_state_id else None
        )
        return ShotAssetSummaryData(
            shot=shot,
            characters=characters,
            references=references,
            scene=scene,
            state=state,
            keyframe_task_count=self._count_keyframe_tasks(project_id, shot_id),
            video_task_count=self._count_video_tasks(project_id, shot_id),
            selected_keyframe_output_count=self._count_selected_keyframe_outputs(
                project_id, shot_id
            ),
            selected_video_output_count=self._count_selected_video_outputs(project_id, shot_id),
        )

    def get_characters_by_ids(self, ids: list[str]) -> dict[str, CharacterRecord]:
        if not ids:
            return {}
        return {
            record.id: record
            for record in self.session.scalars(
                select(CharacterRecord).where(CharacterRecord.id.in_(ids))
            ).all()
        }

    def get_looks_by_ids(self, ids: list[str]) -> dict[str, CharacterLookRecord]:
        if not ids:
            return {}
        return {
            record.id: record
            for record in self.session.scalars(
                select(CharacterLookRecord).where(CharacterLookRecord.id.in_(ids))
            ).all()
        }

    def get_character_references_by_ids(
        self, ids: list[str]
    ) -> dict[str, CharacterReferenceRecord]:
        if not ids:
            return {}
        return {
            record.id: record
            for record in self.session.scalars(
                select(CharacterReferenceRecord)
                .where(CharacterReferenceRecord.id.in_(ids))
                .options(
                    joinedload(CharacterReferenceRecord.media_asset),
                    joinedload(CharacterReferenceRecord.look),
                )
            ).all()
        }

    def get_scene_references_by_ids(self, ids: list[str]) -> dict[str, SceneReferenceRecord]:
        if not ids:
            return {}
        return {
            record.id: record
            for record in self.session.scalars(
                select(SceneReferenceRecord)
                .where(SceneReferenceRecord.id.in_(ids))
                .options(
                    joinedload(SceneReferenceRecord.media_asset),
                    joinedload(SceneReferenceRecord.state),
                )
            ).all()
        }

    def get_media_assets_by_ids(self, ids: list[str]) -> dict[str, MediaAssetRecord]:
        if not ids:
            return {}
        return {
            record.id: record
            for record in self.session.scalars(
                select(MediaAssetRecord).where(MediaAssetRecord.id.in_(ids))
            ).all()
        }

    def _count_keyframe_tasks(self, project_id: str, shot_id: str) -> int:
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(KeyframeGenerationTaskRecord)
                .where(
                    KeyframeGenerationTaskRecord.project_id == project_id,
                    KeyframeGenerationTaskRecord.shot_id == shot_id,
                )
            )
            or 0
        )

    def _count_video_tasks(self, project_id: str, shot_id: str) -> int:
        return int(
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

    def _count_selected_keyframe_outputs(self, project_id: str, shot_id: str) -> int:
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(KeyframeGenerationOutputRecord)
                .join(
                    KeyframeGenerationRunRecord,
                    KeyframeGenerationRunRecord.id == KeyframeGenerationOutputRecord.run_id,
                )
                .join(
                    KeyframeGenerationTaskRecord,
                    KeyframeGenerationTaskRecord.id == KeyframeGenerationRunRecord.keyframe_task_id,
                )
                .where(
                    KeyframeGenerationTaskRecord.project_id == project_id,
                    KeyframeGenerationTaskRecord.shot_id == shot_id,
                    KeyframeGenerationOutputRecord.is_selected.is_(True),
                )
            )
            or 0
        )

    def _count_selected_video_outputs(self, project_id: str, shot_id: str) -> int:
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(VideoGenerationOutputRecord)
                .join(
                    VideoGenerationRunRecord,
                    VideoGenerationRunRecord.id == VideoGenerationOutputRecord.run_id,
                )
                .join(
                    VideoGenerationTaskRecord,
                    VideoGenerationTaskRecord.id == VideoGenerationRunRecord.video_task_id,
                )
                .where(
                    VideoGenerationTaskRecord.project_id == project_id,
                    VideoGenerationTaskRecord.shot_id == shot_id,
                    VideoGenerationOutputRecord.is_selected.is_(True),
                )
            )
            or 0
        )
