import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError

from app.api.schemas.vision_analysis import (
    AnalysisConfirmRequest,
    CharacterVisionAnalysisSuggestion,
    LatestVisionAnalysisTaskResponse,
    SceneVisionAnalysisSuggestion,
    VisionAnalysisTaskResponse,
)
from app.core.config import get_settings
from app.core.errors import AppError
from app.domain.character import (
    AnalysisStatus as CharacterAnalysisStatus,
)
from app.domain.character import (
    Expression,
    PoseType,
    ShotType,
    ViewAngle,
    normalize_optional_text,
    normalize_tags,
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
    ShotScale,
    ViewDirection,
)
from app.domain.scene import (
    SuggestionReviewStatus as SceneSuggestionReviewStatus,
)
from app.domain.scene import (
    normalize_tags as normalize_scene_tags,
)
from app.domain.vision_analysis import (
    VISION_ERROR_MESSAGES,
    VisionAnalysisErrorCode,
    VisionAnalysisTargetType,
    VisionAnalysisTaskStatus,
)
from app.infrastructure.models.character import CharacterReferenceRecord
from app.infrastructure.models.scene import SceneReferenceRecord
from app.infrastructure.models.vision_analysis import VisionAnalysisTaskRecord
from app.infrastructure.vision.factory import is_vision_analysis_available
from app.repository.vision_analysis_repository import VisionAnalysisRepository

CHARACTER_ALLOWED_FIELDS = {
    "shot_type",
    "view_angle",
    "expression",
    "custom_expression",
    "pose_type",
    "custom_pose",
    "tags",
    "description",
    "is_identity_anchor",
}

SCENE_ALLOWED_FIELDS = {
    "shot_scale",
    "camera_position",
    "custom_camera_position",
    "view_direction",
    "custom_view_direction",
    "composition_type",
    "custom_composition",
    "tags",
    "description",
    "is_spatial_anchor",
    "is_empty_plate",
}


