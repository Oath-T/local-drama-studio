import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import UploadFile, status

from app.api.schemas.character import MediaAssetResponse
from app.api.schemas.scene import (
    SceneCreateRequest,
    SceneListResponse,
    SceneReferenceListResponse,
    SceneReferenceResponse,
    SceneReferenceUpdateRequest,
    SceneResponse,
    SceneStateCreateRequest,
    SceneStateListResponse,
    SceneStateResponse,
    SceneStateUpdateRequest,
    SceneUpdateRequest,
    SceneVisionAnalysisSuggestion,
)
from app.core.errors import AppError
from app.domain.media_asset import MediaType
from app.domain.scene import (
    AnalysisStatus,
    CameraPosition,
    CompositionType,
    CrowdLevel,
    Lighting,
    SceneErrorCode,
    SceneType,
    Season,
    ShotScale,
    SuggestionReviewStatus,
    TimeOfDay,
    ViewDirection,
    Weather,
    normalize_optional_text,
    normalize_required_text,
    normalize_tags,
)
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.scene import (
    SceneRecord,
    SceneReferenceRecord,
    SceneStateRecord,
)
from app.repository.scene_repository import SceneListData, SceneRepository
from app.service.media_storage_service import MediaStorageService, StoredImage

ERROR_MESSAGES: dict[SceneErrorCode, str] = {
    SceneErrorCode.PROJECT_NOT_FOUND: "项目不存在或已被删除。",
    SceneErrorCode.SCENE_NOT_FOUND: "场景不存在或已被删除。",
    SceneErrorCode.STATE_NOT_FOUND: "场景状态不存在或已被删除。",
    SceneErrorCode.REFERENCE_NOT_FOUND: "场景参考图不存在或已被删除。",
    SceneErrorCode.MEDIA_NOT_FOUND: "媒体文件不存在或已被删除。",
    SceneErrorCode.NAME_REQUIRED: "请输入场景名称。",
    SceneErrorCode.NAME_TOO_LONG: "场景名称不能超过 120 个字符。",
    SceneErrorCode.STATE_NAME_REQUIRED: "请输入场景状态名称。",
    SceneErrorCode.STATE_NAME_TOO_LONG: "场景状态名称不能超过 120 个字符。",
    SceneErrorCode.CUSTOM_WEATHER_REQUIRED: "选择自定义天气时，请填写天气说明。",
    SceneErrorCode.CUSTOM_LIGHTING_REQUIRED: "选择自定义灯光时，请填写灯光说明。",
    SceneErrorCode.CUSTOM_CAMERA_POSITION_REQUIRED: "选择自定义机位时，请填写机位说明。",
    SceneErrorCode.CUSTOM_VIEW_DIRECTION_REQUIRED: "选择自定义朝向时，请填写朝向说明。",
    SceneErrorCode.CUSTOM_COMPOSITION_REQUIRED: "选择自定义构图时，请填写构图说明。",
    SceneErrorCode.LAST_STATE_DELETE_FORBIDDEN: "不能删除场景的最后一个状态。",
}

HTTP_422 = 422


