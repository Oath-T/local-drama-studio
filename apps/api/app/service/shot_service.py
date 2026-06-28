import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError

from app.api.schemas.character import CharacterReferenceResponse, MediaAssetResponse
from app.api.schemas.scene import SceneReferenceResponse
from app.api.schemas.shot import (
    ShotCharacterCreateRequest,
    ShotCharacterListResponse,
    ShotCharacterResponse,
    ShotCharacterUpdateRequest,
    ShotCreateRequest,
    ShotListResponse,
    ShotMoveRequest,
    ShotReferenceCreateRequest,
    ShotReferenceListResponse,
    ShotReferenceMoveRequest,
    ShotReferenceResponse,
    ShotReferenceUpdateRequest,
    ShotResponse,
    ShotSceneStateSummary,
    ShotSceneSummary,
    ShotUpdateRequest,
)
from app.core.errors import AppError
from app.domain.character import (
    AnalysisStatus as CharacterAnalysisStatus,
)
from app.domain.character import (
    Expression,
    PoseType,
    ViewAngle,
)
from app.domain.character import (
    ShotType as CharacterShotType,
)
from app.domain.character import (
    SuggestionReviewStatus as CharacterSuggestionReviewStatus,
)
from app.domain.scene import (
    AnalysisStatus as SceneAnalysisStatus,
)
from app.domain.scene import (
    CameraPosition,
    CompositionType,
    ViewDirection,
)
from app.domain.scene import (
    ShotScale as SceneShotScale,
)
from app.domain.scene import (
    SuggestionReviewStatus as SceneSuggestionReviewStatus,
)
from app.domain.shot import (
    CameraAngle,
    CameraHeight,
    CameraMovement,
    CharacterReferencePurpose,
    MissingItem,
    ReadinessStatus,
    SceneReferencePurpose,
    ShotCompositionType,
    ShotErrorCode,
    ShotReferenceType,
    ShotScale,
    normalize_optional_text,
    normalize_required_text,
)
from app.infrastructure.models.character import CharacterReferenceRecord, MediaAssetRecord
from app.infrastructure.models.scene import SceneReferenceRecord
from app.infrastructure.models.shot import (
    ShotCharacterRecord,
    ShotRecord,
    ShotReferenceRecord,
)
from app.repository.shot_repository import ShotListData, ShotRepository

ERROR_MESSAGES: dict[ShotErrorCode, str] = {
    ShotErrorCode.PROJECT_NOT_FOUND: "项目不存在或已被删除。",
    ShotErrorCode.SHOT_NOT_FOUND: "镜头不存在或已被删除。",
    ShotErrorCode.SHOT_CHARACTER_NOT_FOUND: "镜头角色不存在或已被删除。",
    ShotErrorCode.SHOT_REFERENCE_NOT_FOUND: "镜头参考图绑定不存在或已被删除。",
    ShotErrorCode.SCENE_NOT_FOUND: "场景不存在或已被删除。",
    ShotErrorCode.SCENE_STATE_NOT_FOUND: "场景状态不存在或已被删除。",
    ShotErrorCode.CHARACTER_NOT_FOUND: "角色不存在或已被删除。",
    ShotErrorCode.LOOK_NOT_FOUND: "造型不存在或已被删除。",
    ShotErrorCode.CHARACTER_REFERENCE_NOT_FOUND: "角色参考图不存在或已被删除。",
    ShotErrorCode.SCENE_REFERENCE_NOT_FOUND: "场景参考图不存在或已被删除。",
    ShotErrorCode.NAME_REQUIRED: "请输入镜头名称。",
    ShotErrorCode.NAME_TOO_LONG: "镜头名称不能超过 120 个字符。",
    ShotErrorCode.CUSTOM_CAMERA_HEIGHT_REQUIRED: "选择自定义机位高度时，请填写说明。",
    ShotErrorCode.CUSTOM_CAMERA_ANGLE_REQUIRED: "选择自定义拍摄角度时，请填写说明。",
    ShotErrorCode.CUSTOM_COMPOSITION_REQUIRED: "选择自定义构图时，请填写说明。",
    ShotErrorCode.CUSTOM_CAMERA_MOVEMENT_REQUIRED: "选择自定义镜头运动时，请填写说明。",
    ShotErrorCode.SCENE_STATE_REQUIRES_SCENE: "选择场景状态前，请先选择场景。",
    ShotErrorCode.SCENE_STATE_MISMATCH: "场景状态不属于当前场景。",
    ShotErrorCode.CHARACTER_ALREADY_IN_SHOT: "该角色已经添加到当前镜头。",
    ShotErrorCode.LOOK_CHARACTER_MISMATCH: "造型不属于该角色。",
    ShotErrorCode.INVALID_REFERENCE_TYPE: "参考图类型无效。",
    ShotErrorCode.INVALID_REFERENCE_PURPOSE: "参考图用途无效。",
    ShotErrorCode.REFERENCE_REQUIRES_SCENE_STATE: "绑定场景参考图前，请先选择场景状态。",
    ShotErrorCode.REFERENCE_SCENE_STATE_MISMATCH: "场景参考图不属于当前镜头的场景状态。",
    ShotErrorCode.REFERENCE_CHARACTER_MISMATCH: "角色参考图与镜头角色不匹配。",
    ShotErrorCode.REFERENCE_ALREADY_BOUND: "相同用途的参考图已经绑定。",
    ShotErrorCode.INVALID_ORDER_INDEX: "排序位置无效。",
    ShotErrorCode.DATABASE_CONFLICT: "数据已被其他操作更新，请刷新后重试。",
}

