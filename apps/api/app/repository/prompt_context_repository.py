from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models.character import (
    CharacterLookRecord,
    CharacterRecord,
    CharacterReferenceRecord,
)
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.scene import SceneRecord, SceneReferenceRecord, SceneStateRecord
from app.infrastructure.models.shot import (
    ShotCharacterRecord,
    ShotRecord,
    ShotReferenceRecord,
)


@dataclass(frozen=True)
class PromptContextCharacterData:
    shot_character: ShotCharacterRecord
    character: CharacterRecord | None
    look: CharacterLookRecord | None


@dataclass(frozen=True)
class PromptContextReferenceData:
    shot_reference: ShotReferenceRecord
    character_reference: CharacterReferenceRecord | None
    scene_reference: SceneReferenceRecord | None


@dataclass(frozen=True)
class PromptContextData:
    shot: ShotRecord
    scene: SceneRecord | None
    state: SceneStateRecord | None
    characters: list[PromptContextCharacterData]
    references: list[PromptContextReferenceData]


class PromptContextRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def project_exists(self, project_id: str) -> bool:
        return self.session.get(ProjectRecord, project_id) is not None

    def get_context(self, project_id: str, shot_id: str) -> PromptContextData | None:
        shot = self.session.scalars(
            select(ShotRecord).where(
                ShotRecord.project_id == project_id,
                ShotRecord.id == shot_id,
            )
        ).first()
        if shot is None:
            return None

        shot_characters = list(
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
        characters_by_id = self._characters_by_id(
            project_id, [item.character_id for item in shot_characters]
        )
        looks_by_id = self._looks_by_id([item.look_id for item in shot_characters if item.look_id])
        context_characters = [
            PromptContextCharacterData(
                shot_character=item,
                character=characters_by_id.get(item.character_id),
                look=looks_by_id.get(item.look_id or ""),
            )
            for item in shot_characters
        ]

        scene = self._scene(project_id, shot.scene_id)
        state = self._state(scene.id, shot.scene_state_id) if scene else None

        shot_references = list(
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
        character_refs_by_id = self._character_references_by_id(
            [item.character_reference_id for item in shot_references if item.character_reference_id]
        )
        scene_refs_by_id = self._scene_references_by_id(
            [item.scene_reference_id for item in shot_references if item.scene_reference_id]
        )
        context_references = [
            PromptContextReferenceData(
                shot_reference=item,
                character_reference=character_refs_by_id.get(item.character_reference_id or ""),
                scene_reference=scene_refs_by_id.get(item.scene_reference_id or ""),
            )
            for item in shot_references
        ]

        return PromptContextData(
            shot=shot,
            scene=scene,
            state=state,
            characters=context_characters,
            references=context_references,
        )

    def _characters_by_id(self, project_id: str, ids: list[str]) -> dict[str, CharacterRecord]:
        if not ids:
            return {}
        return {
            record.id: record
            for record in self.session.scalars(
                select(CharacterRecord).where(
                    CharacterRecord.project_id == project_id,
                    CharacterRecord.id.in_(ids),
                )
            ).all()
        }

    def _looks_by_id(self, ids: list[str]) -> dict[str, CharacterLookRecord]:
        if not ids:
            return {}
        return {
            record.id: record
            for record in self.session.scalars(
                select(CharacterLookRecord).where(CharacterLookRecord.id.in_(ids))
            ).all()
        }

    def _scene(self, project_id: str, scene_id: str | None) -> SceneRecord | None:
        if scene_id is None:
            return None
        return self.session.scalars(
            select(SceneRecord).where(
                SceneRecord.project_id == project_id,
                SceneRecord.id == scene_id,
            )
        ).first()

    def _state(self, scene_id: str, state_id: str | None) -> SceneStateRecord | None:
        if state_id is None:
            return None
        return self.session.scalars(
            select(SceneStateRecord).where(
                SceneStateRecord.scene_id == scene_id,
                SceneStateRecord.id == state_id,
            )
        ).first()

    def _character_references_by_id(self, ids: list[str]) -> dict[str, CharacterReferenceRecord]:
        if not ids:
            return {}
        return {
            record.id: record
            for record in self.session.scalars(
                select(CharacterReferenceRecord).where(CharacterReferenceRecord.id.in_(ids))
            ).all()
        }

    def _scene_references_by_id(self, ids: list[str]) -> dict[str, SceneReferenceRecord]:
        if not ids:
            return {}
        return {
            record.id: record
            for record in self.session.scalars(
                select(SceneReferenceRecord).where(SceneReferenceRecord.id.in_(ids))
            ).all()
        }