class SceneService:
    def __init__(
        self,
        repository: SceneRepository,
        storage_service: MediaStorageService | None = None,
    ) -> None:
        self.repository = repository
        self.storage_service = storage_service or MediaStorageService()

    def list_scenes(self, project_id: UUID) -> SceneListResponse:
        self._ensure_project(project_id)
        data = self.repository.list_scenes(str(project_id))
        return SceneListResponse(
            items=[self._scene_response_from_list(scene, data) for scene in data.scenes],
            total=data.total,
        )

    def create_scene(self, project_id: UUID, payload: SceneCreateRequest) -> SceneResponse:
        self._ensure_project(project_id)
        now = utc_now()
        scene = SceneRecord(
            id=str(uuid4()),
            project_id=str(project_id),
            name=self._normalize_scene_name(payload.name),
            scene_type=payload.scene_type.value,
            description=self._optional(payload.description, 1000),
            fixed_environment_description=self._optional(
                payload.fixed_environment_description, 2000
            ),
            spatial_layout_description=self._optional(payload.spatial_layout_description, 2000),
            visual_style_description=self._optional(payload.visual_style_description, 2000),
            prompt_environment=self._optional(payload.prompt_environment, 3000),
            notes=self._optional(payload.notes, 2000),
            created_at=now,
            updated_at=now,
        )
        created = self.repository.create_scene(scene)
        return self._scene_response(created)

    def get_scene(self, project_id: UUID, scene_id: UUID) -> SceneResponse:
        scene = self._get_scene(project_id, scene_id)
        return self._scene_response(scene)

    def update_scene(
        self,
        project_id: UUID,
        scene_id: UUID,
        payload: SceneUpdateRequest,
    ) -> SceneResponse:
        scene = self._get_scene(project_id, scene_id)
        submitted = payload.model_dump(exclude_unset=True)
        values: dict[str, object] = {}
        if "name" in submitted:
            values["name"] = self._normalize_scene_name(submitted["name"])
        if "scene_type" in submitted and submitted["scene_type"] is not None:
            values["scene_type"] = submitted["scene_type"].value
        for key, max_length in {
            "description": 1000,
            "fixed_environment_description": 2000,
            "spatial_layout_description": 2000,
            "visual_style_description": 2000,
            "prompt_environment": 3000,
            "notes": 2000,
        }.items():
            if key in submitted:
                values[key] = self._optional(submitted[key], max_length)
        values["updated_at"] = utc_now()
        updated = self.repository.update_scene(scene, values)
        return self._scene_response(updated)

    def delete_scene(self, project_id: UUID, scene_id: UUID) -> None:
        scene = self._get_scene(project_id, scene_id)
        references = self._all_scene_references(scene.id)
        media_assets = [reference.media_asset for reference in references]
        media_asset_ids = [media_asset.id for media_asset in media_assets]
        protected_media_ids = self.repository.get_keyframe_referenced_media_asset_ids(
            media_asset_ids
        )
        deletable_media_ids = [
            media_asset_id
            for media_asset_id in media_asset_ids
            if media_asset_id not in protected_media_ids
        ]
        self.repository.delete_scene_and_media_assets(scene, deletable_media_ids)
        for media_asset in media_assets:
            if media_asset.id in protected_media_ids:
                continue
            self._delete_media_files_safely(media_asset)

    def list_states(self, project_id: UUID, scene_id: UUID) -> SceneStateListResponse:
        scene = self._get_scene(project_id, scene_id)
        states, total = self.repository.list_states(scene.id)
        return SceneStateListResponse(
            items=[self._state_response(state) for state in states],
            total=total,
        )

    def create_state(
        self,
        project_id: UUID,
        scene_id: UUID,
        payload: SceneStateCreateRequest,
    ) -> SceneStateResponse:
        scene = self._get_scene(project_id, scene_id)
        existing, _ = self.repository.list_states(scene.id)
        now = utc_now()
        custom_weather = self._normalize_custom_for_enum(
            payload.weather,
            payload.custom_weather,
            Weather.CUSTOM,
            SceneErrorCode.CUSTOM_WEATHER_REQUIRED,
        )
        custom_lighting = self._normalize_custom_for_enum(
            payload.lighting,
            payload.custom_lighting,
            Lighting.CUSTOM,
            SceneErrorCode.CUSTOM_LIGHTING_REQUIRED,
        )
        scene.updated_at = now
        state_record = SceneStateRecord(
            id=str(uuid4()),
            scene_id=scene.id,
            name=self._normalize_state_name(payload.name),
            description=self._optional(payload.description, 1000),
            time_of_day=payload.time_of_day.value,
            weather=payload.weather.value,
            custom_weather=custom_weather,
            lighting=payload.lighting.value,
            custom_lighting=custom_lighting,
            season=payload.season.value,
            environment_condition=self._optional(payload.environment_condition, 2000),
            crowd_level=payload.crowd_level.value,
            prompt_state=self._optional(payload.prompt_state, 3000),
            is_default=len(existing) == 0,
            created_at=now,
            updated_at=now,
        )
        created = self.repository.create_state(state_record)
        return self._state_response(created)

    def get_state(self, project_id: UUID, scene_id: UUID, state_id: UUID) -> SceneStateResponse:
        state_record = self._get_state(project_id, scene_id, state_id)
        return self._state_response(state_record)

    def update_state(
        self,
        project_id: UUID,
        scene_id: UUID,
        state_id: UUID,
        payload: SceneStateUpdateRequest,
    ) -> SceneStateResponse:
        state_record = self._get_state(project_id, scene_id, state_id)
        submitted = payload.model_dump(exclude_unset=True)
        values: dict[str, object] = {}
        if "name" in submitted:
            values["name"] = self._normalize_state_name(submitted["name"])
        for key, max_length in {
            "description": 1000,
            "environment_condition": 2000,
            "prompt_state": 3000,
        }.items():
            if key in submitted:
                values[key] = self._optional(submitted[key], max_length)
        for key in ("time_of_day", "season", "crowd_level"):
            if key in submitted and submitted[key] is not None:
                values[key] = submitted[key].value
        effective_weather = submitted.get("weather") or Weather(state_record.weather)
        effective_custom_weather = submitted.get("custom_weather", state_record.custom_weather)
        values["weather"] = effective_weather.value
        values["custom_weather"] = self._normalize_custom_for_enum(
            effective_weather,
            effective_custom_weather,
            Weather.CUSTOM,
            SceneErrorCode.CUSTOM_WEATHER_REQUIRED,
        )
        effective_lighting = submitted.get("lighting") or Lighting(state_record.lighting)
        effective_custom_lighting = submitted.get("custom_lighting", state_record.custom_lighting)
        values["lighting"] = effective_lighting.value
        values["custom_lighting"] = self._normalize_custom_for_enum(
            effective_lighting,
            effective_custom_lighting,
            Lighting.CUSTOM,
            SceneErrorCode.CUSTOM_LIGHTING_REQUIRED,
        )
        now = utc_now()
        values["updated_at"] = now
        state_record.scene.updated_at = now
        updated = self.repository.update_state(state_record, values)
        return self._state_response(updated)

    def set_default_state(
        self, project_id: UUID, scene_id: UUID, state_id: UUID
    ) -> SceneStateResponse:
        state_record = self._get_state(project_id, scene_id, state_id)
        now = utc_now()
        self.repository.clear_default_states(str(scene_id))
        state_record.scene.updated_at = now
        updated = self.repository.update_state(
            state_record, {"is_default": True, "updated_at": now}
        )
        return self._state_response(updated)

    def delete_state(self, project_id: UUID, scene_id: UUID, state_id: UUID) -> None:
        state_record = self._get_state(project_id, scene_id, state_id)
        states, _ = self.repository.list_states(str(scene_id))
        if len(states) <= 1:
            raise_scene_error(
                SceneErrorCode.LAST_STATE_DELETE_FORBIDDEN,
                status.HTTP_400_BAD_REQUEST,
            )
        references, _ = self.repository.list_references(state_record.id)
        media_assets = [reference.media_asset for reference in references]
        next_default = self._select_next_default_state(state_record, states)
        state_record.scene.updated_at = utc_now()
        media_asset_ids = [media_asset.id for media_asset in media_assets]
        protected_media_ids = self.repository.get_keyframe_referenced_media_asset_ids(
            media_asset_ids
        )
        deletable_media_ids = [
            media_asset_id
            for media_asset_id in media_asset_ids
            if media_asset_id not in protected_media_ids
        ]
        self.repository.delete_state_and_media_assets(
            state_record,
            deletable_media_ids,
            next_default,
        )
        for media_asset in media_assets:
            if media_asset.id in protected_media_ids:
                continue
            self._delete_media_files_safely(media_asset)

    def list_references(
        self, project_id: UUID, scene_id: UUID, state_id: UUID
    ) -> SceneReferenceListResponse:
        state_record = self._get_state(project_id, scene_id, state_id)
        references, total = self.repository.list_references(state_record.id)
        return SceneReferenceListResponse(
            items=[self._reference_response(reference) for reference in references],
            total=total,
        )

    async def upload_reference(
        self,
        project_id: UUID,
        scene_id: UUID,
        state_id: UUID,
        upload: UploadFile,
        payload: SceneReferenceUpdateRequest,
    ) -> SceneReferenceResponse:
        state_record = self._get_state(project_id, scene_id, state_id)
        stored = await self.storage_service.store_scene_reference_image(
            str(project_id), str(scene_id), str(state_id), upload
        )
        references, _ = self.repository.list_references(state_record.id)
        now = utc_now()
        media_asset = self._media_asset_from_stored(stored, str(project_id), now)
        reference = SceneReferenceRecord(
            id=str(uuid4()),
            state_id=state_record.id,
            media_asset_id=media_asset.id,
            shot_scale=(payload.shot_scale or ShotScale.UNKNOWN).value,
            camera_position=(payload.camera_position or CameraPosition.UNKNOWN).value,
            custom_camera_position=self._normalize_reference_custom(
                payload.camera_position or CameraPosition.UNKNOWN,
                payload.custom_camera_position,
                CameraPosition.CUSTOM,
                SceneErrorCode.CUSTOM_CAMERA_POSITION_REQUIRED,
            ),
            view_direction=(payload.view_direction or ViewDirection.UNKNOWN).value,
            custom_view_direction=self._normalize_reference_custom(
                payload.view_direction or ViewDirection.UNKNOWN,
                payload.custom_view_direction,
                ViewDirection.CUSTOM,
                SceneErrorCode.CUSTOM_VIEW_DIRECTION_REQUIRED,
            ),
            composition_type=(payload.composition_type or CompositionType.UNKNOWN).value,
            custom_composition=self._normalize_reference_custom(
                payload.composition_type or CompositionType.UNKNOWN,
                payload.custom_composition,
                CompositionType.CUSTOM,
                SceneErrorCode.CUSTOM_COMPOSITION_REQUIRED,
            ),
            is_empty_plate=bool(payload.is_empty_plate),
            is_primary=len(references) == 0,
            is_spatial_anchor=bool(payload.is_spatial_anchor),
            tags=json.dumps(normalize_tags(payload.tags), ensure_ascii=False),
            description=self._optional(payload.description, 1000),
            notes=self._optional(payload.notes, 1000),
            analysis_status=AnalysisStatus.NOT_ANALYZED.value,
            suggestion_review_status=SuggestionReviewStatus.NOT_REVIEWED.value,
            analysis_suggestions=None,
            created_at=now,
            updated_at=now,
        )
        state_record.scene.updated_at = now
        try:
            created = self.repository.create_reference(media_asset, reference)
        except Exception:
            self.storage_service.delete_relative_file(stored.relative_path)
            self.storage_service.delete_relative_file(stored.thumbnail_relative_path)
            raise
        return self._reference_response(created)

    def get_reference(
        self,
        project_id: UUID,
        scene_id: UUID,
        state_id: UUID,
        reference_id: UUID,
    ) -> SceneReferenceResponse:
        reference = self._get_reference(project_id, scene_id, state_id, reference_id)
        return self._reference_response(reference)

    def update_reference(
        self,
        project_id: UUID,
        scene_id: UUID,
        state_id: UUID,
        reference_id: UUID,
        payload: SceneReferenceUpdateRequest,
    ) -> SceneReferenceResponse:
        reference = self._get_reference(project_id, scene_id, state_id, reference_id)
        submitted = payload.model_dump(exclude_unset=True)
        values: dict[str, object] = {}
        if "shot_scale" in submitted and submitted["shot_scale"] is not None:
            values["shot_scale"] = submitted["shot_scale"].value
        effective_camera = submitted.get("camera_position") or CameraPosition(
            reference.camera_position
        )
        effective_custom_camera = submitted.get(
            "custom_camera_position", reference.custom_camera_position
        )
        values["camera_position"] = effective_camera.value
        values["custom_camera_position"] = self._normalize_reference_custom(
            effective_camera,
            effective_custom_camera,
            CameraPosition.CUSTOM,
            SceneErrorCode.CUSTOM_CAMERA_POSITION_REQUIRED,
        )
        effective_view = submitted.get("view_direction") or ViewDirection(reference.view_direction)
        effective_custom_view = submitted.get(
            "custom_view_direction", reference.custom_view_direction
        )
        values["view_direction"] = effective_view.value
        values["custom_view_direction"] = self._normalize_reference_custom(
            effective_view,
            effective_custom_view,
            ViewDirection.CUSTOM,
            SceneErrorCode.CUSTOM_VIEW_DIRECTION_REQUIRED,
        )
        effective_composition = submitted.get("composition_type") or CompositionType(
            reference.composition_type
        )
        effective_custom_composition = submitted.get(
            "custom_composition", reference.custom_composition
        )
        values["composition_type"] = effective_composition.value
        values["custom_composition"] = self._normalize_reference_custom(
            effective_composition,
            effective_custom_composition,
            CompositionType.CUSTOM,
            SceneErrorCode.CUSTOM_COMPOSITION_REQUIRED,
        )
        for key, max_length in {
            "description": 1000,
            "notes": 1000,
        }.items():
            if key in submitted:
                values[key] = self._optional(submitted[key], max_length)
        if "tags" in submitted:
            values["tags"] = json.dumps(normalize_tags(submitted["tags"]), ensure_ascii=False)
        for key in ("is_empty_plate", "is_spatial_anchor"):
            if key in submitted:
                values[key] = bool(submitted[key])
        now = utc_now()
        values["updated_at"] = now
        reference.state.scene.updated_at = now
        updated = self.repository.update_reference(reference, values)
        return self._reference_response(updated)

    def set_primary_reference(
        self,
        project_id: UUID,
        scene_id: UUID,
        state_id: UUID,
        reference_id: UUID,
    ) -> SceneReferenceResponse:
        reference = self._get_reference(project_id, scene_id, state_id, reference_id)
        now = utc_now()
        self.repository.clear_primary_references(str(state_id))
        reference.state.scene.updated_at = now
        updated = self.repository.update_reference(
            reference, {"is_primary": True, "updated_at": now}
        )
        return self._reference_response(updated)

    def delete_reference(
        self, project_id: UUID, scene_id: UUID, state_id: UUID, reference_id: UUID
    ) -> None:
        reference = self._get_reference(project_id, scene_id, state_id, reference_id)
        media_asset = reference.media_asset
        references, _ = self.repository.list_references(str(state_id))
        next_primary = self._select_next_primary_reference(reference, references)
        reference.state.scene.updated_at = utc_now()
        protected_media_ids = self.repository.get_keyframe_referenced_media_asset_ids(
            [media_asset.id]
        )
        delete_media_asset_id = None if media_asset.id in protected_media_ids else media_asset.id
        self.repository.delete_reference_and_media_asset(
            reference,
            delete_media_asset_id,
            next_primary,
        )
        if media_asset.id not in protected_media_ids:
            self._delete_media_files_safely(media_asset)

    def _ensure_project(self, project_id: UUID) -> None:
        if not self.repository.project_exists(str(project_id)):
            raise_scene_error(SceneErrorCode.PROJECT_NOT_FOUND, status.HTTP_404_NOT_FOUND)

    def _get_scene(self, project_id: UUID, scene_id: UUID) -> SceneRecord:
        scene = self.repository.get_scene(str(project_id), str(scene_id))
        if scene is None:
            raise_scene_error(SceneErrorCode.SCENE_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        return scene

    def _get_state(self, project_id: UUID, scene_id: UUID, state_id: UUID) -> SceneStateRecord:
        self._get_scene(project_id, scene_id)
        state_record = self.repository.get_state(str(scene_id), str(state_id))
        if state_record is None:
            raise_scene_error(SceneErrorCode.STATE_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        return state_record

    def _get_reference(
        self,
        project_id: UUID,
        scene_id: UUID,
        state_id: UUID,
        reference_id: UUID,
    ) -> SceneReferenceRecord:
        self._get_state(project_id, scene_id, state_id)
        reference = self.repository.get_reference(str(state_id), str(reference_id))
        if reference is None:
            raise_scene_error(SceneErrorCode.REFERENCE_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        return reference

    def _all_scene_references(self, scene_id: str) -> list[SceneReferenceRecord]:
        states, _ = self.repository.list_states(scene_id)
        references: list[SceneReferenceRecord] = []
        for state_record in states:
            state_references, _ = self.repository.list_references(state_record.id)
            references.extend(state_references)
        return references

    @staticmethod
    def _select_next_default_state(
        deleting_state: SceneStateRecord, states: list[SceneStateRecord]
    ) -> SceneStateRecord | None:
        if not deleting_state.is_default:
            return None
        remaining = [
            state_record for state_record in states if state_record.id != deleting_state.id
        ]
        if not remaining:
            return None
        next_default = sorted(remaining, key=lambda state: (state.created_at, state.id))[0]
        next_default.is_default = True
        next_default.updated_at = utc_now()
        return next_default

    @staticmethod
    def _select_next_primary_reference(
        deleting_reference: SceneReferenceRecord,
        references: list[SceneReferenceRecord],
    ) -> SceneReferenceRecord | None:
        if not deleting_reference.is_primary:
            return None
        remaining = [reference for reference in references if reference.id != deleting_reference.id]
        if not remaining:
            return None
        next_primary = sorted(remaining, key=lambda ref: (ref.created_at, ref.id))[0]
        next_primary.is_primary = True
        next_primary.updated_at = utc_now()
        return next_primary

    def _scene_response_from_list(
        self, scene: SceneRecord, list_data: SceneListData
    ) -> SceneResponse:
        default_state = list_data.default_states.get(scene.id)
        cover = list_data.cover_references.get(scene.id)
        return SceneResponse(
            id=scene.id,
            project_id=scene.project_id,
            name=scene.name,
            scene_type=SceneType(scene.scene_type),
            description=scene.description,
            fixed_environment_description=scene.fixed_environment_description,
            spatial_layout_description=scene.spatial_layout_description,
            visual_style_description=scene.visual_style_description,
            prompt_environment=scene.prompt_environment,
            notes=scene.notes,
            default_state=self._state_response(default_state) if default_state else None,
            state_count=list_data.state_counts.get(scene.id, 0),
            reference_count=list_data.reference_counts.get(scene.id, 0),
            cover_reference=self._reference_response(cover) if cover else None,
            created_at=ensure_utc(scene.created_at),
            updated_at=ensure_utc(scene.updated_at),
        )

    def _scene_response(self, scene: SceneRecord) -> SceneResponse:
        states, _ = self.repository.list_states(scene.id)
        default_state = next((state for state in states if state.is_default), None)
        reference_count = sum(self.repository.list_references(state.id)[1] for state in states)
        cover_reference = None
        if default_state is not None:
            references, _ = self.repository.list_references(default_state.id)
            cover_reference = next(
                (reference for reference in references if reference.is_primary),
                None,
            )
        return SceneResponse(
            id=scene.id,
            project_id=scene.project_id,
            name=scene.name,
            scene_type=SceneType(scene.scene_type),
            description=scene.description,
            fixed_environment_description=scene.fixed_environment_description,
            spatial_layout_description=scene.spatial_layout_description,
            visual_style_description=scene.visual_style_description,
            prompt_environment=scene.prompt_environment,
            notes=scene.notes,
            default_state=self._state_response(default_state) if default_state else None,
            state_count=len(states),
            reference_count=reference_count,
            cover_reference=self._reference_response(cover_reference) if cover_reference else None,
            created_at=ensure_utc(scene.created_at),
            updated_at=ensure_utc(scene.updated_at),
        )

    def _state_response(self, state_record: SceneStateRecord | None) -> SceneStateResponse | None:
        if state_record is None:
            return None
        references, total = self.repository.list_references(state_record.id)
        primary = next((reference for reference in references if reference.is_primary), None)
        return SceneStateResponse(
            id=state_record.id,
            scene_id=state_record.scene_id,
            name=state_record.name,
            description=state_record.description,
            time_of_day=TimeOfDay(state_record.time_of_day),
            weather=Weather(state_record.weather),
            custom_weather=state_record.custom_weather,
            lighting=Lighting(state_record.lighting),
            custom_lighting=state_record.custom_lighting,
            season=Season(state_record.season),
            environment_condition=state_record.environment_condition,
            crowd_level=CrowdLevel(state_record.crowd_level),
            prompt_state=state_record.prompt_state,
            is_default=state_record.is_default,
            reference_count=total,
            primary_reference=self._reference_response(primary) if primary else None,
            created_at=ensure_utc(state_record.created_at),
            updated_at=ensure_utc(state_record.updated_at),
        )

    def _reference_response(self, reference: SceneReferenceRecord) -> SceneReferenceResponse:
        suggestions = None
        if reference.analysis_suggestions:
            suggestions = SceneVisionAnalysisSuggestion.model_validate_json(
                reference.analysis_suggestions
            )
        return SceneReferenceResponse(
            id=reference.id,
            state_id=reference.state_id,
            media_asset_id=reference.media_asset_id,
            shot_scale=ShotScale(reference.shot_scale),
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
            analysis_status=AnalysisStatus(reference.analysis_status),
            suggestion_review_status=SuggestionReviewStatus(reference.suggestion_review_status),
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
    def _media_asset_from_stored(
        stored: StoredImage,
        project_id: str,
        now: datetime,
    ) -> MediaAssetRecord:
        return MediaAssetRecord(
            id=str(uuid4()),
            project_id=project_id,
            media_type=MediaType.IMAGE.value,
            original_filename=stored.original_filename,
            stored_filename=stored.stored_filename,
            relative_path=stored.relative_path,
            thumbnail_relative_path=stored.thumbnail_relative_path,
            mime_type=stored.mime_type,
            extension=stored.extension,
            size_bytes=stored.size_bytes,
            width=stored.width,
            height=stored.height,
            sha256=stored.sha256,
            created_at=now,
        )

    def _delete_media_files_safely(self, media_asset: MediaAssetRecord) -> None:
        self.storage_service.delete_relative_file_safely(media_asset.relative_path)
        self.storage_service.delete_relative_file_safely(media_asset.thumbnail_relative_path)

    @staticmethod
    def _normalize_scene_name(value: object) -> str:
        try:
            return normalize_required_text(
                value if isinstance(value, str) else None,
                SceneErrorCode.NAME_REQUIRED,
                SceneErrorCode.NAME_TOO_LONG,
                120,
            )
        except ValueError as exc:
            code = exc.args[0] if exc.args else SceneErrorCode.NAME_REQUIRED
            raise_scene_error(SceneErrorCode(code), HTTP_422)

    @staticmethod
    def _normalize_state_name(value: object) -> str:
        try:
            return normalize_required_text(
                value if isinstance(value, str) else None,
                SceneErrorCode.STATE_NAME_REQUIRED,
                SceneErrorCode.STATE_NAME_TOO_LONG,
                120,
            )
        except ValueError as exc:
            code = exc.args[0] if exc.args else SceneErrorCode.STATE_NAME_REQUIRED
            raise_scene_error(SceneErrorCode(code), HTTP_422)

    @staticmethod
    def _optional(value: object, max_length: int) -> str | None:
        try:
            return normalize_optional_text(value if isinstance(value, str) else None, max_length)
        except ValueError:
            raise_scene_error(SceneErrorCode.NAME_TOO_LONG, HTTP_422)

    @staticmethod
    def _normalize_custom_for_enum(
        enum_value: object,
        custom_value: object,
        custom_enum: object,
        required_code: SceneErrorCode,
    ) -> str | None:
        if enum_value != custom_enum:
            return None
        try:
            value = normalize_optional_text(
                custom_value if isinstance(custom_value, str) else None, 120
            )
        except ValueError:
            raise_scene_error(required_code, HTTP_422)
        if value is None:
            raise_scene_error(required_code, HTTP_422)
        return value

    @staticmethod
    def _normalize_reference_custom(
        enum_value: object,
        custom_value: object,
        custom_enum: object,
        required_code: SceneErrorCode,
    ) -> str | None:
        return SceneService._normalize_custom_for_enum(
            enum_value,
            custom_value,
            custom_enum,
            required_code,
        )


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def raise_scene_error(code: SceneErrorCode, http_status: int) -> None:
    raise AppError(code=code.value, message=ERROR_MESSAGES[code], status_code=http_status)
