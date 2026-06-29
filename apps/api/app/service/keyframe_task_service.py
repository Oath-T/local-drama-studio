from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError

from app.api.schemas.character import MediaAssetResponse
from app.api.schemas.keyframe_task import (
    KeyframeShotSnapshot,
    KeyframeTaskCreateRequest,
    KeyframeTaskListResponse,
    KeyframeTaskReferenceCreateRequest,
    KeyframeTaskReferenceListResponse,
    KeyframeTaskReferenceResponse,
    KeyframeTaskReferenceUpdateRequest,
    KeyframeTaskResponse,
    KeyframeTaskUpdateRequest,
)
from app.core.errors import AppError
from app.domain.keyframe_task import (
    ASPECT_RATIO_DIMENSIONS,
    DEFAULT_ASPECT_RATIO,
    DEFAULT_GUIDANCE_SCALE,
    DEFAULT_HEIGHT,
    DEFAULT_OUTPUT_COUNT,
    DEFAULT_STEPS,
    DEFAULT_WIDTH,
    KeyframeTaskAspectRatio,
    KeyframeTaskErrorCode,
    KeyframeTaskReadinessStatus,
    KeyframeTaskReferenceType,
    KeyframeTaskStatus,
    aspect_ratio_matches,
    normalize_optional_text,
    normalize_required_text,
)
from app.domain.shot import CharacterReferencePurpose, SceneReferencePurpose
from app.infrastructure.models.character import CharacterReferenceRecord, MediaAssetRecord
from app.infrastructure.models.keyframe_task import (
    KeyframeGenerationTaskRecord,
    KeyframeGenerationTaskReferenceRecord,
)
from app.infrastructure.models.scene import SceneReferenceRecord
from app.infrastructure.models.shot import ShotRecord, ShotReferenceRecord
from app.repository.keyframe_task_repository import KeyframeTaskRepository
from app.service.keyframe_prompt_template_service import KeyframePromptTemplateService
from app.service.keyframe_task_readiness_service import KeyframeTaskReadinessService, ensure_utc
from app.service.keyframe_task_snapshot_builder import KeyframeTaskSnapshotBuilder

ERROR_MESSAGES: dict[KeyframeTaskErrorCode, str] = {
    KeyframeTaskErrorCode.PROJECT_NOT_FOUND: "项目不存在或已被删除。",
    KeyframeTaskErrorCode.SHOT_NOT_FOUND: "镜头不存在或已被删除。",
    KeyframeTaskErrorCode.TASK_NOT_FOUND: "关键帧任务不存在或已被删除。",
    KeyframeTaskErrorCode.TASK_REFERENCE_NOT_FOUND: "任务参考图不存在或已被删除。",
    KeyframeTaskErrorCode.SHOT_REFERENCE_NOT_FOUND: "当前镜头参考图不存在或已被移除。",
    KeyframeTaskErrorCode.NAME_REQUIRED: "请输入任务名称。",
    KeyframeTaskErrorCode.NAME_TOO_LONG: "任务名称不能超过 120 个字符。",
    KeyframeTaskErrorCode.INVALID_STATUS: "任务状态无效。",
    KeyframeTaskErrorCode.INVALID_ASPECT_RATIO: "图片比例无效。",
    KeyframeTaskErrorCode.INVALID_DIMENSIONS: "图片尺寸必须为 256 到 4096 之间且为 8 的倍数。",
    KeyframeTaskErrorCode.INVALID_STEPS: "推理步数必须在 1 到 150 之间。",
    KeyframeTaskErrorCode.INVALID_GUIDANCE: "引导强度必须在 0 到 30 之间。",
    KeyframeTaskErrorCode.INVALID_OUTPUT_COUNT: "输出数量必须在 1 到 8 之间。",
    KeyframeTaskErrorCode.INVALID_SEED: "随机种子必须为空、0 或正整数。",
    KeyframeTaskErrorCode.INVALID_REFERENCE_TYPE: "任务参考图类型无效。",
    KeyframeTaskErrorCode.INVALID_REFERENCE_PURPOSE: "任务参考图用途无效。",
    KeyframeTaskErrorCode.REFERENCE_ALREADY_EXISTS: "相同用途的任务参考图已经存在。",
    KeyframeTaskErrorCode.TASK_NOT_READY: "当前任务尚未满足准备完成条件。",
    KeyframeTaskErrorCode.MEDIA_IN_USE_BY_KEYFRAME_TASK: "无法删除：该媒体已被关键帧生成任务使用。",
    KeyframeTaskErrorCode.DATABASE_CONFLICT: "数据已被其他操作更新，请刷新后重试。",
}

