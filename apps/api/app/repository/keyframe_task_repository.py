from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.infrastructure.models.character import (
    CharacterLookRecord,
    CharacterRecord,
    CharacterReferenceRecord,
    MediaAssetRecord,
)
from app.infrastructure.models.keyframe_task import (
    KeyframeGenerationTaskRecord,
    KeyframeGenerationTaskReferenceRecord,
)
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.scene import SceneRecord, SceneReferenceRecord, SceneStateRecord
from app.infrastructure.models.shot import (
    ShotCharacterRecord,
    ShotRecord,
    ShotReferenceRecord,
)


@dataclass(frozen=True)
class KeyframeTaskListData:
    tasks: list[KeyframeGenerationTaskRecord]
    total: int
    references_by_task_id: dict[str, list[KeyframeGenerationTaskReferenceRecord]]


class KeyframeTaskRepository:
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

    def list_tasks(self, project_id: str, shot_id: str) -> KeyframeTaskListData:
        statement = (
            select(KeyframeGenerationTaskRecord)
            .where(
                KeyframeGenerationTaskRecord.project_id == project_id,
                KeyframeGenerationTaskRecord.shot_id == shot_id,
            )
            .order_by(
                KeyframeGenerationTaskRecord.created_at.desc(),
                KeyframeGenerationTaskRecord.id.desc(),
            )
        )
        tasks = list(self.session.scalars(statement).all())
        total = (
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
        references_by_task_id = self.list_references_for_tasks([task.id for task in tasks])
        return KeyframeTaskListData(
            tasks=tasks,
            total=total,
            references_by_task_id=references_by_task_id,
        )

    def get_task(self, project_id: str, task_id: str) -> KeyframeGenerationTaskRecord | None:
        return self.session.scalars(
            select(KeyframeGenerationTaskRecord).where(
                KeyframeGenerationTaskRecord.project_id == project_id,
                KeyframeGenerationTaskRecord.id == task_id,
            )
        ).first()

    def list_references(self, task_id: str) -> list[KeyframeGenerationTaskReferenceRecord]:
        return list(
            self.session.scalars(
                select(KeyframeGenerationTaskReferenceRecord)
                .where(KeyframeGenerationTaskReferenceRecord.task_id == task_id)
                .order_by(
                    KeyframeGenerationTaskReferenceRecord.order_index.asc(),
                    KeyframeGenerationTaskReferenceRecord.created_at.asc(),
                    KeyframeGenerationTaskReferenceRecord.id.asc(),
                )
            ).all()
        )

    def list_references_for_tasks(
        self, task_ids: list[str]
    ) -> dict[str, list[KeyframeGenerationTaskReferenceRecord]]:
        if not task_ids:
            return {}
        rows = list(
            self.session.scalars(
                select(KeyframeGenerationTaskReferenceRecord)
                .where(KeyframeGenerationTaskReferenceRecord.task_id.in_(task_ids))
                .order_by(
                    KeyframeGenerationTaskReferenceRecord.task_id.asc(),
                    KeyframeGenerationTaskReferenceRecord.order_index.asc(),
                    KeyframeGenerationTaskReferenceRecord.created_at.asc(),
                    KeyframeGenerationTaskReferenceRecord.id.asc(),
                )
            ).all()
        )
        grouped: dict[str, list[KeyframeGenerationTaskReferenceRecord]] = {
            task_id: [] for task_id in task_ids
        }
        for row in rows:
            grouped.setdefault(row.task_id, []).append(row)
        return grouped

    def get_reference(
        self, task_id: str, reference_id: str
    ) -> KeyframeGenerationTaskReferenceRecord | None:
        return self.session.scalars(
            select(KeyframeGenerationTaskReferenceRecord).where(
                KeyframeGenerationTaskReferenceRecord.task_id == task_id,
                KeyframeGenerationTaskReferenceRecord.id == reference_id,
            )
        ).first()

    def list_shot_characters(self, shot_id: str) -> list[ShotCharacterRecord]:
        return list(
            self.session.scalars(
                select(ShotCharacterRecord)
                .where(ShotCharacterRecord.shot_id == shot_id)
                .order_by(ShotCharacterRecord.order_index.asc(), ShotCharacterRecord.id.asc())
            ).all()
        )

    def list_shot_references(self, shot_id: str) -> list[ShotReferenceRecord]:
        return list(
            self.session.scalars(
                select(ShotReferenceRecord)
                .where(ShotReferenceRecord.shot_id == shot_id)
                .order_by(ShotReferenceRecord.order_index.asc(), ShotReferenceRecord.id.asc())
            ).all()
        )

    def get_shot_reference(
        self, shot_id: str, shot_reference_id: str
    ) -> ShotReferenceRecord | None:
        return self.session.scalars(
            select(ShotReferenceRecord).where(
                ShotReferenceRecord.shot_id == shot_id,
                ShotReferenceRecord.id == shot_reference_id,
            )
        ).first()

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
                    joinedload(CharacterReferenceRecord.look).joinedload(
                        CharacterLookRecord.character
                    ),
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
                    joinedload(SceneReferenceRecord.state).joinedload(SceneStateRecord.scene),
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

    def create_task(
        self,
        task: KeyframeGenerationTaskRecord,
        references: list[KeyframeGenerationTaskReferenceRecord],
    ) -> KeyframeGenerationTaskRecord:
        try:
            self.session.add(task)
            self.session.add_all(references)
            self.session.commit()
            self.session.refresh(task)
            return task
        except Exception:
            self.session.rollback()
            raise

    def update_task(
        self,
        task: KeyframeGenerationTaskRecord,
        values: dict[str, object],
    ) -> KeyframeGenerationTaskRecord:
        try:
            for key, value in values.items():
                setattr(task, key, value)
            self.session.commit()
            self.session.refresh(task)
            return task
        except Exception:
            self.session.rollback()
            raise

    def delete_task(self, task: KeyframeGenerationTaskRecord) -> None:
        try:
            self.session.delete(task)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def duplicate_task(
        self,
        task: KeyframeGenerationTaskRecord,
        references: list[KeyframeGenerationTaskReferenceRecord],
    ) -> KeyframeGenerationTaskRecord:
        try:
            self.session.add(task)
            self.session.add_all(references)
            self.session.commit()
            self.session.refresh(task)
            return task
        except Exception:
            self.session.rollback()
            raise

    def find_duplicate_reference(
        self,
        task_id: str,
        reference_type: str,
        character_reference_id: str | None,
        scene_reference_id: str | None,
        media_asset_id: str | None,
        purpose: str,
        source_shot_character_id: str | None,
    ) -> KeyframeGenerationTaskReferenceRecord | None:
        statement = select(KeyframeGenerationTaskReferenceRecord).where(
            KeyframeGenerationTaskReferenceRecord.task_id == task_id,
            KeyframeGenerationTaskReferenceRecord.reference_type == reference_type,
            KeyframeGenerationTaskReferenceRecord.purpose == purpose,
        )
        if reference_type == "character":
            statement = statement.where(
                KeyframeGenerationTaskReferenceRecord.character_reference_id
                == character_reference_id,
            )
            if source_shot_character_id is None:
                statement = statement.where(
                    KeyframeGenerationTaskReferenceRecord.source_shot_character_id.is_(None)
                )
            else:
                statement = statement.where(
                    KeyframeGenerationTaskReferenceRecord.source_shot_character_id
                    == source_shot_character_id
                )
        elif reference_type == "scene":
            statement = statement.where(
                KeyframeGenerationTaskReferenceRecord.scene_reference_id == scene_reference_id,
            )
        else:
            statement = statement.where(
                KeyframeGenerationTaskReferenceRecord.media_asset_id == media_asset_id,
            )
        return self.session.scalars(statement).first()

    def create_reference(
        self,
        task: KeyframeGenerationTaskRecord,
        reference: KeyframeGenerationTaskReferenceRecord,
    ) -> KeyframeGenerationTaskReferenceRecord:
        try:
            self.session.add(reference)
            self.session.commit()
            self.session.refresh(reference)
            self.session.refresh(task)
            return reference
        except Exception:
            self.session.rollback()
            raise

    def update_reference(
        self,
        task: KeyframeGenerationTaskRecord,
        reference: KeyframeGenerationTaskReferenceRecord,
        values: dict[str, object],
        order_index: int | None,
    ) -> KeyframeGenerationTaskReferenceRecord:
        try:
            for key, value in values.items():
                setattr(reference, key, value)
            if order_index is not None:
                references = self.list_references(reference.task_id)
                ordered = [item for item in references if item.id != reference.id]
                target_index = max(1, min(order_index, len(references)))
                ordered.insert(target_index - 1, reference)
                self._write_reference_order(ordered)
            self.session.commit()
            self.session.refresh(reference)
            self.session.refresh(task)
            return reference
        except Exception:
            self.session.rollback()
            raise

    def delete_reference(
        self,
        task: KeyframeGenerationTaskRecord,
        reference: KeyframeGenerationTaskReferenceRecord,
    ) -> None:
        try:
            task_id = reference.task_id
            self.session.delete(reference)
            self.session.flush()
            self._compact_reference_order(task_id)
            self.session.commit()
            self.session.refresh(task)
        except Exception:
            self.session.rollback()
            raise

    def _compact_reference_order(self, task_id: str) -> None:
        self._write_reference_order(self.list_references(task_id))

    def _write_reference_order(
        self, references: list[KeyframeGenerationTaskReferenceRecord]
    ) -> None:
        temp_base = max((reference.order_index for reference in references), default=0) + 10000
        for index, reference in enumerate(references, start=1):
            reference.order_index = temp_base + index
        self.session.flush()
        for index, reference in enumerate(references, start=1):
            reference.order_index = index
