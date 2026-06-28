from dataclasses import dataclass

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session, joinedload

from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.scene import (
    SceneRecord,
    SceneReferenceRecord,
    SceneStateRecord,
)


@dataclass(frozen=True)
class SceneListData:
    scenes: list[SceneRecord]
    total: int
    state_counts: dict[str, int]
    reference_counts: dict[str, int]
    default_states: dict[str, SceneStateRecord]
    cover_references: dict[str, SceneReferenceRecord]


class SceneRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def project_exists(self, project_id: str) -> bool:
        return self.session.get(ProjectRecord, project_id) is not None

    def list_scenes(self, project_id: str) -> SceneListData:
        statement = (
            select(SceneRecord)
            .where(SceneRecord.project_id == project_id)
            .order_by(
                SceneRecord.updated_at.desc(),
                SceneRecord.created_at.desc(),
                SceneRecord.id.asc(),
            )
        )
        scenes = list(self.session.scalars(statement).all())
        total = (
            self.session.scalar(
                select(func.count())
                .select_from(SceneRecord)
                .where(SceneRecord.project_id == project_id)
            )
            or 0
        )
        scene_ids = [scene.id for scene in scenes]
        if not scene_ids:
            return SceneListData(scenes, total, {}, {}, {}, {})

        state_counts = dict(
            self.session.execute(
                select(SceneStateRecord.scene_id, func.count(SceneStateRecord.id))
                .where(SceneStateRecord.scene_id.in_(scene_ids))
                .group_by(SceneStateRecord.scene_id)
            ).all()
        )
        reference_counts = dict(
            self.session.execute(
                select(SceneStateRecord.scene_id, func.count(SceneReferenceRecord.id))
                .join(SceneReferenceRecord, SceneReferenceRecord.state_id == SceneStateRecord.id)
                .where(SceneStateRecord.scene_id.in_(scene_ids))
                .group_by(SceneStateRecord.scene_id)
            ).all()
        )
        default_state_records = list(
            self.session.scalars(
                select(SceneStateRecord).where(
                    SceneStateRecord.scene_id.in_(scene_ids),
                    SceneStateRecord.is_default.is_(True),
                )
            ).all()
        )
        default_states = {state.scene_id: state for state in default_state_records}
        cover_records = list(
            self.session.scalars(
                select(SceneReferenceRecord)
                .join(SceneStateRecord, SceneReferenceRecord.state_id == SceneStateRecord.id)
                .where(
                    SceneStateRecord.scene_id.in_(scene_ids),
                    SceneStateRecord.is_default.is_(True),
                    SceneReferenceRecord.is_primary.is_(True),
                )
                .options(joinedload(SceneReferenceRecord.media_asset))
            ).all()
        )
        state_to_scene = {state.id: state.scene_id for state in default_state_records}
        cover_references = {
            state_to_scene[reference.state_id]: reference
            for reference in cover_records
            if reference.state_id in state_to_scene
        }
        return SceneListData(
            scenes=scenes,
            total=total,
            state_counts={key: int(value) for key, value in state_counts.items()},
            reference_counts={key: int(value) for key, value in reference_counts.items()},
            default_states=default_states,
            cover_references=cover_references,
        )

    def get_scene(self, project_id: str, scene_id: str) -> SceneRecord | None:
        statement = (
            select(SceneRecord)
            .where(SceneRecord.project_id == project_id, SceneRecord.id == scene_id)
            .options(joinedload(SceneRecord.states))
        )
        return self.session.scalars(statement).unique().first()

    def create_scene(self, scene: SceneRecord) -> SceneRecord:
        self.session.add(scene)
        self.session.commit()
        self.session.refresh(scene)
        return scene

    def update_scene(self, scene: SceneRecord, values: dict[str, object]) -> SceneRecord:
        for key, value in values.items():
            setattr(scene, key, value)
        self.session.commit()
        self.session.refresh(scene)
        return scene

    def delete_scene_and_media_assets(self, scene: SceneRecord, media_asset_ids: list[str]) -> None:
        try:
            self.session.delete(scene)
            if media_asset_ids:
                self.session.execute(
                    delete(MediaAssetRecord).where(MediaAssetRecord.id.in_(media_asset_ids))
                )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def list_states(self, scene_id: str) -> tuple[list[SceneStateRecord], int]:
        statement = (
            select(SceneStateRecord)
            .where(SceneStateRecord.scene_id == scene_id)
            .order_by(
                SceneStateRecord.is_default.desc(),
                SceneStateRecord.created_at.asc(),
                SceneStateRecord.id.asc(),
            )
        )
        total = (
            self.session.scalar(
                select(func.count())
                .select_from(SceneStateRecord)
                .where(SceneStateRecord.scene_id == scene_id)
            )
            or 0
        )
        return list(self.session.scalars(statement).all()), total

    def get_state(self, scene_id: str, state_id: str) -> SceneStateRecord | None:
        statement = select(SceneStateRecord).where(
            SceneStateRecord.scene_id == scene_id,
            SceneStateRecord.id == state_id,
        )
        return self.session.scalars(statement).first()

    def create_state(self, state: SceneStateRecord) -> SceneStateRecord:
        self.session.add(state)
        self.session.commit()
        self.session.refresh(state)
        return state

    def update_state(self, state: SceneStateRecord, values: dict[str, object]) -> SceneStateRecord:
        for key, value in values.items():
            setattr(state, key, value)
        self.session.commit()
        self.session.refresh(state)
        return state

    def clear_default_states(self, scene_id: str) -> None:
        self.session.execute(
            update(SceneStateRecord)
            .where(SceneStateRecord.scene_id == scene_id)
            .values(is_default=False)
        )

    def delete_state_and_media_assets(
        self,
        state: SceneStateRecord,
        media_asset_ids: list[str],
        next_default_state: SceneStateRecord | None = None,
    ) -> None:
        try:
            self.session.delete(state)
            if next_default_state is not None:
                next_default_state.is_default = True
            if media_asset_ids:
                self.session.execute(
                    delete(MediaAssetRecord).where(MediaAssetRecord.id.in_(media_asset_ids))
                )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def list_references(self, state_id: str) -> tuple[list[SceneReferenceRecord], int]:
        statement = (
            select(SceneReferenceRecord)
            .where(SceneReferenceRecord.state_id == state_id)
            .options(joinedload(SceneReferenceRecord.media_asset))
            .order_by(
                SceneReferenceRecord.is_primary.desc(),
                SceneReferenceRecord.created_at.asc(),
                SceneReferenceRecord.id.asc(),
            )
        )
        total = (
            self.session.scalar(
                select(func.count())
                .select_from(SceneReferenceRecord)
                .where(SceneReferenceRecord.state_id == state_id)
            )
            or 0
        )
        return list(self.session.scalars(statement).all()), total

    def get_reference(self, state_id: str, reference_id: str) -> SceneReferenceRecord | None:
        statement = (
            select(SceneReferenceRecord)
            .where(
                SceneReferenceRecord.state_id == state_id,
                SceneReferenceRecord.id == reference_id,
            )
            .options(joinedload(SceneReferenceRecord.media_asset))
        )
        return self.session.scalars(statement).first()

    def create_reference(
        self,
        media_asset: MediaAssetRecord,
        reference: SceneReferenceRecord,
    ) -> SceneReferenceRecord:
        self.session.add(media_asset)
        self.session.add(reference)
        self.session.commit()
        self.session.refresh(reference)
        return reference

    def update_reference(
        self, reference: SceneReferenceRecord, values: dict[str, object]
    ) -> SceneReferenceRecord:
        for key, value in values.items():
            setattr(reference, key, value)
        self.session.commit()
        self.session.refresh(reference)
        return reference

    def clear_primary_references(self, state_id: str) -> None:
        self.session.execute(
            update(SceneReferenceRecord)
            .where(SceneReferenceRecord.state_id == state_id)
            .values(is_primary=False)
        )

    def delete_reference_and_media_asset(
        self,
        reference: SceneReferenceRecord,
        media_asset_id: str,
        next_primary_reference: SceneReferenceRecord | None = None,
    ) -> None:
        try:
            self.session.delete(reference)
            self.session.execute(
                delete(MediaAssetRecord).where(MediaAssetRecord.id == media_asset_id)
            )
            if next_primary_reference is not None:
                next_primary_reference.is_primary = True
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
