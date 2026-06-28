from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.infrastructure.models.character import (
    CharacterLookRecord,
    CharacterRecord,
    CharacterReferenceRecord,
    MediaAssetRecord,
)
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.scene import SceneRecord, SceneReferenceRecord, SceneStateRecord
from app.infrastructure.models.shot import ShotCharacterRecord, ShotRecord, ShotReferenceRecord


@dataclass(frozen=True)
class RecommendationData:
    shot: ShotRecord
    shot_characters: list[ShotCharacterRecord]
    characters: dict[str, CharacterRecord]
    looks: dict[str, CharacterLookRecord]
    character_references: list[CharacterReferenceRecord]
    scene_state: SceneStateRecord | None
    scene_references: list[SceneReferenceRecord]
    bound_references: list[ShotReferenceRecord]


class ShotRecommendationRepository:
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

    def load_recommendation_data(self, shot: ShotRecord) -> RecommendationData:
        shot_characters = list(
            self.session.scalars(
                select(ShotCharacterRecord)
                .where(ShotCharacterRecord.shot_id == shot.id)
                .order_by(
                    ShotCharacterRecord.order_index.asc(),
                    ShotCharacterRecord.created_at.asc(),
                    ShotCharacterRecord.id.asc(),
                )
            ).all()
        )
        character_ids = [character.character_id for character in shot_characters]
        look_ids = [character.look_id for character in shot_characters if character.look_id]
        characters = self._get_characters_by_ids(character_ids)
        looks = self._get_looks_by_ids(look_ids)
        character_references = self._list_character_reference_candidates(
            shot.project_id, character_ids
        )
        scene_state = self._get_scene_state(shot.scene_state_id)
        scene_references = (
            self._list_scene_reference_candidates(shot.project_id, shot.scene_state_id)
            if shot.scene_state_id
            else []
        )
        bound_references = list(
            self.session.scalars(
                select(ShotReferenceRecord)
                .where(ShotReferenceRecord.shot_id == shot.id)
                .order_by(
                    ShotReferenceRecord.reference_type.asc(),
                    ShotReferenceRecord.purpose.asc(),
                    ShotReferenceRecord.created_at.asc(),
                    ShotReferenceRecord.id.asc(),
                )
            ).all()
        )
        return RecommendationData(
            shot=shot,
            shot_characters=shot_characters,
            characters=characters,
            looks=looks,
            character_references=character_references,
            scene_state=scene_state,
            scene_references=scene_references,
            bound_references=bound_references,
        )

    def _get_characters_by_ids(self, ids: list[str]) -> dict[str, CharacterRecord]:
        if not ids:
            return {}
        return {
            record.id: record
            for record in self.session.scalars(
                select(CharacterRecord).where(CharacterRecord.id.in_(ids))
            ).all()
        }

    def _get_looks_by_ids(self, ids: list[str]) -> dict[str, CharacterLookRecord]:
        if not ids:
            return {}
        return {
            record.id: record
            for record in self.session.scalars(
                select(CharacterLookRecord).where(CharacterLookRecord.id.in_(ids))
            ).all()
        }

    def _list_character_reference_candidates(
        self, project_id: str, character_ids: list[str]
    ) -> list[CharacterReferenceRecord]:
        if not character_ids:
            return []
        return list(
            self.session.scalars(
                select(CharacterReferenceRecord)
                .join(CharacterLookRecord)
                .join(CharacterRecord)
                .join(MediaAssetRecord)
                .where(
                    CharacterRecord.project_id == project_id,
                    CharacterRecord.id.in_(character_ids),
                )
                .options(
                    joinedload(CharacterReferenceRecord.media_asset),
                    joinedload(CharacterReferenceRecord.look).joinedload(
                        CharacterLookRecord.character
                    ),
                )
                .order_by(
                    CharacterReferenceRecord.created_at.asc(),
                    CharacterReferenceRecord.id.asc(),
                )
            ).all()
        )

    def _get_scene_state(self, state_id: str | None) -> SceneStateRecord | None:
        if state_id is None:
            return None
        return self.session.get(SceneStateRecord, state_id)

    def _list_scene_reference_candidates(
        self, project_id: str, state_id: str | None
    ) -> list[SceneReferenceRecord]:
        if state_id is None:
            return []
        return list(
            self.session.scalars(
                select(SceneReferenceRecord)
                .join(SceneStateRecord)
                .join(SceneRecord)
                .join(MediaAssetRecord)
                .where(
                    SceneRecord.project_id == project_id,
                    SceneReferenceRecord.state_id == state_id,
                )
                .options(
                    joinedload(SceneReferenceRecord.media_asset),
                    joinedload(SceneReferenceRecord.state),
                )
                .order_by(
                    SceneReferenceRecord.created_at.asc(),
                    SceneReferenceRecord.id.asc(),
                )
            ).all()
        )
