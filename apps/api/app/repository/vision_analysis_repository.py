from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.domain.vision_analysis import VisionAnalysisTargetType, VisionAnalysisTaskStatus
from app.infrastructure.models.character import (
    CharacterLookRecord,
    CharacterRecord,
    CharacterReferenceRecord,
    MediaAssetRecord,
)
from app.infrastructure.models.project import ProjectRecord
from app.infrastructure.models.scene import SceneRecord, SceneReferenceRecord, SceneStateRecord
from app.infrastructure.models.vision_analysis import VisionAnalysisTaskRecord

ACTIVE_STATUSES = (
    VisionAnalysisTaskStatus.PENDING.value,
    VisionAnalysisTaskStatus.RUNNING.value,
)


class VisionAnalysisRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def project_exists(self, project_id: str) -> bool:
        return self.session.get(ProjectRecord, project_id) is not None

    def get_task(self, project_id: str, task_id: str) -> VisionAnalysisTaskRecord | None:
        statement = select(VisionAnalysisTaskRecord).where(
            VisionAnalysisTaskRecord.project_id == project_id,
            VisionAnalysisTaskRecord.id == task_id,
        )
        return self.session.scalars(statement).first()

    def get_latest_character_task(
        self, project_id: str, reference_id: str
    ) -> VisionAnalysisTaskRecord | None:
        statement = (
            select(VisionAnalysisTaskRecord)
            .where(
                VisionAnalysisTaskRecord.project_id == project_id,
                VisionAnalysisTaskRecord.target_type
                == VisionAnalysisTargetType.CHARACTER_REFERENCE.value,
                VisionAnalysisTaskRecord.character_reference_id == reference_id,
            )
            .order_by(
                VisionAnalysisTaskRecord.created_at.desc(),
                VisionAnalysisTaskRecord.id.desc(),
            )
        )
        return self.session.scalars(statement).first()

    def get_latest_scene_task(
        self, project_id: str, reference_id: str
    ) -> VisionAnalysisTaskRecord | None:
        statement = (
            select(VisionAnalysisTaskRecord)
            .where(
                VisionAnalysisTaskRecord.project_id == project_id,
                VisionAnalysisTaskRecord.target_type
                == VisionAnalysisTargetType.SCENE_REFERENCE.value,
                VisionAnalysisTaskRecord.scene_reference_id == reference_id,
            )
            .order_by(
                VisionAnalysisTaskRecord.created_at.desc(),
                VisionAnalysisTaskRecord.id.desc(),
            )
        )
        return self.session.scalars(statement).first()

    def has_active_character_task(self, project_id: str, reference_id: str) -> bool:
        statement = select(VisionAnalysisTaskRecord.id).where(
            VisionAnalysisTaskRecord.project_id == project_id,
            VisionAnalysisTaskRecord.target_type
            == VisionAnalysisTargetType.CHARACTER_REFERENCE.value,
            VisionAnalysisTaskRecord.character_reference_id == reference_id,
            VisionAnalysisTaskRecord.status.in_(ACTIVE_STATUSES),
        )
        return self.session.scalars(statement).first() is not None

    def has_active_scene_task(self, project_id: str, reference_id: str) -> bool:
        statement = select(VisionAnalysisTaskRecord.id).where(
            VisionAnalysisTaskRecord.project_id == project_id,
            VisionAnalysisTaskRecord.target_type == VisionAnalysisTargetType.SCENE_REFERENCE.value,
            VisionAnalysisTaskRecord.scene_reference_id == reference_id,
            VisionAnalysisTaskRecord.status.in_(ACTIVE_STATUSES),
        )
        return self.session.scalars(statement).first() is not None

    def get_character_reference_for_path(
        self,
        project_id: str,
        character_id: str,
        look_id: str,
        reference_id: str,
    ) -> CharacterReferenceRecord | None:
        statement = (
            select(CharacterReferenceRecord)
            .join(CharacterLookRecord, CharacterReferenceRecord.look_id == CharacterLookRecord.id)
            .join(CharacterRecord, CharacterLookRecord.character_id == CharacterRecord.id)
            .where(
                CharacterRecord.project_id == project_id,
                CharacterRecord.id == character_id,
                CharacterLookRecord.id == look_id,
                CharacterReferenceRecord.id == reference_id,
            )
            .options(
                joinedload(CharacterReferenceRecord.media_asset),
                joinedload(CharacterReferenceRecord.look).joinedload(CharacterLookRecord.character),
            )
        )
        return self.session.scalars(statement).first()

    def get_scene_reference_for_path(
        self,
        project_id: str,
        scene_id: str,
        state_id: str,
        reference_id: str,
    ) -> SceneReferenceRecord | None:
        statement = (
            select(SceneReferenceRecord)
            .join(SceneStateRecord, SceneReferenceRecord.state_id == SceneStateRecord.id)
            .join(SceneRecord, SceneStateRecord.scene_id == SceneRecord.id)
            .where(
                SceneRecord.project_id == project_id,
                SceneRecord.id == scene_id,
                SceneStateRecord.id == state_id,
                SceneReferenceRecord.id == reference_id,
            )
            .options(
                joinedload(SceneReferenceRecord.media_asset),
                joinedload(SceneReferenceRecord.state).joinedload(SceneStateRecord.scene),
            )
        )
        return self.session.scalars(statement).first()

    def create_task(self, task: VisionAnalysisTaskRecord) -> VisionAnalysisTaskRecord:
        self.session.add(task)
        self.session.flush()
        return task

    def get_media_asset(self, media_asset_id: str) -> MediaAssetRecord | None:
        return self.session.get(MediaAssetRecord, media_asset_id)