HTTP_422 = 422


class KeyframeTaskService:
    def __init__(
        self,
        repository: KeyframeTaskRepository,
        snapshot_builder: KeyframeTaskSnapshotBuilder | None = None,
        prompt_service: KeyframePromptTemplateService | None = None,
        readiness_service: KeyframeTaskReadinessService | None = None,
    ) -> None:
        self.repository = repository
        self.snapshot_builder = snapshot_builder or KeyframeTaskSnapshotBuilder(repository)
        self.prompt_service = prompt_service or KeyframePromptTemplateService()
        self.readiness_service = readiness_service or KeyframeTaskReadinessService()

    def list_tasks(self, project_id: UUID, shot_id: UUID) -> KeyframeTaskListResponse:
        shot = self._get_shot(project_id, shot_id)
        data = self.repository.list_tasks(str(project_id), shot.id)
        media_assets = self._media_assets_for_references(
            [reference for refs in data.references_by_task_id.values() for reference in refs]
        )
        return KeyframeTaskListResponse(
            items=[
                self._task_response(
                    task,
                    data.references_by_task_id.get(task.id, []),
                    media_assets,
                    shot,
                )
                for task in data.tasks
            ],
            total=data.total,
        )

    def create_task(
        self, project_id: UUID, shot_id: UUID, payload: KeyframeTaskCreateRequest
    ) -> KeyframeTaskResponse:
        shot = self._get_shot(project_id, shot_id)
        snapshot = self.snapshot_builder.build(shot)
        now = utc_now()
        task = KeyframeGenerationTaskRecord(
            id=str(uuid4()),
            project_id=str(project_id),
            shot_id=shot.id,
            name=(
                self._normalize_name(payload.name)
                if payload.name is not None
                else self._default_name(shot)
            ),
            status=KeyframeTaskStatus.DRAFT.value,
            shot_snapshot=snapshot.model_dump_json(),
            source_shot_updated_at=ensure_utc(shot.updated_at),
            prompt_zh=self.prompt_service.build_prompt_zh(snapshot),
            prompt_en=None,
            negative_prompt=self.prompt_service.default_negative_prompt(),
            aspect_ratio=DEFAULT_ASPECT_RATIO.value,
            width=DEFAULT_WIDTH,
            height=DEFAULT_HEIGHT,
            seed=None,
            steps=DEFAULT_STEPS,
            guidance_scale=DEFAULT_GUIDANCE_SCALE,
            sampler_name=None,
            scheduler_name=None,
            model_provider=None,
            model_name=None,
            model_version=None,
            output_count=DEFAULT_OUTPUT_COUNT,
            created_at=now,
            updated_at=now,
        )
        references = (
            self._copy_current_shot_references(task.id, shot.id, now)
            if payload.copy_current_references
            else []
        )
        try:
            created = self.repository.create_task(task, references)
        except SQLAlchemyError:
            raise_keyframe_error(KeyframeTaskErrorCode.DATABASE_CONFLICT, status.HTTP_409_CONFLICT)
        return self._task_response(
            created,
            self.repository.list_references(created.id),
            self._media_assets_for_references(references),
            shot,
        )

    def get_task(self, project_id: UUID, task_id: UUID) -> KeyframeTaskResponse:
        task = self._get_task(project_id, task_id)
        references = self.repository.list_references(task.id)
        return self._task_response(
            task,
            references,
            self._media_assets_for_references(references),
            self.repository.get_shot(task.project_id, task.shot_id),
        )

    def update_task(
        self, project_id: UUID, task_id: UUID, payload: KeyframeTaskUpdateRequest
    ) -> KeyframeTaskResponse:
        task = self._get_task(project_id, task_id)
        submitted = payload.model_dump(exclude_unset=True)
        values = self._normalize_task_update_values(task, submitted)
        changed = any(getattr(task, key) != value for key, value in values.items())
        if not changed:
            return self.get_task(project_id, task_id)
        values["updated_at"] = utc_now()
        if task.status == KeyframeTaskStatus.READY.value:
            values["status"] = KeyframeTaskStatus.DRAFT.value
        try:
            updated = self.repository.update_task(task, values)
        except SQLAlchemyError:
            raise_keyframe_error(KeyframeTaskErrorCode.DATABASE_CONFLICT, status.HTTP_409_CONFLICT)
        references = self.repository.list_references(updated.id)
        return self._task_response(
            updated,
            references,
            self._media_assets_for_references(references),
            self.repository.get_shot(updated.project_id, updated.shot_id),
        )

    def delete_task(self, project_id: UUID, task_id: UUID) -> None:
        task = self._get_task(project_id, task_id)
        self.repository.delete_task(task)

    def duplicate_task(self, project_id: UUID, task_id: UUID) -> KeyframeTaskResponse:
        source = self._get_task(project_id, task_id)
        source_references = self.repository.list_references(source.id)
        now = utc_now()
        duplicate = KeyframeGenerationTaskRecord(
            id=str(uuid4()),
            project_id=source.project_id,
            shot_id=source.shot_id,
            name=f"{source.name} - 副本",
            status=KeyframeTaskStatus.DRAFT.value,
            shot_snapshot=source.shot_snapshot,
            source_shot_updated_at=source.source_shot_updated_at,
            prompt_zh=source.prompt_zh,
            prompt_en=source.prompt_en,
            negative_prompt=source.negative_prompt,
            aspect_ratio=source.aspect_ratio,
            width=source.width,
            height=source.height,
            seed=source.seed,
            steps=source.steps,
            guidance_scale=source.guidance_scale,
            sampler_name=source.sampler_name,
            scheduler_name=source.scheduler_name,
            model_provider=source.model_provider,
            model_name=source.model_name,
            model_version=source.model_version,
            output_count=source.output_count,
            created_at=now,
            updated_at=now,
        )
        duplicate_references = [
            KeyframeGenerationTaskReferenceRecord(
                id=str(uuid4()),
                task_id=duplicate.id,
                reference_type=reference.reference_type,
                shot_reference_id=reference.shot_reference_id,
                character_reference_id=reference.character_reference_id,
                scene_reference_id=reference.scene_reference_id,
                media_asset_id=reference.media_asset_id,
                purpose=reference.purpose,
                order_index=reference.order_index,
                source_shot_character_id=reference.source_shot_character_id,
                source_character_id=reference.source_character_id,
                source_look_id=reference.source_look_id,
                source_scene_id=reference.source_scene_id,
                source_scene_state_id=reference.source_scene_state_id,
                created_at=now,
            )
            for reference in source_references
        ]
        try:
            created = self.repository.duplicate_task(duplicate, duplicate_references)
        except SQLAlchemyError:
            raise_keyframe_error(KeyframeTaskErrorCode.DATABASE_CONFLICT, status.HTTP_409_CONFLICT)
        return self._task_response(
            created,
            duplicate_references,
            self._media_assets_for_references(duplicate_references),
            self.repository.get_shot(created.project_id, created.shot_id),
        )

    def mark_ready(self, project_id: UUID, task_id: UUID) -> KeyframeTaskResponse:
        task = self._get_task(project_id, task_id)
        references = self.repository.list_references(task.id)
        current_shot = self.repository.get_shot(task.project_id, task.shot_id)
        readiness = self._calculate_readiness(task, references, current_shot)
        if readiness.readiness_status != KeyframeTaskReadinessStatus.READY:
            raise AppError(
                code=KeyframeTaskErrorCode.TASK_NOT_READY.value,
                message=ERROR_MESSAGES[KeyframeTaskErrorCode.TASK_NOT_READY],
                status_code=status.HTTP_400_BAD_REQUEST,
                details=readiness.model_dump(mode="json"),
            )
        if task.status != KeyframeTaskStatus.READY.value:
            task = self.repository.update_task(
                task,
                {"status": KeyframeTaskStatus.READY.value, "updated_at": utc_now()},
            )
        return self._task_response(
            task,
            references,
            self._media_assets_for_references(references),
            current_shot,
        )

    def mark_draft(self, project_id: UUID, task_id: UUID) -> KeyframeTaskResponse:
        task = self._get_task(project_id, task_id)
        if task.status != KeyframeTaskStatus.DRAFT.value:
            task = self.repository.update_task(
                task,
                {"status": KeyframeTaskStatus.DRAFT.value, "updated_at": utc_now()},
            )
        references = self.repository.list_references(task.id)
        return self._task_response(
            task,
            references,
            self._media_assets_for_references(references),
            self.repository.get_shot(task.project_id, task.shot_id),
        )

    def list_references(self, project_id: UUID, task_id: UUID) -> KeyframeTaskReferenceListResponse:
        task = self._get_task(project_id, task_id)
        references = self.repository.list_references(task.id)
        media_assets = self._media_assets_for_references(references)
        return KeyframeTaskReferenceListResponse(
            items=[self._reference_response(reference, media_assets) for reference in references],
            total=len(references),
        )

    def add_reference(
        self,
        project_id: UUID,
        task_id: UUID,
        payload: KeyframeTaskReferenceCreateRequest,
    ) -> KeyframeTaskResponse:
        task = self._get_task(project_id, task_id)
        shot = self.repository.get_shot(task.project_id, task.shot_id)
        if shot is None:
            raise_keyframe_error(KeyframeTaskErrorCode.SHOT_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        shot_reference = self.repository.get_shot_reference(shot.id, payload.shot_reference_id)
        if shot_reference is None:
            raise_keyframe_error(
                KeyframeTaskErrorCode.SHOT_REFERENCE_NOT_FOUND, status.HTTP_404_NOT_FOUND
            )
        reference = self._task_reference_from_shot_reference(
            task.id,
            shot_reference,
            self._next_reference_order(task.id),
            utc_now(),
            payload.purpose,
        )
        self._ensure_reference_not_duplicate(task.id, reference)
        if task.status == KeyframeTaskStatus.READY.value:
            task.status = KeyframeTaskStatus.DRAFT.value
            task.updated_at = utc_now()
        try:
            self.repository.create_reference(task, reference)
        except SQLAlchemyError:
            raise_keyframe_error(KeyframeTaskErrorCode.DATABASE_CONFLICT, status.HTTP_409_CONFLICT)
        return self.get_task(project_id, task_id)

    def update_reference(
        self,
        project_id: UUID,
        task_id: UUID,
        reference_id: UUID,
        payload: KeyframeTaskReferenceUpdateRequest,
    ) -> KeyframeTaskResponse:
        task = self._get_task(project_id, task_id)
        reference = self._get_reference(task.id, reference_id)
        submitted = payload.model_dump(exclude_unset=True)
        values: dict[str, object] = {}
        if "purpose" in submitted and submitted["purpose"] is not None:
            next_purpose = self._validate_purpose(reference.reference_type, submitted["purpose"])
            values["purpose"] = next_purpose
        next_order = submitted.get("order_index")
        changed = any(getattr(reference, key) != value for key, value in values.items())
        if next_order is not None and next_order != reference.order_index:
            changed = True
        if not changed:
            return self.get_task(project_id, task_id)
        self._ensure_reference_not_duplicate(
            task.id,
            reference,
            next_purpose=str(values.get("purpose", reference.purpose)),
            ignore_reference_id=reference.id,
        )
        if task.status == KeyframeTaskStatus.READY.value:
            task.status = KeyframeTaskStatus.DRAFT.value
            task.updated_at = utc_now()
        try:
            self.repository.update_reference(task, reference, values, next_order)
        except SQLAlchemyError:
            raise_keyframe_error(KeyframeTaskErrorCode.DATABASE_CONFLICT, status.HTTP_409_CONFLICT)
        return self.get_task(project_id, task_id)

    def delete_reference(self, project_id: UUID, task_id: UUID, reference_id: UUID) -> None:
        task = self._get_task(project_id, task_id)
        reference = self._get_reference(task.id, reference_id)
        if task.status == KeyframeTaskStatus.READY.value:
            task.status = KeyframeTaskStatus.DRAFT.value
            task.updated_at = utc_now()
        self.repository.delete_reference(task, reference)

    def _copy_current_shot_references(
        self, task_id: str, shot_id: str, now: datetime
    ) -> list[KeyframeGenerationTaskReferenceRecord]:
        records: list[KeyframeGenerationTaskReferenceRecord] = []
        shot_references = self.repository.list_shot_references(shot_id)
        for order, shot_reference in enumerate(shot_references, start=1):
            records.append(
                self._task_reference_from_shot_reference(
                    task_id,
                    shot_reference,
                    order,
                    now,
                    purpose_override=None,
                )
            )
        return records

    def _task_reference_from_shot_reference(
        self,
        task_id: str,
        shot_reference: ShotReferenceRecord,
        order_index: int,
        now: datetime,
        purpose_override: str | None,
    ) -> KeyframeGenerationTaskReferenceRecord:
        purpose = self._validate_purpose(
            shot_reference.reference_type,
            purpose_override or shot_reference.purpose,
        )
        if shot_reference.reference_type == KeyframeTaskReferenceType.CHARACTER.value:
            source = self._get_character_reference_source(shot_reference)
            return KeyframeGenerationTaskReferenceRecord(
                id=str(uuid4()),
                task_id=task_id,
                reference_type=KeyframeTaskReferenceType.CHARACTER.value,
                shot_reference_id=shot_reference.id,
                character_reference_id=source.id,
                scene_reference_id=None,
                media_asset_id=source.media_asset_id,
                purpose=purpose,
                order_index=order_index,
                source_shot_character_id=shot_reference.shot_character_id,
                source_character_id=source.look.character_id,
                source_look_id=source.look_id,
                source_scene_id=None,
                source_scene_state_id=None,
                created_at=now,
            )
        if shot_reference.reference_type == KeyframeTaskReferenceType.SCENE.value:
            source_scene = self._get_scene_reference_source(shot_reference)
            return KeyframeGenerationTaskReferenceRecord(
                id=str(uuid4()),
                task_id=task_id,
                reference_type=KeyframeTaskReferenceType.SCENE.value,
                shot_reference_id=shot_reference.id,
                character_reference_id=None,
                scene_reference_id=source_scene.id,
                media_asset_id=source_scene.media_asset_id,
                purpose=purpose,
                order_index=order_index,
                source_shot_character_id=None,
                source_character_id=None,
                source_look_id=None,
                source_scene_id=source_scene.state.scene_id,
                source_scene_state_id=source_scene.state_id,
                created_at=now,
            )
        raise_keyframe_error(KeyframeTaskErrorCode.INVALID_REFERENCE_TYPE, HTTP_422)

    def _get_character_reference_source(
        self, shot_reference: ShotReferenceRecord
    ) -> CharacterReferenceRecord:
        source_id = shot_reference.character_reference_id
        source = self.repository.get_character_references_by_ids(
            [source_id] if source_id else []
        ).get(source_id or "")
        if source is None:
            raise_keyframe_error(
                KeyframeTaskErrorCode.SHOT_REFERENCE_NOT_FOUND, status.HTTP_404_NOT_FOUND
            )
        return source

    def _get_scene_reference_source(
        self, shot_reference: ShotReferenceRecord
    ) -> SceneReferenceRecord:
        source_id = shot_reference.scene_reference_id
        source = self.repository.get_scene_references_by_ids([source_id] if source_id else []).get(
            source_id or ""
        )
        if source is None:
            raise_keyframe_error(
                KeyframeTaskErrorCode.SHOT_REFERENCE_NOT_FOUND, status.HTTP_404_NOT_FOUND
            )
        return source

    def _task_response(
        self,
        task: KeyframeGenerationTaskRecord,
        references: list[KeyframeGenerationTaskReferenceRecord],
        media_assets: dict[str, MediaAssetRecord],
        current_shot: ShotRecord | None,
    ) -> KeyframeTaskResponse:
        snapshot = self._snapshot_from_task(task)
        readiness = self.readiness_service.calculate(
            task,
            snapshot,
            references,
            media_assets,
            current_shot,
        )
        return KeyframeTaskResponse(
            id=task.id,
            project_id=task.project_id,
            shot_id=task.shot_id,
            name=task.name,
            status=KeyframeTaskStatus(task.status),
            shot_snapshot=snapshot,
            source_shot_updated_at=ensure_utc(task.source_shot_updated_at),
            prompt_zh=task.prompt_zh,
            prompt_en=task.prompt_en,
            negative_prompt=task.negative_prompt,
            aspect_ratio=KeyframeTaskAspectRatio(task.aspect_ratio),
            width=task.width,
            height=task.height,
            seed=task.seed,
            steps=task.steps,
            guidance_scale=task.guidance_scale,
            sampler_name=task.sampler_name,
            scheduler_name=task.scheduler_name,
            model_provider=task.model_provider,
            model_name=task.model_name,
            model_version=task.model_version,
            output_count=task.output_count,
            readiness=readiness,
            shot_changed_since_snapshot=self.readiness_service.shot_changed_since_snapshot(
                task, current_shot
            ),
            references=[
                self._reference_response(reference, media_assets) for reference in references
            ],
            reference_count=len(references),
            created_at=ensure_utc(task.created_at),
            updated_at=ensure_utc(task.updated_at),
        )

    def _reference_response(
        self,
        reference: KeyframeGenerationTaskReferenceRecord,
        media_assets: dict[str, MediaAssetRecord],
    ) -> KeyframeTaskReferenceResponse:
        return KeyframeTaskReferenceResponse(
            id=reference.id,
            task_id=reference.task_id,
            reference_type=KeyframeTaskReferenceType(reference.reference_type),
            shot_reference_id=reference.shot_reference_id,
            character_reference_id=reference.character_reference_id,
            scene_reference_id=reference.scene_reference_id,
            media_asset_id=reference.media_asset_id,
            purpose=reference.purpose,
            order_index=reference.order_index,
            source_shot_character_id=reference.source_shot_character_id,
            source_character_id=reference.source_character_id,
            source_look_id=reference.source_look_id,
            source_scene_id=reference.source_scene_id,
            source_scene_state_id=reference.source_scene_state_id,
            source_reference_deleted=(
                reference.character_reference_id is None
                if reference.reference_type == KeyframeTaskReferenceType.CHARACTER.value
                else reference.scene_reference_id is None
            ),
            media_asset=self._media_asset_response(media_assets.get(reference.media_asset_id)),
            created_at=ensure_utc(reference.created_at),
        )

    @staticmethod
    def _media_asset_response(media_asset: MediaAssetRecord | None) -> MediaAssetResponse | None:
        if media_asset is None:
            return None
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

    def _calculate_readiness(
        self,
        task: KeyframeGenerationTaskRecord,
        references: list[KeyframeGenerationTaskReferenceRecord],
        current_shot: ShotRecord | None,
    ):
        return self.readiness_service.calculate(
            task,
            self._snapshot_from_task(task),
            references,
            self._media_assets_for_references(references),
            current_shot,
        )

    def _media_assets_for_references(
        self, references: list[KeyframeGenerationTaskReferenceRecord]
    ) -> dict[str, MediaAssetRecord]:
        return self.repository.get_media_assets_by_ids(
            sorted({reference.media_asset_id for reference in references})
        )

    @staticmethod
    def _snapshot_from_task(task: KeyframeGenerationTaskRecord) -> KeyframeShotSnapshot:
        return KeyframeShotSnapshot.model_validate_json(task.shot_snapshot)

    def _normalize_task_update_values(
        self, task: KeyframeGenerationTaskRecord, submitted: dict[str, object]
    ) -> dict[str, object]:
        values: dict[str, object] = {}
        if "name" in submitted:
            values["name"] = self._normalize_name(submitted["name"])
        for key, max_length in {
            "prompt_zh": 8000,
            "prompt_en": 8000,
            "negative_prompt": 4000,
            "sampler_name": 120,
            "scheduler_name": 120,
            "model_provider": 120,
            "model_name": 200,
            "model_version": 120,
        }.items():
            if key in submitted:
                values[key] = self._optional(submitted[key], max_length)
        if "aspect_ratio" in submitted and submitted["aspect_ratio"] is not None:
            aspect_ratio = KeyframeTaskAspectRatio(str(submitted["aspect_ratio"]))
            values["aspect_ratio"] = aspect_ratio.value
            if aspect_ratio != KeyframeTaskAspectRatio.CUSTOM and (
                "width" not in submitted and "height" not in submitted
            ):
                width, height = ASPECT_RATIO_DIMENSIONS[aspect_ratio]
                values["width"] = width
                values["height"] = height
        for key in ("width", "height", "seed", "steps", "guidance_scale", "output_count"):
            if key in submitted:
                if key != "seed" and submitted[key] is None:
                    raise_keyframe_error(self._numeric_error_code(key), HTTP_422)
                values[key] = submitted[key]
        self._validate_dimensions(
            KeyframeTaskAspectRatio(values.get("aspect_ratio", task.aspect_ratio)),
            int(values.get("width", task.width)),
            int(values.get("height", task.height)),
            allow_mismatch=True,
        )
        return values

    @staticmethod
    def _validate_dimensions(
        aspect_ratio: KeyframeTaskAspectRatio,
        width: int,
        height: int,
        allow_mismatch: bool,
    ) -> None:
        if not 256 <= width <= 4096 or width % 8 != 0:
            raise_keyframe_error(KeyframeTaskErrorCode.INVALID_DIMENSIONS, HTTP_422)
        if not 256 <= height <= 4096 or height % 8 != 0:
            raise_keyframe_error(KeyframeTaskErrorCode.INVALID_DIMENSIONS, HTTP_422)
        if not allow_mismatch and not aspect_ratio_matches(aspect_ratio, width, height):
            raise_keyframe_error(KeyframeTaskErrorCode.INVALID_DIMENSIONS, HTTP_422)

    def _ensure_reference_not_duplicate(
        self,
        task_id: str,
        reference: KeyframeGenerationTaskReferenceRecord,
        next_purpose: str | None = None,
        ignore_reference_id: str | None = None,
    ) -> None:
        duplicate = self.repository.find_duplicate_reference(
            task_id,
            reference.reference_type,
            reference.character_reference_id,
            reference.scene_reference_id,
            next_purpose or reference.purpose,
            reference.source_shot_character_id,
        )
        if duplicate is not None and duplicate.id != ignore_reference_id:
            raise_keyframe_error(
                KeyframeTaskErrorCode.REFERENCE_ALREADY_EXISTS,
                status.HTTP_409_CONFLICT,
            )

    def _next_reference_order(self, task_id: str) -> int:
        return len(self.repository.list_references(task_id)) + 1

    def _get_shot(self, project_id: UUID, shot_id: UUID) -> ShotRecord:
        shot = self.repository.get_shot(str(project_id), str(shot_id))
        if shot is None:
            if not self.repository.project_exists(str(project_id)):
                raise_keyframe_error(
                    KeyframeTaskErrorCode.PROJECT_NOT_FOUND, status.HTTP_404_NOT_FOUND
                )
            raise_keyframe_error(KeyframeTaskErrorCode.SHOT_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        return shot

    def _get_task(self, project_id: UUID, task_id: UUID) -> KeyframeGenerationTaskRecord:
        task = self.repository.get_task(str(project_id), str(task_id))
        if task is None:
            if not self.repository.project_exists(str(project_id)):
                raise_keyframe_error(
                    KeyframeTaskErrorCode.PROJECT_NOT_FOUND, status.HTTP_404_NOT_FOUND
                )
            raise_keyframe_error(KeyframeTaskErrorCode.TASK_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        return task

    def _get_reference(
        self, task_id: str, reference_id: UUID
    ) -> KeyframeGenerationTaskReferenceRecord:
        reference = self.repository.get_reference(task_id, str(reference_id))
        if reference is None:
            raise_keyframe_error(
                KeyframeTaskErrorCode.TASK_REFERENCE_NOT_FOUND,
                status.HTTP_404_NOT_FOUND,
            )
        return reference

    @staticmethod
    def _validate_purpose(reference_type: str, value: str) -> str:
        if reference_type == KeyframeTaskReferenceType.CHARACTER.value:
            try:
                return CharacterReferencePurpose(value).value
            except ValueError:
                raise_keyframe_error(KeyframeTaskErrorCode.INVALID_REFERENCE_PURPOSE, HTTP_422)
        if reference_type == KeyframeTaskReferenceType.SCENE.value:
            try:
                return SceneReferencePurpose(value).value
            except ValueError:
                raise_keyframe_error(KeyframeTaskErrorCode.INVALID_REFERENCE_PURPOSE, HTTP_422)
        raise_keyframe_error(KeyframeTaskErrorCode.INVALID_REFERENCE_TYPE, HTTP_422)

    @staticmethod
    def _normalize_name(value: object) -> str:
        try:
            return normalize_required_text(
                value if isinstance(value, str) else None,
                KeyframeTaskErrorCode.NAME_REQUIRED,
                KeyframeTaskErrorCode.NAME_TOO_LONG,
                120,
            )
        except ValueError as exc:
            code = exc.args[0] if exc.args else KeyframeTaskErrorCode.NAME_REQUIRED
            raise_keyframe_error(KeyframeTaskErrorCode(code), HTTP_422)

    @staticmethod
    def _optional(value: object, max_length: int) -> str | None:
        try:
            return normalize_optional_text(value if isinstance(value, str) else None, max_length)
        except ValueError:
            raise_keyframe_error(KeyframeTaskErrorCode.NAME_TOO_LONG, HTTP_422)

    @staticmethod
    def _default_name(shot: ShotRecord) -> str:
        return f"镜头 {shot.order_index:02d} - {shot.name}"

    @staticmethod
    def _numeric_error_code(key: str) -> KeyframeTaskErrorCode:
        return {
            "width": KeyframeTaskErrorCode.INVALID_DIMENSIONS,
            "height": KeyframeTaskErrorCode.INVALID_DIMENSIONS,
            "steps": KeyframeTaskErrorCode.INVALID_STEPS,
            "guidance_scale": KeyframeTaskErrorCode.INVALID_GUIDANCE,
            "output_count": KeyframeTaskErrorCode.INVALID_OUTPUT_COUNT,
        }[key]


def utc_now() -> datetime:
    return datetime.now(UTC)


def raise_keyframe_error(code: KeyframeTaskErrorCode, http_status: int) -> None:
    raise AppError(code=code.value, message=ERROR_MESSAGES[code], status_code=http_status)