class VisionAnalysisService:
    def __init__(self, repository: VisionAnalysisRepository) -> None:
        self.repository = repository

    def get_task(self, project_id: UUID, task_id: UUID) -> VisionAnalysisTaskResponse:
        task = self.repository.get_task(str(project_id), str(task_id))
        if task is None:
            raise_vision_error(
                VisionAnalysisErrorCode.ANALYSIS_TASK_NOT_FOUND,
                status.HTTP_404_NOT_FOUND,
            )
        return self._task_response(task)

    def get_latest_character_task(
        self,
        project_id: UUID,
        character_id: UUID,
        look_id: UUID,
        reference_id: UUID,
    ) -> LatestVisionAnalysisTaskResponse:
        reference = self.repository.get_character_reference_for_path(
            str(project_id), str(character_id), str(look_id), str(reference_id)
        )
        if reference is None:
            raise_vision_error(VisionAnalysisErrorCode.MEDIA_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        task = self.repository.get_latest_character_task(str(project_id), str(reference_id))
        return LatestVisionAnalysisTaskResponse(
            task=self._task_response(task) if task is not None else None
        )

    def get_latest_scene_task(
        self,
        project_id: UUID,
        scene_id: UUID,
        state_id: UUID,
        reference_id: UUID,
    ) -> LatestVisionAnalysisTaskResponse:
        reference = self.repository.get_scene_reference_for_path(
            str(project_id), str(scene_id), str(state_id), str(reference_id)
        )
        if reference is None:
            raise_vision_error(VisionAnalysisErrorCode.MEDIA_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        task = self.repository.get_latest_scene_task(str(project_id), str(reference_id))
        return LatestVisionAnalysisTaskResponse(
            task=self._task_response(task) if task is not None else None
        )

    def create_character_task(
        self,
        project_id: UUID,
        character_id: UUID,
        look_id: UUID,
        reference_id: UUID,
    ) -> VisionAnalysisTaskResponse:
        self._ensure_available()
        reference = self.repository.get_character_reference_for_path(
            str(project_id), str(character_id), str(look_id), str(reference_id)
        )
        if reference is None:
            raise_vision_error(VisionAnalysisErrorCode.MEDIA_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        if self.repository.has_active_character_task(str(project_id), str(reference_id)):
            raise_vision_error(
                VisionAnalysisErrorCode.ANALYSIS_ALREADY_RUNNING,
                status.HTTP_409_CONFLICT,
            )
        return self._create_task(
            project_id=str(project_id),
            target_type=VisionAnalysisTargetType.CHARACTER_REFERENCE,
            reference=reference,
        )

    def create_scene_task(
        self,
        project_id: UUID,
        scene_id: UUID,
        state_id: UUID,
        reference_id: UUID,
    ) -> VisionAnalysisTaskResponse:
        self._ensure_available()
        reference = self.repository.get_scene_reference_for_path(
            str(project_id), str(scene_id), str(state_id), str(reference_id)
        )
        if reference is None:
            raise_vision_error(VisionAnalysisErrorCode.MEDIA_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        if self.repository.has_active_scene_task(str(project_id), str(reference_id)):
            raise_vision_error(
                VisionAnalysisErrorCode.ANALYSIS_ALREADY_RUNNING,
                status.HTTP_409_CONFLICT,
            )
        return self._create_task(
            project_id=str(project_id),
            target_type=VisionAnalysisTargetType.SCENE_REFERENCE,
            reference=reference,
        )

    def confirm_character_suggestions(
        self,
        project_id: UUID,
        character_id: UUID,
        look_id: UUID,
        reference_id: UUID,
        payload: AnalysisConfirmRequest,
    ) -> CharacterSuggestionReviewStatus:
        reference = self.repository.get_character_reference_for_path(
            str(project_id), str(character_id), str(look_id), str(reference_id)
        )
        if reference is None:
            raise_vision_error(VisionAnalysisErrorCode.MEDIA_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        suggestion = _load_character_suggestion(reference)
        values = _validate_confirm_payload(payload, CHARACTER_ALLOWED_FIELDS)
        official_values = _character_official_values(values, reference, suggestion)
        status_raw = _review_status(
            payload.accepted_fields,
            official_values,
            _suggested_character_values(suggestion),
        )
        for key, value in official_values.items():
            setattr(reference, key, value)
        now = utc_now()
        reference.suggestion_review_status = status_raw
        reference.updated_at = now
        self.repository.session.commit()
        return CharacterSuggestionReviewStatus(status_raw)

    def confirm_scene_suggestions(
        self,
        project_id: UUID,
        scene_id: UUID,
        state_id: UUID,
        reference_id: UUID,
        payload: AnalysisConfirmRequest,
    ) -> SceneSuggestionReviewStatus:
        reference = self.repository.get_scene_reference_for_path(
            str(project_id), str(scene_id), str(state_id), str(reference_id)
        )
        if reference is None:
            raise_vision_error(VisionAnalysisErrorCode.MEDIA_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        suggestion = _load_scene_suggestion(reference)
        values = _validate_confirm_payload(payload, SCENE_ALLOWED_FIELDS)
        official_values = _scene_official_values(values, reference, suggestion)
        status_raw = _review_status(
            payload.accepted_fields,
            official_values,
            _suggested_scene_values(suggestion),
        )
        for key, value in official_values.items():
            setattr(reference, key, value)
        now = utc_now()
        reference.suggestion_review_status = status_raw
        reference.updated_at = now
        self.repository.session.commit()
        return SceneSuggestionReviewStatus(status_raw)

    def reject_character_suggestions(
        self,
        project_id: UUID,
        character_id: UUID,
        look_id: UUID,
        reference_id: UUID,
    ) -> CharacterSuggestionReviewStatus:
        reference = self.repository.get_character_reference_for_path(
            str(project_id), str(character_id), str(look_id), str(reference_id)
        )
        if reference is None:
            raise_vision_error(VisionAnalysisErrorCode.MEDIA_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        _load_character_suggestion(reference)
        reference.suggestion_review_status = CharacterSuggestionReviewStatus.REJECTED.value
        reference.updated_at = utc_now()
        self.repository.session.commit()
        return CharacterSuggestionReviewStatus.REJECTED

    def reject_scene_suggestions(
        self,
        project_id: UUID,
        scene_id: UUID,
        state_id: UUID,
        reference_id: UUID,
    ) -> SceneSuggestionReviewStatus:
        reference = self.repository.get_scene_reference_for_path(
            str(project_id), str(scene_id), str(state_id), str(reference_id)
        )
        if reference is None:
            raise_vision_error(VisionAnalysisErrorCode.MEDIA_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        _load_scene_suggestion(reference)
        reference.suggestion_review_status = SceneSuggestionReviewStatus.REJECTED.value
        reference.updated_at = utc_now()
        self.repository.session.commit()
        return SceneSuggestionReviewStatus.REJECTED

    def _create_task(
        self,
        project_id: str,
        target_type: VisionAnalysisTargetType,
        reference: CharacterReferenceRecord | SceneReferenceRecord,
    ) -> VisionAnalysisTaskResponse:
        now = utc_now()
        settings = get_settings()
        task = VisionAnalysisTaskRecord(
            id=str(uuid4()),
            project_id=project_id,
            target_type=target_type.value,
            character_reference_id=reference.id
            if target_type == VisionAnalysisTargetType.CHARACTER_REFERENCE
            else None,
            scene_reference_id=reference.id
            if target_type == VisionAnalysisTargetType.SCENE_REFERENCE
            else None,
            provider=settings.vision_provider,
            model_name=settings.openai_vision_model,
            status=VisionAnalysisTaskStatus.PENDING.value,
            attempt_count=0,
            error_code=None,
            error_message_safe=None,
            started_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        try:
            reference.analysis_status = (
                CharacterAnalysisStatus.PENDING.value
                if target_type == VisionAnalysisTargetType.CHARACTER_REFERENCE
                else SceneAnalysisStatus.PENDING.value
            )
            reference.updated_at = now
            self.repository.create_task(task)
            self.repository.session.commit()
            self.repository.session.refresh(task)
        except SQLAlchemyError:
            self.repository.session.rollback()
            raise_vision_error(
                VisionAnalysisErrorCode.ANALYSIS_ALREADY_RUNNING,
                status.HTTP_409_CONFLICT,
            )
        return self._task_response(task)

    @staticmethod
    def _task_response(task: VisionAnalysisTaskRecord) -> VisionAnalysisTaskResponse:
        return VisionAnalysisTaskResponse(
            id=task.id,
            project_id=task.project_id,
            target_type=VisionAnalysisTargetType(task.target_type),
            character_reference_id=task.character_reference_id,
            scene_reference_id=task.scene_reference_id,
            provider=task.provider,
            status=VisionAnalysisTaskStatus(task.status),
            attempt_count=task.attempt_count,
            error_code=task.error_code,
            error_message_safe=task.error_message_safe,
            started_at=ensure_utc(task.started_at) if task.started_at else None,
            completed_at=ensure_utc(task.completed_at) if task.completed_at else None,
            created_at=ensure_utc(task.created_at),
            updated_at=ensure_utc(task.updated_at),
        )

    def _ensure_available(self) -> None:
        if not is_vision_analysis_available(get_settings()):
            raise_vision_error(
                VisionAnalysisErrorCode.PROVIDER_NOT_CONFIGURED,
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )


def _load_character_suggestion(
    reference: CharacterReferenceRecord,
) -> CharacterVisionAnalysisSuggestion:
    if reference.analysis_suggestions is None:
        raise_vision_error(
            VisionAnalysisErrorCode.SUGGESTION_NOT_AVAILABLE,
            status.HTTP_409_CONFLICT,
        )
    try:
        return CharacterVisionAnalysisSuggestion.model_validate_json(reference.analysis_suggestions)
    except ValueError:
        raise_vision_error(
            VisionAnalysisErrorCode.SUGGESTION_VALIDATION_FAILED,
            status.HTTP_409_CONFLICT,
        )


def _load_scene_suggestion(reference: SceneReferenceRecord) -> SceneVisionAnalysisSuggestion:
    if reference.analysis_suggestions is None:
        raise_vision_error(
            VisionAnalysisErrorCode.SUGGESTION_NOT_AVAILABLE,
            status.HTTP_409_CONFLICT,
        )
    try:
        return SceneVisionAnalysisSuggestion.model_validate_json(reference.analysis_suggestions)
    except ValueError:
        raise_vision_error(
            VisionAnalysisErrorCode.SUGGESTION_VALIDATION_FAILED,
            status.HTTP_409_CONFLICT,
        )


def _validate_confirm_payload(payload: AnalysisConfirmRequest, allowed: set[str]) -> dict[str, Any]:
    fields = list(dict.fromkeys(payload.accepted_fields))
    if not fields:
        raise_vision_error(
            VisionAnalysisErrorCode.SUGGESTION_VALIDATION_FAILED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    unknown = set(fields) - allowed
    extra = set(payload.values) - set(fields)
    if unknown or extra:
        raise_vision_error(
            VisionAnalysisErrorCode.SUGGESTION_VALIDATION_FAILED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return {field: payload.values.get(field) for field in fields}


def _character_official_values(
    values: dict[str, Any],
    reference: CharacterReferenceRecord,
    suggestion: CharacterVisionAnalysisSuggestion,
) -> dict[str, object]:
    result: dict[str, object] = {}
    expression = Expression(values.get("expression", reference.expression))
    pose = PoseType(values.get("pose_type", reference.pose_type))
    for key, enum_type in {
        "shot_type": ShotType,
        "view_angle": ViewAngle,
        "expression": Expression,
        "pose_type": PoseType,
    }.items():
        if key in values:
            result[key] = enum_type(values[key]).value
    if "custom_expression" in values or "expression" in values:
        if expression == Expression.CUSTOM:
            custom = normalize_optional_text(str(values.get("custom_expression") or ""), 100)
            if custom is None:
                raise_vision_error(
                    VisionAnalysisErrorCode.SUGGESTION_VALIDATION_FAILED,
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            result["custom_expression"] = custom
        else:
            result["custom_expression"] = None
    if "custom_pose" in values or "pose_type" in values:
        if pose == PoseType.CUSTOM:
            custom = normalize_optional_text(str(values.get("custom_pose") or ""), 100)
            if custom is None:
                raise_vision_error(
                    VisionAnalysisErrorCode.SUGGESTION_VALIDATION_FAILED,
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            result["custom_pose"] = custom
        else:
            result["custom_pose"] = None
    if "tags" in values:
        tags = values["tags"] if isinstance(values["tags"], list) else []
        result["tags"] = json.dumps(normalize_tags([str(tag) for tag in tags]), ensure_ascii=False)
    if "description" in values:
        result["description"] = normalize_optional_text(
            values["description"] if isinstance(values["description"], str) else None,
            1000,
        )
    if "is_identity_anchor" in values:
        result["is_identity_anchor"] = bool(values["is_identity_anchor"])
    CharacterVisionAnalysisSuggestion.model_validate(suggestion)
    return result


def _scene_official_values(
    values: dict[str, Any],
    reference: SceneReferenceRecord,
    suggestion: SceneVisionAnalysisSuggestion,
) -> dict[str, object]:
    result: dict[str, object] = {}
    camera = CameraPosition(values.get("camera_position", reference.camera_position))
    direction = ViewDirection(values.get("view_direction", reference.view_direction))
    composition = CompositionType(values.get("composition_type", reference.composition_type))
    for key, enum_type in {
        "shot_scale": ShotScale,
        "camera_position": CameraPosition,
        "view_direction": ViewDirection,
        "composition_type": CompositionType,
    }.items():
        if key in values:
            result[key] = enum_type(values[key]).value
    for key, enum_value, output_key in (
        ("custom_camera_position", camera, "custom_camera_position"),
        ("custom_view_direction", direction, "custom_view_direction"),
        ("custom_composition", composition, "custom_composition"),
    ):
        if key in values or output_key.replace("custom_", "") in values:
            if enum_value.value == "custom":
                custom = normalize_optional_text(str(values.get(key) or ""), 120)
                if custom is None:
                    raise_vision_error(
                        VisionAnalysisErrorCode.SUGGESTION_VALIDATION_FAILED,
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                    )
                result[output_key] = custom
            else:
                result[output_key] = None
    if "tags" in values:
        tags = values["tags"] if isinstance(values["tags"], list) else []
        result["tags"] = json.dumps(
            normalize_scene_tags([str(tag) for tag in tags]),
            ensure_ascii=False,
        )
    if "description" in values:
        result["description"] = normalize_optional_text(
            values["description"] if isinstance(values["description"], str) else None,
            1000,
        )
    if "is_spatial_anchor" in values:
        result["is_spatial_anchor"] = bool(values["is_spatial_anchor"])
    if "is_empty_plate" in values:
        result["is_empty_plate"] = bool(values["is_empty_plate"])
    SceneVisionAnalysisSuggestion.model_validate(suggestion)
    return result


def _suggested_character_values(suggestion: CharacterVisionAnalysisSuggestion) -> dict[str, object]:
    values: dict[str, object] = {
        "shot_type": suggestion.shot_type.value,
        "view_angle": suggestion.view_angle.value,
        "expression": suggestion.expression.value,
        "pose_type": suggestion.pose_type.value,
        "tags": suggestion.tags,
        "description": suggestion.description,
    }
    if suggestion.expression == Expression.CUSTOM:
        values["custom_expression"] = suggestion.custom_expression
    if suggestion.pose_type == PoseType.CUSTOM:
        values["custom_pose"] = suggestion.custom_pose
    if suggestion.identity_anchor_recommended:
        values["is_identity_anchor"] = True
    return {key: value for key, value in values.items() if value not in (None, "", [], "unknown")}


def _suggested_scene_values(suggestion: SceneVisionAnalysisSuggestion) -> dict[str, object]:
    values: dict[str, object] = {
        "shot_scale": suggestion.shot_scale.value,
        "camera_position": suggestion.camera_position.value,
        "view_direction": suggestion.view_direction.value,
        "composition_type": suggestion.composition_type.value,
        "tags": suggestion.tags,
        "description": suggestion.description,
    }
    if suggestion.camera_position == CameraPosition.CUSTOM:
        values["custom_camera_position"] = suggestion.custom_camera_position
    if suggestion.view_direction == ViewDirection.CUSTOM:
        values["custom_view_direction"] = suggestion.custom_view_direction
    if suggestion.composition_type == CompositionType.CUSTOM:
        values["custom_composition"] = suggestion.custom_composition
    if suggestion.spatial_anchor_recommended:
        values["is_spatial_anchor"] = True
    if suggestion.empty_plate_recommended:
        values["is_empty_plate"] = True
    return {key: value for key, value in values.items() if value not in (None, "", [], "unknown")}


def _review_status(
    accepted_fields: list[str],
    official_values: dict[str, object],
    suggested_values: dict[str, object],
) -> str:
    accepted_set = set(accepted_fields)
    suggested_set = set(suggested_values)
    if accepted_set == suggested_set and all(
        _compare_stored_value(official_values.get(key), suggested_values[key])
        for key in suggested_set
    ):
        return CharacterSuggestionReviewStatus.ACCEPTED.value
    return CharacterSuggestionReviewStatus.EDITED_AND_ACCEPTED.value


def _compare_stored_value(value: object, suggested: object) -> bool:
    if isinstance(value, str) and isinstance(suggested, list):
        return json.loads(value or "[]") == suggested
    return value == suggested


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def raise_vision_error(code: VisionAnalysisErrorCode, http_status: int) -> None:
    raise AppError(
        code=code.value,
        message=VISION_ERROR_MESSAGES[code.value],
        status_code=http_status,
    )
