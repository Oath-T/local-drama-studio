from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.infrastructure.models.character import (
    CharacterLookRecord,
    CharacterRecord,
    CharacterReferenceRecord,
    MediaAssetRecord,
)
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.scene import SceneRecord, SceneReferenceRecord, SceneStateRecord
from app.infrastructure.models.shot import (
    ShotCharacterRecord,
    ShotRecord,
    ShotReferenceRecord,
)


@dataclass(frozen=True)
class ShotListData:
    shots: list[ShotRecord]
    total: int
    character_counts: dict[str, int]
    reference_counts: dict[str, int]
    primary_subject_counts: dict[str, int]
    character_reference_counts: dict[str, int]
    scene_reference_counts: dict[str, int]
    scenes: dict[str, SceneRecord]
    states: dict[str, SceneStateRecord]


class ShotRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def project_exists(self, project_id: str) -> bool:
        return self.session.get(ProjectRecord, project_id) is not None

    def list_shots(self, project_id: str) -> ShotListData:
        statement = (
            select(ShotRecord)
            .where(ShotRecord.project_id == project_id)
            .order_by(
                ShotRecord.order_index.asc(),
                ShotRecord.created_at.asc(),
                ShotRecord.id.asc(),
            )
        )
        shots = list(self.session.scalars(statement).all())
        total = (
            self.session.scalar(
                select(func.count())
                .select_from(ShotRecord)
                .where(ShotRecord.project_id == project_id)
            )
            or 0
        )
        shot_ids = [shot.id for shot in shots]
        if not shot_ids:
            return ShotListData(shots, total, {}, {}, {}, {}, {}, {}, {})

        character_counts = dict(
            self.session.execute(
                select(ShotCharacterRecord.shot_id, func.count(ShotCharacterRecord.id))
                .where(ShotCharacterRecord.shot_id.in_(shot_ids))
                .group_by(ShotCharacterRecord.shot_id)
            ).all()
        )
        reference_counts = dict(
            self.session.execute(
                select(ShotReferenceRecord.shot_id, func.count(ShotReferenceRecord.id))
                .where(ShotReferenceRecord.shot_id.in_(shot_ids))
                .group_by(ShotReferenceRecord.shot_id)
            ).all()
        )
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
        character_reference_counts = dict(
            self.session.execute(
                select(ShotReferenceRecord.shot_id, func.count(ShotReferenceRecord.id))
                .where(
                    ShotReferenceRecord.shot_id.in_(shot_ids),
                    ShotReferenceRecord.reference_type == "character",
                )
                .group_by(ShotReferenceRecord.shot_id)
            ).all()
        )
        scene_reference_counts = dict(
            self.session.execute(
                select(ShotReferenceRecord.shot_id, func.count(ShotReferenceRecord.id))
                .where(
                    ShotReferenceRecord.shot_id.in_(shot_ids),
                    ShotReferenceRecord.reference_type == "scene",
                )
                .group_by(ShotReferenceRecord.shot_id)
            ).all()
        )
        scene_ids = [shot.scene_id for shot in shots if shot.scene_id]
        state_ids = [shot.scene_state_id for shot in shots if shot.scene_state_id]
        scenes = (
            {
                scene.id: scene
                for scene in self.session.scalars(
                    select(SceneRecord).where(SceneRecord.id.in_(scene_ids))
                ).all()
            }
            if scene_ids
            else {}
        )
        states = (
            {
                state.id: state
                for state in self.session.scalars(
                    select(SceneStateRecord).where(SceneStateRecord.id.in_(state_ids))
                ).all()
            }
            if state_ids
            else {}
        )
        return ShotListData(
            shots=shots,
            total=total,
            character_counts={key: int(value) for key, value in character_counts.items()},
            reference_counts={key: int(value) for key, value in reference_counts.items()},
            primary_subject_counts={
                key: int(value) for key, value in primary_subject_counts.items()
            },
            character_reference_counts={
                key: int(value) for key, value in character_reference_counts.items()
            },
            scene_reference_counts={
                key: int(value) for key, value in scene_reference_counts.items()
            },
            scenes=scenes,
            states=states,
        )

    def get_shot(self, project_id: str, shot_id: str) -> ShotRecord | None:
        statement = select(ShotRecord).where(
            ShotRecord.project_id == project_id,
            ShotRecord.id == shot_id,
        )
        return self.session.scalars(statement).first()

    def list_project_shots_for_update(self, project_id: str) -> list[ShotRecord]:
        return list(
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

    def create_shot(self, shot: ShotRecord) -> ShotRecord:
        try:
            self.session.add(shot)
            self.session.commit()
            self.session.refresh(shot)
            return shot
        except Exception:
            self.session.rollback()
            raise

    def update_shot(
        self,
        shot: ShotRecord,
        values: dict[str, object],
        delete_incompatible_scene_references: bool = False,
    ) -> ShotRecord:
        try:
            for key, value in values.items():
                setattr(shot, key, value)
            if delete_incompatible_scene_references:
                self.delete_scene_references_for_shot(shot.id)
            self.session.commit()
            self.session.refresh(shot)
            return shot
        except Exception:
            self.session.rollback()
            raise

    def delete_shot(self, shot: ShotRecord) -> None:
        try:
            project_id = shot.project_id
            self.session.delete(shot)
            self.session.flush()
            self._compact_shot_order(project_id)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def move_shot(self, shot: ShotRecord, order_index: int) -> ShotRecord:
        try:
            shots = self.list_project_shots_for_update(shot.project_id)
            ordered = [item for item in shots if item.id != shot.id]
            target_index = max(1, min(order_index, len(shots)))
            ordered.insert(target_index - 1, shot)
            self._write_shot_order(ordered)
            shot.updated_at = shot.updated_at
            self.session.commit()
            self.session.refresh(shot)
            return shot
        except Exception:
            self.session.rollback()
            raise

    def duplicate_shot(
        self,
        source: ShotRecord,
        duplicate: ShotRecord,
        characters: list[ShotCharacterRecord],
        references: list[ShotReferenceRecord],
    ) -> ShotRecord:
        try:
            shots = self.list_project_shots_for_update(source.project_id)
            for shot in shots:
                if shot.order_index > source.order_index:
                    shot.order_index += 10000
            self.session.flush()
            duplicate.order_index = source.order_index + 1
            self.session.add(duplicate)
            self.session.add_all(characters)
            self.session.flush()
            self.session.add_all(references)
            self.session.flush()
            self._compact_shot_order(source.project_id)
            self.session.commit()
            self.session.refresh(duplicate)
            return duplicate
        except Exception:
            self.session.rollback()
            raise

    def list_characters(self, shot_id: str) -> tuple[list[ShotCharacterRecord], int]:
        statement = (
            select(ShotCharacterRecord)
            .where(ShotCharacterRecord.shot_id == shot_id)
            .order_by(ShotCharacterRecord.order_index.asc(), ShotCharacterRecord.created_at.asc())
        )
        total = (
            self.session.scalar(
                select(func.count())
                .select_from(ShotCharacterRecord)
                .where(ShotCharacterRecord.shot_id == shot_id)
            )
            or 0
        )
        return list(self.session.scalars(statement).all()), total

    def get_shot_character(
        self, shot_id: str, shot_character_id: str
    ) -> ShotCharacterRecord | None:
        return self.session.scalars(
            select(ShotCharacterRecord).where(
                ShotCharacterRecord.shot_id == shot_id,
                ShotCharacterRecord.id == shot_character_id,
            )
        ).first()

    def find_shot_character(self, shot_id: str, character_id: str) -> ShotCharacterRecord | None:
        return self.session.scalars(
            select(ShotCharacterRecord).where(
                ShotCharacterRecord.shot_id == shot_id,
                ShotCharacterRecord.character_id == character_id,
            )
        ).first()

    def create_shot_character(self, record: ShotCharacterRecord) -> ShotCharacterRecord:
        try:
            self.session.add(record)
            self.session.commit()
            self.session.refresh(record)
            return record
        except Exception:
            self.session.rollback()
            raise

    def update_shot_character(
        self, record: ShotCharacterRecord, values: dict[str, object]
    ) -> ShotCharacterRecord:
        try:
            for key, value in values.items():
                setattr(record, key, value)
            self.session.commit()
            self.session.refresh(record)
            return record
        except Exception:
            self.session.rollback()
            raise

    def delete_shot_character(self, record: ShotCharacterRecord) -> None:
        try:
            shot_id = record.shot_id
            self.session.delete(record)
            self.session.flush()
            self._compact_shot_character_order(shot_id)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def move_shot_character(
        self, record: ShotCharacterRecord, order_index: int
    ) -> ShotCharacterRecord:
        try:
            characters, _ = self.list_characters(record.shot_id)
            ordered = [item for item in characters if item.id != record.id]
            target_index = max(1, min(order_index, len(characters)))
            ordered.insert(target_index - 1, record)
            self._write_shot_character_order(ordered)
            self.session.commit()
            self.session.refresh(record)
            return record
        except Exception:
            self.session.rollback()
            raise

    def list_references(self, shot_id: str) -> tuple[list[ShotReferenceRecord], int]:
        statement = (
            select(ShotReferenceRecord)
            .where(ShotReferenceRecord.shot_id == shot_id)
            .order_by(ShotReferenceRecord.order_index.asc(), ShotReferenceRecord.created_at.asc())
        )
        total = (
            self.session.scalar(
                select(func.count())
                .select_from(ShotReferenceRecord)
                .where(ShotReferenceRecord.shot_id == shot_id)
            )
            or 0
        )
        return list(self.session.scalars(statement).all()), total

    def get_shot_reference(
        self, shot_id: str, shot_reference_id: str
    ) -> ShotReferenceRecord | None:
        return self.session.scalars(
            select(ShotReferenceRecord).where(
                ShotReferenceRecord.shot_id == shot_id,
                ShotReferenceRecord.id == shot_reference_id,
            )
        ).first()

    def find_duplicate_reference(
        self,
        shot_id: str,
        reference_type: str,
        character_reference_id: str | None,
        scene_reference_id: str | None,
        media_asset_id: str | None,
        purpose: str,
        shot_character_id: str | None,
    ) -> ShotReferenceRecord | None:
        statement = select(ShotReferenceRecord).where(
            ShotReferenceRecord.shot_id == shot_id,
            ShotReferenceRecord.reference_type == reference_type,
            ShotReferenceRecord.purpose == purpose,
            ShotReferenceRecord.character_reference_id == character_reference_id,
            ShotReferenceRecord.scene_reference_id == scene_reference_id,
            ShotReferenceRecord.media_asset_id == media_asset_id,
        )
        if shot_character_id is None:
            statement = statement.where(ShotReferenceRecord.shot_character_id.is_(None))
        else:
            statement = statement.where(ShotReferenceRecord.shot_character_id == shot_character_id)
        return self.session.scalars(statement).first()

    def create_reference(self, record: ShotReferenceRecord) -> ShotReferenceRecord:
        try:
            self.session.add(record)
            self.session.commit()
            self.session.refresh(record)
            return record
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def update_reference(
        self, record: ShotReferenceRecord, values: dict[str, object]
    ) -> ShotReferenceRecord:
        try:
            for key, value in values.items():
                setattr(record, key, value)
            self.session.commit()
            self.session.refresh(record)
            return record
        except Exception:
            self.session.rollback()
            raise

    def delete_reference(self, record: ShotReferenceRecord) -> None:
        try:
            shot_id = record.shot_id
            self.session.delete(record)
            self.session.flush()
            self._compact_shot_reference_order(shot_id)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def move_reference(self, record: ShotReferenceRecord, order_index: int) -> ShotReferenceRecord:
        try:
            references, _ = self.list_references(record.shot_id)
            ordered = [item for item in references if item.id != record.id]
            target_index = max(1, min(order_index, len(references)))
            ordered.insert(target_index - 1, record)
            self._write_shot_reference_order(ordered)
            self.session.commit()
            self.session.refresh(record)
            return record
        except Exception:
            self.session.rollback()
            raise

    def delete_scene_references_for_shot(self, shot_id: str) -> None:
        for reference in self.session.scalars(
            select(ShotReferenceRecord).where(
                ShotReferenceRecord.shot_id == shot_id,
                ShotReferenceRecord.reference_type == "scene",
            )
        ):
            self.session.delete(reference)

    def get_scene(self, project_id: str, scene_id: str) -> SceneRecord | None:
        return self.session.scalars(
            select(SceneRecord).where(
                SceneRecord.project_id == project_id,
                SceneRecord.id == scene_id,
            )
        ).first()

    def get_state(self, scene_id: str, state_id: str) -> SceneStateRecord | None:
        return self.session.scalars(
            select(SceneStateRecord).where(
                SceneStateRecord.scene_id == scene_id,
                SceneStateRecord.id == state_id,
            )
        ).first()

    def get_character(self, project_id: str, character_id: str) -> CharacterRecord | None:
        return self.session.scalars(
            select(CharacterRecord).where(
                CharacterRecord.project_id == project_id,
                CharacterRecord.id == character_id,
            )
        ).first()

    def get_look(self, character_id: str, look_id: str) -> CharacterLookRecord | None:
        return self.session.scalars(
            select(CharacterLookRecord).where(
                CharacterLookRecord.character_id == character_id,
                CharacterLookRecord.id == look_id,
            )
        ).first()

    def get_character_reference(self, reference_id: str) -> CharacterReferenceRecord | None:
        return self.session.scalars(
            select(CharacterReferenceRecord)
            .where(CharacterReferenceRecord.id == reference_id)
            .options(
                joinedload(CharacterReferenceRecord.media_asset),
                joinedload(CharacterReferenceRecord.look).joinedload(CharacterLookRecord.character),
            )
        ).first()

    def get_scene_reference(self, reference_id: str) -> SceneReferenceRecord | None:
        return self.session.scalars(
            select(SceneReferenceRecord)
            .where(SceneReferenceRecord.id == reference_id)
            .options(
                joinedload(SceneReferenceRecord.media_asset),
                joinedload(SceneReferenceRecord.state).joinedload(SceneStateRecord.scene),
            )
        ).first()

    def get_media_asset(self, media_asset_id: str) -> MediaAssetRecord | None:
        return self.session.get(MediaAssetRecord, media_asset_id)

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

    def get_scene_by_id(self, scene_id: str | None) -> SceneRecord | None:
        if scene_id is None:
            return None
        return self.session.get(SceneRecord, scene_id)

    def get_state_by_id(self, state_id: str | None) -> SceneStateRecord | None:
        if state_id is None:
            return None
        return self.session.get(SceneStateRecord, state_id)

    def _compact_shot_order(self, project_id: str) -> None:
        self._write_shot_order(self.list_project_shots_for_update(project_id))

    def _compact_shot_character_order(self, shot_id: str) -> None:
        characters, _ = self.list_characters(shot_id)
        self._write_shot_character_order(characters)

    def _compact_shot_reference_order(self, shot_id: str) -> None:
        references, _ = self.list_references(shot_id)
        self._write_shot_reference_order(references)

    def _write_shot_order(self, shots: list[ShotRecord]) -> None:
        temp_base = max((shot.order_index for shot in shots), default=0) + 10000
        for index, shot in enumerate(shots, start=1):
            shot.order_index = temp_base + index
        self.session.flush()
        for index, shot in enumerate(shots, start=1):
            shot.order_index = index

    def _write_shot_character_order(self, characters: list[ShotCharacterRecord]) -> None:
        temp_base = max((character.order_index for character in characters), default=0) + 10000
        for index, character in enumerate(characters, start=1):
            character.order_index = temp_base + index
        self.session.flush()
        for index, character in enumerate(characters, start=1):
            character.order_index = index

    def _write_shot_reference_order(self, references: list[ShotReferenceRecord]) -> None:
        temp_base = max((reference.order_index for reference in references), default=0) + 10000
        for index, reference in enumerate(references, start=1):
            reference.order_index = temp_base + index
        self.session.flush()
        for index, reference in enumerate(references, start=1):
            reference.order_index = index