HTTP_422 = 422


class ShotService:
    def __init__(self, repository: ShotRepository) -> None:
        self.repository = repository

    def list_shots(self, project_id: UUID) -> ShotListResponse:
        self._ensure_project(project_id)
        data = self.repository.list_shots(str(project_id))
        return ShotListResponse(
            items=[self._shot_response_from_list(shot, data) for shot in data.shots],
            total=data.total,
        )

    def create_shot(self, project_id: UUID, payload: ShotCreateRequest) -> ShotResponse:
        self._ensure_project(project_id)
        scene_id, scene_state_id = self._validate_scene_binding(
            str(project_id), payload.scene_id, payload.scene_state_id
        )
        now = utc_now()
        data = self.repository.list_shots(str(project_id))
        shot = ShotRecord(
            id=str(uuid4()),
            project_id=str(project_id),
            name=self._normalize_name(payload.name),
            order_index=data.total + 1,
            story_description=self._optional(payload.story_description, 3000),
            visual_description=self._optional(payload.visual_description, 3000),
            dialogue=self._optional(payload.dialogue, 3000),
            action_summary=self._optional(payload.action_summary, 2000),
            duration_seconds=payload.duration_seconds,
            shot_scale=payload.shot_scale.value,
            camera_height=payload.camera_height.value,
            custom_camera_height=self._normalize_custom(
                payload.camera_height,
                payload.custom_camera_height,
                CameraHeight.CUSTOM,
                ShotErrorCode.CUSTOM_CAMERA_HEIGHT_REQUIRED,
            ),
            camera_angle=payload.camera_angle.value,
            custom_camera_angle=self._normalize_custom(
                payload.camera_angle,
                payload.custom_camera_angle,
                CameraAngle.CUSTOM,
                ShotErrorCode.CUSTOM_CAMERA_ANGLE_REQUIRED,
            ),
            composition_type=payload.composition_type.value,
            custom_composition=self._normalize_custom(
                payload.composition_type,
                payload.custom_composition,
                ShotCompositionType.CUSTOM,
                ShotErrorCode.CUSTOM_COMPOSITION_REQUIRED,
            ),
            camera_movement=payload.camera_movement.value,
            custom_camera_movement=self._normalize_custom(
                payload.camera_movement,
                payload.custom_camera_movement,
                CameraMovement.CUSTOM,
                ShotErrorCode.CUSTOM_CAMERA_MOVEMENT_REQUIRED,
            ),
            focal_subject=self._optional(payload.focal_subject, 200),
            mood_description=self._optional(payload.mood_description, 1000),
            scene_id=scene_id,
            scene_state_id=scene_state_id,
            notes=self._optional(payload.notes, 2000),
            created_at=now,
            updated_at=now,
        )
        created = self.repository.create_shot(shot)
        return self._shot_response(created, include_children=True)

    def get_shot(self, project_id: UUID, shot_id: UUID) -> ShotResponse:
        shot = self._get_shot(project_id, shot_id)
        return self._shot_response(shot, include_children=True)

    def update_shot(
        self, project_id: UUID, shot_id: UUID, payload: ShotUpdateRequest
    ) -> ShotResponse:
        shot = self._get_shot(project_id, shot_id)
        submitted = payload.model_dump(exclude_unset=True)
        values: dict[str, object] = {}
        if "name" in submitted:
            values["name"] = self._normalize_name(submitted["name"])
        for key, max_length in {
            "story_description": 3000,
            "visual_description": 3000,
            "dialogue": 3000,
            "action_summary": 2000,
            "focal_subject": 200,
            "mood_description": 1000,
            "notes": 2000,
        }.items():
            if key in submitted:
                values[key] = self._optional(submitted[key], max_length)
        if "duration_seconds" in submitted:
            values["duration_seconds"] = submitted["duration_seconds"]
        if "shot_scale" in submitted and submitted["shot_scale"] is not None:
            values["shot_scale"] = submitted["shot_scale"].value

        self._apply_custom_update(
            values,
            submitted,
            "camera_height",
            "custom_camera_height",
            CameraHeight,
            CameraHeight.CUSTOM,
            shot.camera_height,
            shot.custom_camera_height,
            ShotErrorCode.CUSTOM_CAMERA_HEIGHT_REQUIRED,
        )
        self._apply_custom_update(
            values,
            submitted,
            "camera_angle",
            "custom_camera_angle",
            CameraAngle,
            CameraAngle.CUSTOM,
            shot.camera_angle,
            shot.custom_camera_angle,
            ShotErrorCode.CUSTOM_CAMERA_ANGLE_REQUIRED,
        )
        self._apply_custom_update(
            values,
            submitted,
            "composition_type",
            "custom_composition",
            ShotCompositionType,
            ShotCompositionType.CUSTOM,
            shot.composition_type,
            shot.custom_composition,
            ShotErrorCode.CUSTOM_COMPOSITION_REQUIRED,
        )
        self._apply_custom_update(
            values,
            submitted,
            "camera_movement",
            "custom_camera_movement",
            CameraMovement,
            CameraMovement.CUSTOM,
            shot.camera_movement,
            shot.custom_camera_movement,
            ShotErrorCode.CUSTOM_CAMERA_MOVEMENT_REQUIRED,
        )

        scene_changed = "scene_id" in submitted
        state_changed = "scene_state_id" in submitted
        next_scene_id = submitted.get("scene_id", shot.scene_id)
        next_state_id = submitted.get("scene_state_id", shot.scene_state_id)
        if scene_changed and next_scene_id is None:
            next_state_id = None
        if scene_changed and next_scene_id != shot.scene_id and not state_changed:
            if (
                next_state_id
                and self.repository.get_state(str(next_scene_id), str(next_state_id)) is None
            ):
                next_state_id = None
        if scene_changed or state_changed:
            validated_scene_id, validated_state_id = self._validate_scene_binding(
                str(project_id), next_scene_id, next_state_id
            )
            values["scene_id"] = validated_scene_id
            values["scene_state_id"] = validated_state_id

        values["updated_at"] = utc_now()
        delete_scene_refs = (
            "scene_state_id" in values and values["scene_state_id"] != shot.scene_state_id
        ) or ("scene_id" in values and values["scene_id"] != shot.scene_id)
        updated = self.repository.update_shot(
            shot, values, delete_incompatible_scene_references=delete_scene_refs
        )
        return self._shot_response(updated, include_children=True)

    def delete_shot(self, project_id: UUID, shot_id: UUID) -> None:
        shot = self._get_shot(project_id, shot_id)
        self.repository.delete_shot(shot)

    def move_shot(self, project_id: UUID, shot_id: UUID, payload: ShotMoveRequest) -> ShotResponse:
        shot = self._get_shot(project_id, shot_id)
        moved = self.repository.move_shot(shot, payload.order_index)
        return self._shot_response(moved, include_children=True)

    def duplicate_shot(self, project_id: UUID, shot_id: UUID) -> ShotResponse:
        source = self._get_shot(project_id, shot_id)
        now = utc_now()
        duplicate = ShotRecord(
            id=str(uuid4()),
            project_id=source.project_id,
            name=f"{source.name} - 副本",
            order_index=source.order_index + 1,
            story_description=source.story_description,
            visual_description=source.visual_description,
            dialogue=source.dialogue,
            action_summary=source.action_summary,
            duration_seconds=source.duration_seconds,
            shot_scale=source.shot_scale,
            camera_height=source.camera_height,
            custom_camera_height=source.custom_camera_height,
            camera_angle=source.camera_angle,
            custom_camera_angle=source.custom_camera_angle,
            composition_type=source.composition_type,
            custom_composition=source.custom_composition,
            camera_movement=source.camera_movement,
            custom_camera_movement=source.custom_camera_movement,
            focal_subject=source.focal_subject,
            mood_description=source.mood_description,
            scene_id=source.scene_id,
            scene_state_id=source.scene_state_id,
            notes=source.notes,
            created_at=now,
            updated_at=now,
        )
        source_characters, _ = self.repository.list_characters(source.id)
        character_id_map: dict[str, str] = {}
        duplicates: list[ShotCharacterRecord] = []
        for source_character in source_characters:
            new_id = str(uuid4())
            character_id_map[source_character.id] = new_id
            duplicates.append(
                ShotCharacterRecord(
                    id=new_id,
                    shot_id=duplicate.id,
                    character_id=source_character.character_id,
                    look_id=source_character.look_id,
                    action_description=source_character.action_description,
                    expression_description=source_character.expression_description,
                    position_description=source_character.position_description,
                    is_primary_subject=source_character.is_primary_subject,
                    order_index=source_character.order_index,
                    notes=source_character.notes,
                    created_at=now,
                    updated_at=now,
                )
            )
        source_references, _ = self.repository.list_references(source.id)
        reference_duplicates = [
            ShotReferenceRecord(
                id=str(uuid4()),
                shot_id=duplicate.id,
                reference_type=reference.reference_type,
                character_reference_id=reference.character_reference_id,
                scene_reference_id=reference.scene_reference_id,
                shot_character_id=(
                    character_id_map.get(reference.shot_character_id)
                    if reference.shot_character_id
                    else None
                ),
                purpose=reference.purpose,
                order_index=reference.order_index,
                notes=reference.notes,
                created_at=now,
                updated_at=now,
            )
            for reference in source_references
        ]
        try:
            created = self.repository.duplicate_shot(
                source, duplicate, duplicates, reference_duplicates
            )
        except SQLAlchemyError:
            raise_shot_error(ShotErrorCode.DATABASE_CONFLICT, status.HTTP_409_CONFLICT)
        return self._shot_response(created, include_children=True)

    def list_characters(self, project_id: UUID, shot_id: UUID) -> ShotCharacterListResponse:
        shot = self._get_shot(project_id, shot_id)
        characters, total = self.repository.list_characters(shot.id)
        return ShotCharacterListResponse(
            items=[self._shot_character_response(character) for character in characters],
            total=total,
        )

    def add_character(
        self, project_id: UUID, shot_id: UUID, payload: ShotCharacterCreateRequest
    ) -> ShotCharacterResponse:
        shot = self._get_shot(project_id, shot_id)
        character = self.repository.get_character(str(project_id), payload.character_id)
        if character is None:
            raise_shot_error(ShotErrorCode.CHARACTER_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        if self.repository.find_shot_character(shot.id, payload.character_id) is not None:
            raise_shot_error(ShotErrorCode.CHARACTER_ALREADY_IN_SHOT, status.HTTP_409_CONFLICT)
        look_id = self._validate_look(payload.character_id, payload.look_id)
        characters, total = self.repository.list_characters(shot.id)
        now = utc_now()
        record = ShotCharacterRecord(
            id=str(uuid4()),
            shot_id=shot.id,
            character_id=payload.character_id,
            look_id=look_id,
            action_description=self._optional(payload.action_description, 2000),
            expression_description=self._optional(payload.expression_description, 1000),
            position_description=self._optional(payload.position_description, 1000),
            is_primary_subject=payload.is_primary_subject,
            order_index=total + 1,
            notes=self._optional(payload.notes, 1000),
            created_at=now,
            updated_at=now,
        )
        try:
            created = self.repository.create_shot_character(record)
        except SQLAlchemyError:
            raise_shot_error(ShotErrorCode.DATABASE_CONFLICT, status.HTTP_409_CONFLICT)
        shot.updated_at = now
        return self._shot_character_response(created)

    def update_character(
        self,
        project_id: UUID,
        shot_id: UUID,
        shot_character_id: UUID,
        payload: ShotCharacterUpdateRequest,
    ) -> ShotCharacterResponse:
        shot = self._get_shot(project_id, shot_id)
        record = self._get_shot_character(shot.id, shot_character_id)
        submitted = payload.model_dump(exclude_unset=True)
        values: dict[str, object] = {}
        if "look_id" in submitted:
            values["look_id"] = self._validate_look(record.character_id, submitted["look_id"])
        for key, max_length in {
            "action_description": 2000,
            "expression_description": 1000,
            "position_description": 1000,
            "notes": 1000,
        }.items():
            if key in submitted:
                values[key] = self._optional(submitted[key], max_length)
        if "is_primary_subject" in submitted:
            values["is_primary_subject"] = bool(submitted["is_primary_subject"])
        values["updated_at"] = utc_now()
        updated = self.repository.update_shot_character(record, values)
        shot.updated_at = values["updated_at"]
        return self._shot_character_response(updated)

    def delete_character(self, project_id: UUID, shot_id: UUID, shot_character_id: UUID) -> None:
        shot = self._get_shot(project_id, shot_id)
        record = self._get_shot_character(shot.id, shot_character_id)
        self.repository.delete_shot_character(record)

    def move_character(
        self,
        project_id: UUID,
        shot_id: UUID,
        shot_character_id: UUID,
        payload: ShotMoveRequest,
    ) -> ShotCharacterResponse:
        shot = self._get_shot(project_id, shot_id)
        record = self._get_shot_character(shot.id, shot_character_id)
        moved = self.repository.move_shot_character(record, payload.order_index)
        return self._shot_character_response(moved)

    def list_references(self, project_id: UUID, shot_id: UUID) -> ShotReferenceListResponse:
        shot = self._get_shot(project_id, shot_id)
        references, total = self.repository.list_references(shot.id)
        return ShotReferenceListResponse(
            items=[self._shot_reference_response(reference) for reference in references],
            total=total,
        )

    def add_reference(
        self, project_id: UUID, shot_id: UUID, payload: ShotReferenceCreateRequest
    ) -> ShotReferenceResponse:
        shot = self._get_shot(project_id, shot_id)
        reference_type = payload.reference_type
        purpose = self._validate_purpose(reference_type, payload.purpose)
        character_reference_id: str | None = None
        scene_reference_id: str | None = None
        shot_character_id: str | None = None
        if reference_type == ShotReferenceType.CHARACTER:
            character_reference_id, shot_character_id = self._validate_character_reference(
                shot, payload.character_reference_id, payload.shot_character_id
            )
        elif reference_type == ShotReferenceType.SCENE:
            scene_reference_id = self._validate_scene_reference(shot, payload.scene_reference_id)
        else:
            raise_shot_error(ShotErrorCode.INVALID_REFERENCE_TYPE, HTTP_422)

        duplicate = self.repository.find_duplicate_reference(
            shot.id,
            reference_type.value,
            character_reference_id,
            scene_reference_id,
            purpose,
            shot_character_id,
        )
        if duplicate is not None:
            raise_shot_error(ShotErrorCode.REFERENCE_ALREADY_BOUND, status.HTTP_409_CONFLICT)
        references, total = self.repository.list_references(shot.id)
        now = utc_now()
        record = ShotReferenceRecord(
            id=str(uuid4()),
            shot_id=shot.id,
            reference_type=reference_type.value,
            character_reference_id=character_reference_id,
            scene_reference_id=scene_reference_id,
            shot_character_id=shot_character_id,
            purpose=purpose,
            order_index=total + 1,
            notes=self._optional(payload.notes, 1000),
            created_at=now,
            updated_at=now,
        )
        try:
            created = self.repository.create_reference(record)
        except SQLAlchemyError:
            raise_shot_error(ShotErrorCode.DATABASE_CONFLICT, status.HTTP_409_CONFLICT)
        return self._shot_reference_response(created)

    def update_reference(
        self,
        project_id: UUID,
        shot_id: UUID,
        shot_reference_id: UUID,
        payload: ShotReferenceUpdateRequest,
    ) -> ShotReferenceResponse:
        shot = self._get_shot(project_id, shot_id)
        record = self._get_shot_reference(shot.id, shot_reference_id)
        submitted = payload.model_dump(exclude_unset=True)
        values: dict[str, object] = {}
        next_purpose = record.purpose
        if "purpose" in submitted and submitted["purpose"] is not None:
            next_purpose = self._validate_purpose(
                ShotReferenceType(record.reference_type), submitted["purpose"]
            )
            values["purpose"] = next_purpose
        if "notes" in submitted:
            values["notes"] = self._optional(submitted["notes"], 1000)
        duplicate = self.repository.find_duplicate_reference(
            shot.id,
            record.reference_type,
            record.character_reference_id,
            record.scene_reference_id,
            next_purpose,
            record.shot_character_id,
        )
        if duplicate is not None and duplicate.id != record.id:
            raise_shot_error(ShotErrorCode.REFERENCE_ALREADY_BOUND, status.HTTP_409_CONFLICT)
        values["updated_at"] = utc_now()
        try:
            updated = self.repository.update_reference(record, values)
        except SQLAlchemyError:
            raise_shot_error(ShotErrorCode.DATABASE_CONFLICT, status.HTTP_409_CONFLICT)
        return self._shot_reference_response(updated)

    def delete_reference(self, project_id: UUID, shot_id: UUID, shot_reference_id: UUID) -> None:
        shot = self._get_shot(project_id, shot_id)
        record = self._get_shot_reference(shot.id, shot_reference_id)
        self.repository.delete_reference(record)

    def move_reference(
        self,
        project_id: UUID,
        shot_id: UUID,
        shot_reference_id: UUID,
        payload: ShotReferenceMoveRequest,
    ) -> ShotReferenceResponse:
        shot = self._get_shot(project_id, shot_id)
        record = self._get_shot_reference(shot.id, shot_reference_id)
        moved = self.repository.move_reference(record, payload.order_index)
        return self._shot_reference_response(moved)

    def _ensure_project(self, project_id: UUID) -> None:
        if not self.repository.project_exists(str(project_id)):
            raise_shot_error(ShotErrorCode.PROJECT_NOT_FOUND, status.HTTP_404_NOT_FOUND)

    def _get_shot(self, project_id: UUID, shot_id: UUID) -> ShotRecord:
        shot = self.repository.get_shot(str(project_id), str(shot_id))
        if shot is None:
            raise_shot_error(ShotErrorCode.SHOT_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        return shot

    def _get_shot_character(self, shot_id: str, shot_character_id: UUID) -> ShotCharacterRecord:
        record = self.repository.get_shot_character(shot_id, str(shot_character_id))
        if record is None:
            raise_shot_error(ShotErrorCode.SHOT_CHARACTER_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        return record

    def _get_shot_reference(self, shot_id: str, shot_reference_id: UUID) -> ShotReferenceRecord:
        record = self.repository.get_shot_reference(shot_id, str(shot_reference_id))
        if record is None:
            raise_shot_error(ShotErrorCode.SHOT_REFERENCE_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        return record

    def _validate_scene_binding(
        self, project_id: str, scene_id: object, scene_state_id: object
    ) -> tuple[str | None, str | None]:
        normalized_scene_id = str(scene_id) if scene_id else None
        normalized_state_id = str(scene_state_id) if scene_state_id else None
        if normalized_state_id and not normalized_scene_id:
            raise_shot_error(ShotErrorCode.SCENE_STATE_REQUIRES_SCENE, HTTP_422)
        if normalized_scene_id:
            scene = self.repository.get_scene(project_id, normalized_scene_id)
            if scene is None:
                raise_shot_error(ShotErrorCode.SCENE_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        if normalized_state_id:
            state = self.repository.get_state(str(normalized_scene_id), normalized_state_id)
            if state is None:
                raise_shot_error(ShotErrorCode.SCENE_STATE_MISMATCH, HTTP_422)
        return normalized_scene_id, normalized_state_id

    def _validate_look(self, character_id: str, look_id: object) -> str | None:
        if look_id is None:
            return None
        look = self.repository.get_look(character_id, str(look_id))
        if look is None:
            raise_shot_error(ShotErrorCode.LOOK_CHARACTER_MISMATCH, HTTP_422)
        return look.id

    def _validate_character_reference(
        self,
        shot: ShotRecord,
        reference_id: str | None,
        shot_character_id: str | None,
    ) -> tuple[str, str | None]:
        if reference_id is None:
            raise_shot_error(ShotErrorCode.CHARACTER_REFERENCE_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        reference = self.repository.get_character_reference(reference_id)
        if reference is None or reference.look.character.project_id != shot.project_id:
            raise_shot_error(ShotErrorCode.CHARACTER_REFERENCE_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        if shot_character_id is None:
            return reference.id, None
        shot_character = self.repository.get_shot_character(shot.id, shot_character_id)
        if shot_character is None:
            raise_shot_error(ShotErrorCode.SHOT_CHARACTER_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        if shot_character.character_id != reference.look.character_id:
            raise_shot_error(ShotErrorCode.REFERENCE_CHARACTER_MISMATCH, HTTP_422)
        return reference.id, shot_character.id

    def _validate_scene_reference(self, shot: ShotRecord, reference_id: str | None) -> str:
        if shot.scene_state_id is None:
            raise_shot_error(ShotErrorCode.REFERENCE_REQUIRES_SCENE_STATE, HTTP_422)
        if reference_id is None:
            raise_shot_error(ShotErrorCode.SCENE_REFERENCE_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        reference = self.repository.get_scene_reference(reference_id)
        if reference is None or reference.state.scene.project_id != shot.project_id:
            raise_shot_error(ShotErrorCode.SCENE_REFERENCE_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        if reference.state_id != shot.scene_state_id:
            raise_shot_error(ShotErrorCode.REFERENCE_SCENE_STATE_MISMATCH, HTTP_422)
        return reference.id

    @staticmethod
    def _validate_purpose(
        reference_type: ShotReferenceType,
        purpose: CharacterReferencePurpose | SceneReferencePurpose,
    ) -> str:
        if reference_type == ShotReferenceType.CHARACTER:
            try:
                return CharacterReferencePurpose(str(purpose)).value
            except ValueError:
                raise_shot_error(ShotErrorCode.INVALID_REFERENCE_PURPOSE, HTTP_422)
        if reference_type == ShotReferenceType.SCENE:
            try:
                return SceneReferencePurpose(str(purpose)).value
            except ValueError:
                raise_shot_error(ShotErrorCode.INVALID_REFERENCE_PURPOSE, HTTP_422)
        raise_shot_error(ShotErrorCode.INVALID_REFERENCE_TYPE, HTTP_422)

    def _shot_response_from_list(self, shot: ShotRecord, data: ShotListData) -> ShotResponse:
        readiness, missing = self._calculate_readiness(
            shot,
            character_count=data.character_counts.get(shot.id, 0),
            primary_subject_count=data.primary_subject_counts.get(shot.id, 0),
            character_reference_count=data.character_reference_counts.get(shot.id, 0),
            scene_reference_count=data.scene_reference_counts.get(shot.id, 0),
        )
        return self._shot_response(
            shot,
            include_children=False,
            readiness_status=readiness,
            missing_items=missing,
            character_count=data.character_counts.get(shot.id, 0),
            reference_count=data.reference_counts.get(shot.id, 0),
            scene=data.scenes.get(shot.scene_id or ""),
            state=data.states.get(shot.scene_state_id or ""),
        )

    def _shot_response(
        self,
        shot: ShotRecord,
        include_children: bool,
        readiness_status: ReadinessStatus | None = None,
        missing_items: list[MissingItem] | None = None,
        character_count: int | None = None,
        reference_count: int | None = None,
        scene: object | None = None,
        state: object | None = None,
    ) -> ShotResponse:
        characters: list[ShotCharacterRecord] = []
        references: list[ShotReferenceRecord] = []
        total_characters = character_count if character_count is not None else 0
        total_references = reference_count if reference_count is not None else 0
        if include_children or readiness_status is None or missing_items is None:
            characters, total_characters = self.repository.list_characters(shot.id)
            references, total_references = self.repository.list_references(shot.id)
        if readiness_status is None or missing_items is None:
            primary_count = len(
                [character for character in characters if character.is_primary_subject]
            )
            character_ref_count = len(
                [reference for reference in references if reference.reference_type == "character"]
            )
            scene_ref_count = len(
                [reference for reference in references if reference.reference_type == "scene"]
            )
            readiness_status, missing_items = self._calculate_readiness(
                shot,
                total_characters,
                primary_count,
                character_ref_count,
                scene_ref_count,
            )
        scene_record = (
            scene if scene is not None else self.repository.get_scene_by_id(shot.scene_id)
        )
        state_record = (
            state if state is not None else self.repository.get_state_by_id(shot.scene_state_id)
        )
        return ShotResponse(
            id=shot.id,
            project_id=shot.project_id,
            name=shot.name,
            order_index=shot.order_index,
            story_description=shot.story_description,
            visual_description=shot.visual_description,
            dialogue=shot.dialogue,
            action_summary=shot.action_summary,
            duration_seconds=shot.duration_seconds,
            shot_scale=ShotScale(shot.shot_scale),
            camera_height=CameraHeight(shot.camera_height),
            custom_camera_height=shot.custom_camera_height,
            camera_angle=CameraAngle(shot.camera_angle),
            custom_camera_angle=shot.custom_camera_angle,
            composition_type=ShotCompositionType(shot.composition_type),
            custom_composition=shot.custom_composition,
            camera_movement=CameraMovement(shot.camera_movement),
            custom_camera_movement=shot.custom_camera_movement,
            focal_subject=shot.focal_subject,
            mood_description=shot.mood_description,
            scene_id=shot.scene_id,
            scene_state_id=shot.scene_state_id,
            scene=ShotSceneSummary(id=scene_record.id, name=scene_record.name)
            if scene_record
            else None,
            scene_state=ShotSceneStateSummary(id=state_record.id, name=state_record.name)
            if state_record
            else None,
            notes=shot.notes,
            readiness_status=readiness_status,
            missing_items=missing_items,
            character_count=character_count if character_count is not None else total_characters,
            reference_count=reference_count if reference_count is not None else total_references,
            characters=[self._shot_character_response(character) for character in characters]
            if include_children
            else [],
            references=[self._shot_reference_response(reference) for reference in references]
            if include_children
            else [],
            created_at=ensure_utc(shot.created_at),
            updated_at=ensure_utc(shot.updated_at),
        )

    @staticmethod
    def _calculate_readiness(
        shot: ShotRecord,
        character_count: int,
        primary_subject_count: int,
        character_reference_count: int,
        scene_reference_count: int,
    ) -> tuple[ReadinessStatus, list[MissingItem]]:
        missing: list[MissingItem] = []
        if not shot.visual_description:
            missing.append(MissingItem.VISUAL_DESCRIPTION)
        if not shot.scene_id:
            missing.append(MissingItem.SCENE)
        if not shot.scene_state_id:
            missing.append(MissingItem.SCENE_STATE)
        if character_count == 0:
            missing.append(MissingItem.CHARACTERS)
        basic_missing = {
            MissingItem.VISUAL_DESCRIPTION,
            MissingItem.SCENE,
            MissingItem.SCENE_STATE,
            MissingItem.CHARACTERS,
        }
        if any(item in basic_missing for item in missing):
            return ReadinessStatus.DRAFT, missing
        if primary_subject_count == 0:
            missing.append(MissingItem.PRIMARY_SUBJECT)
        if character_reference_count == 0:
            missing.append(MissingItem.CHARACTER_REFERENCES)
        if scene_reference_count == 0:
            missing.append(MissingItem.SCENE_REFERENCES)
        if missing:
            return ReadinessStatus.BASIC_READY, missing
        return ReadinessStatus.ASSET_READY, []

    def _shot_character_response(self, record: ShotCharacterRecord) -> ShotCharacterResponse:
        character = self.repository.get_characters_by_ids([record.character_id]).get(
            record.character_id
        )
        looks = self.repository.get_looks_by_ids([record.look_id] if record.look_id else [])
        look = looks.get(record.look_id or "")
        return ShotCharacterResponse(
            id=record.id,
            shot_id=record.shot_id,
            character_id=record.character_id,
            character_name=character.name if character else "已删除角色",
            look_id=record.look_id,
            look_name=look.name if look else None,
            action_description=record.action_description,
            expression_description=record.expression_description,
            position_description=record.position_description,
            is_primary_subject=record.is_primary_subject,
            order_index=record.order_index,
            notes=record.notes,
            created_at=ensure_utc(record.created_at),
            updated_at=ensure_utc(record.updated_at),
        )

    def _shot_reference_response(self, record: ShotReferenceRecord) -> ShotReferenceResponse:
        character_reference = None
        scene_reference = None
        media_asset = None
        if (
            record.reference_type == ShotReferenceType.CHARACTER.value
            and record.character_reference_id
        ):
            source = self.repository.get_character_reference(record.character_reference_id)
            if source is not None:
                character_reference = self._character_reference_response(source)
                media_asset = character_reference.media_asset
        if record.reference_type == ShotReferenceType.SCENE.value and record.scene_reference_id:
            source_scene = self.repository.get_scene_reference(record.scene_reference_id)
            if source_scene is not None:
                scene_reference = self._scene_reference_response(source_scene)
                media_asset = scene_reference.media_asset
        return ShotReferenceResponse(
            id=record.id,
            shot_id=record.shot_id,
            reference_type=ShotReferenceType(record.reference_type),
            character_reference_id=record.character_reference_id,
            scene_reference_id=record.scene_reference_id,
            shot_character_id=record.shot_character_id,
            purpose=record.purpose,
            order_index=record.order_index,
            notes=record.notes,
            media_asset=media_asset,
            character_reference=character_reference,
            scene_reference=scene_reference,
            created_at=ensure_utc(record.created_at),
            updated_at=ensure_utc(record.updated_at),
        )

    def _character_reference_response(
        self, reference: CharacterReferenceRecord
    ) -> CharacterReferenceResponse:
        suggestions = None
        if reference.analysis_suggestions:
            suggestions = json.loads(reference.analysis_suggestions)
        return CharacterReferenceResponse(
            id=reference.id,
            look_id=reference.look_id,
            media_asset_id=reference.media_asset_id,
            shot_type=CharacterShotType(reference.shot_type),
            view_angle=ViewAngle(reference.view_angle),
            expression=Expression(reference.expression),
            pose_type=PoseType(reference.pose_type),
            custom_expression=reference.custom_expression,
            custom_pose=reference.custom_pose,
            tags=json.loads(reference.tags or "[]"),
            description=reference.description,
            notes=reference.notes,
            is_primary=reference.is_primary,
            is_identity_anchor=reference.is_identity_anchor,
            analysis_status=CharacterAnalysisStatus(reference.analysis_status),
            suggestion_review_status=CharacterSuggestionReviewStatus(
                reference.suggestion_review_status
            ),
            analysis_suggestions=suggestions,
            media_asset=self._media_asset_response(reference.media_asset),
            created_at=ensure_utc(reference.created_at),
            updated_at=ensure_utc(reference.updated_at),
        )

    def _scene_reference_response(self, reference: SceneReferenceRecord) -> SceneReferenceResponse:
        suggestions = None
        if reference.analysis_suggestions:
            suggestions = json.loads(reference.analysis_suggestions)
        return SceneReferenceResponse(
            id=reference.id,
            state_id=reference.state_id,
            media_asset_id=reference.media_asset_id,
            shot_scale=SceneShotScale(reference.shot_scale),
            camera_position=CameraPosition(reference.camera_position),
            custom_camera_position=reference.custom_camera_position,
            view_direction=ViewDirection(reference.view_direction),
            custom_view_direction=reference.custom_view_direction,
            composition_type=CompositionType(reference.composition_type),
            custom_composition=reference.custom_composition,
            is_empty_plate=reference.is_empty_plate,
            is_primary=reference.is_primary,
            is_spatial_anchor=reference.is_spatial_anchor,
            tags=json.loads(reference.tags or "[]"),
            description=reference.description,
            notes=reference.notes,
            analysis_status=SceneAnalysisStatus(reference.analysis_status),
            suggestion_review_status=SceneSuggestionReviewStatus(
                reference.suggestion_review_status
            ),
            analysis_suggestions=suggestions,
            media_asset=self._media_asset_response(reference.media_asset),
            created_at=ensure_utc(reference.created_at),
            updated_at=ensure_utc(reference.updated_at),
        )

    @staticmethod
    def _media_asset_response(media_asset: MediaAssetRecord) -> MediaAssetResponse:
        return MediaAssetResponse(
            id=media_asset.id,
            project_id=media_asset.project_id,
            media_type=media_asset.media_type,
            original_filename=media_asset.original_filename,
            mime_type=media_asset.mime_type,
            extension=media_asset.extension,
            size_bytes=media_asset.size_bytes,
            width=media_asset.width,
            height=media_asset.height,
            sha256=media_asset.sha256,
            thumbnail_url=f"/api/media/{media_asset.id}/thumbnail",
            content_url=f"/api/media/{media_asset.id}/content",
            created_at=ensure_utc(media_asset.created_at),
        )

    @staticmethod
    def _normalize_name(value: object) -> str:
        try:
            return normalize_required_text(
                value if isinstance(value, str) else None,
                ShotErrorCode.NAME_REQUIRED,
                ShotErrorCode.NAME_TOO_LONG,
                120,
            )
        except ValueError as exc:
            code = exc.args[0] if exc.args else ShotErrorCode.NAME_REQUIRED
            raise_shot_error(ShotErrorCode(code), HTTP_422)

    @staticmethod
    def _optional(value: object, max_length: int) -> str | None:
        try:
            return normalize_optional_text(value if isinstance(value, str) else None, max_length)
        except ValueError:
            raise_shot_error(ShotErrorCode.NAME_TOO_LONG, HTTP_422)

    @staticmethod
    def _normalize_custom(
        enum_value: object,
        custom_value: object,
        custom_enum: object,
        required_code: ShotErrorCode,
    ) -> str | None:
        if enum_value != custom_enum:
            return None
        value = ShotService._optional(custom_value, 120)
        if value is None:
            raise_shot_error(required_code, HTTP_422)
        return value

    @staticmethod
    def _apply_custom_update(
        values: dict[str, object],
        submitted: dict[str, object],
        enum_key: str,
        custom_key: str,
        enum_class: type,
        custom_enum: object,
        current_enum: str,
        current_custom: str | None,
        required_code: ShotErrorCode,
    ) -> None:
        if enum_key not in submitted and custom_key not in submitted:
            return
        effective_enum = submitted.get(enum_key) or enum_class(current_enum)
        effective_custom = submitted.get(custom_key, current_custom)
        values[enum_key] = effective_enum.value
        values[custom_key] = ShotService._normalize_custom(
            effective_enum, effective_custom, custom_enum, required_code
        )


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def raise_shot_error(code: ShotErrorCode, http_status: int) -> None:
    raise AppError(code=code.value, message=ERROR_MESSAGES[code], status_code=http_status)
