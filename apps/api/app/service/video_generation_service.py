from datetime import UTC, datetime
from random import SystemRandom
from uuid import UUID, uuid4

from fastapi import UploadFile, status
from sqlalchemy.exc import SQLAlchemyError

from app.api.schemas.character import MediaAssetResponse
from app.api.schemas.video_generation import (
    VideoInputUploadResponse,
    VideoOutputResponse,
    VideoRunCreateResponse,
    VideoRunInputSnapshot,
    VideoRunListResponse,
    VideoRunResponse,
    VideoRunSnapshot,
    VideoTaskCreateRequest,
    VideoTaskInputRequest,
    VideoTaskInputResponse,
    VideoTaskListResponse,
    VideoTaskResponse,
    VideoTaskUpdateRequest,
    VideoWorkflowListResponse,
    VideoWorkflowResponse,
)
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.domain.media_asset import MediaType
from app.domain.video_generation import (
    VIDEO_GENERATION_ERROR_MESSAGES,
    VIDEO_INPUT_ROLE_ORDER,
    VideoGenerationErrorCode,
    VideoGenerationRunStatus,
    VideoGenerationTaskStatus,
    VideoInputRole,
    VideoTaskReadinessStatus,
    VideoWorkflowMode,
)
from app.infrastructure.generation.base import GenerationProviderRuntimeError
from app.infrastructure.generation.factory import create_video_generation_provider
from app.infrastructure.generation.video_workflow import (
    LoadedVideoWorkflow,
    VideoWorkflowMappingValues,
    VideoWorkflowRegistry,
)
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.video_generation import (
    VideoGenerationOutputRecord,
    VideoGenerationRunRecord,
    VideoGenerationTaskInputRecord,
    VideoGenerationTaskRecord,
)
from app.repository.video_generation_repository import VideoGenerationRepository
from app.service.media_storage_service import MediaStorageService, StoredImage, StoredVideo
from app.service.video_generation_readiness_service import (
    VideoGenerationReadinessService,
    ensure_utc,
)

MAX_COMFYUI_SEED = 2**32 - 1
MODEL_LOADER_INPUTS: dict[str, tuple[str, ...]] = {
    "CheckpointLoaderSimple": ("ckpt_name",),
    "CLIPLoader": ("clip_name",),
    "CLIPVisionLoader": ("clip_name", "clip_vision_name"),
    "UNETLoader": ("unet_name",),
    "VAELoader": ("vae_name",),
}


class VideoGenerationService:
    def __init__(
        self,
        repository: VideoGenerationRepository,
        settings: Settings | None = None,
        workflow_registry: VideoWorkflowRegistry | None = None,
        readiness_service: VideoGenerationReadinessService | None = None,
        storage_service: MediaStorageService | None = None,
    ) -> None:
        self.repository = repository
        self.settings = settings or get_settings()
        self.workflow_registry = workflow_registry or VideoWorkflowRegistry(self.settings)
        self.readiness_service = readiness_service or VideoGenerationReadinessService()
        self.storage_service = storage_service or MediaStorageService()

    async def list_workflows(self, project_id: UUID) -> VideoWorkflowListResponse:
        self._ensure_project_exists(project_id)
        provider_available, node_types, object_info = await self._provider_availability()
        workflows = self.workflow_registry.list_workflows()
        items = [
            VideoWorkflowResponse(
                workflow_id=workflow.manifest.workflow_id,
                display_name=workflow.manifest.display_name,
                version=workflow.manifest.version,
                mode=workflow.manifest.mode,
                required_input_roles=workflow.manifest.required_input_roles,
                available=not self._workflow_missing_requirements(
                    workflow,
                    provider_available=provider_available,
                    node_types=node_types,
                    object_info=object_info,
                ),
                missing_requirements=self._workflow_missing_requirements(
                    workflow,
                    provider_available=provider_available,
                    node_types=node_types,
                    object_info=object_info,
                ),
                reference_inputs_used=True,
            )
            for workflow in workflows
        ]
        return VideoWorkflowListResponse(items=items, total=len(items))

    def list_tasks(self, project_id: UUID, shot_id: UUID) -> VideoTaskListResponse:
        self._get_shot(project_id, shot_id)
        data = self.repository.list_tasks_for_shot(str(project_id), str(shot_id))
        return VideoTaskListResponse(
            items=[
                self._task_response(
                    task,
                    data.media_assets_by_id.get(task.input_media_asset_id or ""),
                    data.input_records_by_task_id.get(task.id, []),
                    data.input_media_assets_by_id,
                    data.latest_run_status_by_task_id.get(task.id),
                    data.selected_outputs_by_task_id.get(task.id),
                    data.selected_media_assets_by_id,
                )
                for task in data.tasks
            ],
            total=data.total,
        )

    def create_task(
        self,
        project_id: UUID,
        shot_id: UUID,
        payload: VideoTaskCreateRequest,
    ) -> VideoTaskResponse:
        self._get_shot(project_id, shot_id)
        now = utc_now()
        workflow_id = self._default_workflow_id()
        task_id = str(uuid4())
        inputs = self._input_records_from_create_payload(project_id, task_id, payload, now)
        start_input = _input_by_role(inputs, VideoInputRole.START_FRAME)
        task = VideoGenerationTaskRecord(
            id=task_id,
            project_id=str(project_id),
            shot_id=str(shot_id),
            name="视频生成任务",
            status=VideoGenerationTaskStatus.DRAFT.value,
            input_media_asset_id=start_input.media_asset_id if start_input else None,
            source_keyframe_output_id=(
                start_input.source_keyframe_output_id
                if start_input
                else payload.source_keyframe_output_id
            ),
            source_keyframe_task_id=(
                start_input.source_keyframe_task_id
                if start_input
                else payload.source_keyframe_task_id
            ),
            prompt=None,
            negative_prompt=None,
            duration_seconds=5.0,
            fps=16,
            width=768,
            height=1360,
            seed=None,
            motion_strength=None,
            camera_motion=None,
            workflow_id=workflow_id,
            created_at=now,
            updated_at=now,
        )
        try:
            created = self.repository.create_task_with_inputs(task, inputs)
        except SQLAlchemyError:
            raise_video_error(VideoGenerationErrorCode.DATABASE_CONFLICT, status.HTTP_409_CONFLICT)
        media_asset = (
            self.repository.get_media_asset(str(project_id), created.input_media_asset_id)
            if created.input_media_asset_id
            else None
        )
        input_assets = self.repository.get_media_assets_by_ids(
            sorted({record.media_asset_id for record in inputs if record.media_asset_id})
        )
        return self._task_response(created, media_asset, inputs, input_assets, None, None, {})

    def get_task(self, project_id: UUID, task_id: UUID) -> VideoTaskResponse:
        task = self._get_task(project_id, task_id)
        media_asset = (
            self.repository.get_media_asset(str(project_id), task.input_media_asset_id)
            if task.input_media_asset_id
            else None
        )
        input_records = self.repository.list_inputs_for_task(task.id)
        input_assets = self.repository.get_media_assets_by_ids(
            sorted({record.media_asset_id for record in input_records if record.media_asset_id})
        )
        return self._task_response(task, media_asset, input_records, input_assets, None, None, {})

    def update_task(
        self,
        project_id: UUID,
        task_id: UUID,
        payload: VideoTaskUpdateRequest,
    ) -> VideoTaskResponse:
        task = self._get_task(project_id, task_id)
        values = self._update_values(payload)
        replace_inputs = "inputs" in payload.model_fields_set
        input_records: list[VideoGenerationTaskInputRecord] | None = None
        if replace_inputs:
            input_records = self._input_records_from_requests(
                project_id,
                task.id,
                payload.inputs or [],
                utc_now(),
            )
            start_input = _input_by_role(input_records, VideoInputRole.START_FRAME)
            values["input_media_asset_id"] = start_input.media_asset_id if start_input else None
            values["source_keyframe_output_id"] = (
                start_input.source_keyframe_output_id if start_input else None
            )
            values["source_keyframe_task_id"] = (
                start_input.source_keyframe_task_id if start_input else None
            )
        else:
            legacy_input_changed = False
            if "source_keyframe_output_id" in values and values.get("source_keyframe_output_id"):
                media_asset = self.repository.get_keyframe_output_media_asset(
                    str(project_id),
                    str(values["source_keyframe_output_id"]),
                )
                if media_asset is None:
                    raise_video_error(
                        VideoGenerationErrorCode.VIDEO_INPUT_IMAGE_UNAVAILABLE,
                        status.HTTP_404_NOT_FOUND,
                    )
                self._ensure_image_media_asset(media_asset)
                values["input_media_asset_id"] = media_asset.id
                legacy_input_changed = True
            if "input_media_asset_id" in values:
                legacy_input_changed = True
                if values.get("input_media_asset_id"):
                    media_asset = self.repository.get_media_asset(
                        str(project_id),
                        str(values["input_media_asset_id"]),
                    )
                    if media_asset is None:
                        raise_video_error(
                            VideoGenerationErrorCode.VIDEO_INPUT_IMAGE_UNAVAILABLE,
                            status.HTTP_404_NOT_FOUND,
                        )
                    self._ensure_image_media_asset(media_asset)
            if legacy_input_changed:
                input_records = self._legacy_start_input_records(task, values, utc_now())
        values["status"] = VideoGenerationTaskStatus.DRAFT.value
        values["updated_at"] = utc_now()
        try:
            if input_records is not None:
                updated = self.repository.update_task_with_inputs(task, values, input_records)
            else:
                updated = self.repository.update_task(task, values)
        except SQLAlchemyError:
            raise_video_error(VideoGenerationErrorCode.DATABASE_CONFLICT, status.HTTP_409_CONFLICT)
        media_asset = (
            self.repository.get_media_asset(str(project_id), updated.input_media_asset_id)
            if updated.input_media_asset_id
            else None
        )
        stored_inputs = self.repository.list_inputs_for_task(updated.id)
        input_assets = self.repository.get_media_assets_by_ids(
            sorted({record.media_asset_id for record in stored_inputs if record.media_asset_id})
        )
        return self._task_response(
            updated, media_asset, stored_inputs, input_assets, None, None, {}
        )

    def delete_task(self, project_id: UUID, task_id: UUID) -> None:
        task = self._get_task(project_id, task_id)
        try:
            self.repository.delete_task(task)
        except SQLAlchemyError:
            raise_video_error(VideoGenerationErrorCode.DATABASE_CONFLICT, status.HTTP_409_CONFLICT)

    async def mark_ready(self, project_id: UUID, task_id: UUID) -> VideoTaskResponse:
        task = self._get_task(project_id, task_id)
        media_asset = (
            self.repository.get_media_asset(str(project_id), task.input_media_asset_id)
            if task.input_media_asset_id
            else None
        )
        input_records = self.repository.list_inputs_for_task(task.id)
        input_assets = self.repository.get_media_assets_by_ids(
            sorted({record.media_asset_id for record in input_records if record.media_asset_id})
        )
        workflow = (
            self.workflow_registry.get_workflow(task.workflow_id) if task.workflow_id else None
        )
        if workflow is not None and workflow.available_locally:
            provider_available, node_types, object_info = await self._provider_availability(
                raise_when_offline=True
            )
            missing = self._workflow_missing_requirements(
                workflow,
                provider_available=provider_available,
                node_types=node_types,
                object_info=object_info,
            )
            if missing:
                raise_video_error(
                    VideoGenerationErrorCode.VIDEO_WORKFLOW_UNAVAILABLE,
                    status.HTTP_400_BAD_REQUEST,
                    details={"missing": missing},
                )
        readiness = self._readiness(task, media_asset, input_records, input_assets)
        if readiness.readiness_status != VideoTaskReadinessStatus.READY:
            raise AppError(
                code=VideoGenerationErrorCode.VIDEO_TASK_NOT_READY.value,
                message=VIDEO_GENERATION_ERROR_MESSAGES[
                    VideoGenerationErrorCode.VIDEO_TASK_NOT_READY.value
                ],
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                details=readiness.model_dump(mode="json"),
            )
        updated = self.repository.update_task(
            task,
            {"status": VideoGenerationTaskStatus.READY.value, "updated_at": utc_now()},
        )
        return self._task_response(
            updated, media_asset, input_records, input_assets, None, None, {}
        )

    def mark_draft(self, project_id: UUID, task_id: UUID) -> VideoTaskResponse:
        task = self._get_task(project_id, task_id)
        updated = self.repository.update_task(
            task,
            {"status": VideoGenerationTaskStatus.DRAFT.value, "updated_at": utc_now()},
        )
        media_asset = (
            self.repository.get_media_asset(str(project_id), updated.input_media_asset_id)
            if updated.input_media_asset_id
            else None
        )
        input_records = self.repository.list_inputs_for_task(updated.id)
        input_assets = self.repository.get_media_assets_by_ids(
            sorted({record.media_asset_id for record in input_records if record.media_asset_id})
        )
        return self._task_response(
            updated, media_asset, input_records, input_assets, None, None, {}
        )

    async def create_run(
        self,
        project_id: UUID,
        task_id: UUID,
        workflow_id: str,
    ) -> VideoRunCreateResponse:
        task = self._get_task(project_id, task_id)
        workflow = self.workflow_registry.get_workflow(workflow_id)
        if task.status != VideoGenerationTaskStatus.READY.value:
            raise_video_error(
                VideoGenerationErrorCode.VIDEO_TASK_NOT_READY,
                status.HTTP_400_BAD_REQUEST,
            )
        media_asset = (
            self.repository.get_media_asset(str(project_id), task.input_media_asset_id)
            if task.input_media_asset_id
            else None
        )
        input_records = self.repository.list_inputs_for_task(task.id)
        input_assets = self.repository.get_media_assets_by_ids(
            sorted({record.media_asset_id for record in input_records if record.media_asset_id})
        )
        readiness = self._readiness(
            task,
            media_asset,
            input_records,
            input_assets,
            forced_workflow=workflow,
        )
        if readiness.readiness_status != VideoTaskReadinessStatus.READY:
            raise AppError(
                code=VideoGenerationErrorCode.VIDEO_TASK_NOT_READY.value,
                message=VIDEO_GENERATION_ERROR_MESSAGES[
                    VideoGenerationErrorCode.VIDEO_TASK_NOT_READY.value
                ],
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                details=readiness.model_dump(mode="json"),
            )
        if self.repository.get_active_run_for_task(task.id) is not None:
            raise_video_error(
                VideoGenerationErrorCode.VIDEO_GENERATION_ALREADY_RUNNING,
                status.HTTP_409_CONFLICT,
            )
        provider_available, node_types, object_info = await self._provider_availability(
            raise_when_offline=True
        )
        missing = self._workflow_missing_requirements(
            workflow,
            provider_available=provider_available,
            node_types=node_types,
            object_info=object_info,
        )
        if missing:
            raise_video_error(
                VideoGenerationErrorCode.VIDEO_WORKFLOW_UNAVAILABLE,
                status.HTTP_400_BAD_REQUEST,
                details={"missing": missing},
            )
        snapshot = self._build_run_snapshot(task, workflow)
        now = utc_now()
        run = VideoGenerationRunRecord(
            id=str(uuid4()),
            project_id=task.project_id,
            video_task_id=task.id,
            run_number=self.repository.next_run_number(task.id),
            provider="comfyui",
            workflow_id=workflow.manifest.workflow_id,
            workflow_version=workflow.manifest.version,
            status=VideoGenerationRunStatus.QUEUED.value,
            provider_job_id=None,
            submitted_payload_snapshot=snapshot.model_dump_json(),
            error_code=None,
            error_message_safe=None,
            queued_at=now,
            started_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        try:
            created = self.repository.create_run(run)
        except SQLAlchemyError:
            raise_video_error(VideoGenerationErrorCode.DATABASE_CONFLICT, status.HTTP_409_CONFLICT)
        return VideoRunCreateResponse(
            run_id=created.id,
            status=VideoGenerationRunStatus(created.status),
        )

    def list_runs(self, project_id: UUID, task_id: UUID) -> VideoRunListResponse:
        task = self._get_task(project_id, task_id)
        data = self.repository.list_runs_for_task(task.project_id, task.id)
        return VideoRunListResponse(
            items=[
                self._run_response(
                    run,
                    data.outputs_by_run_id.get(run.id, []),
                    data.media_assets_by_id,
                )
                for run in data.runs
            ],
            total=data.total,
        )

    def get_run(self, project_id: UUID, run_id: UUID) -> VideoRunResponse:
        run = self._get_run(project_id, run_id)
        outputs = self.repository.list_outputs_for_runs([run.id]).get(run.id, [])
        media_assets = self.repository.get_media_assets_by_ids(
            sorted({output.media_asset_id for output in outputs})
        )
        return self._run_response(run, outputs, media_assets)

    def select_output(self, project_id: UUID, output_id: UUID) -> VideoOutputResponse:
        output = self._get_output(project_id, output_id)
        self.repository.select_output(output)
        media_asset = self.repository.media_asset_for_output(output)
        media_assets = {output.media_asset_id: media_asset} if media_asset else {}
        return self._output_response(output, media_assets)

    def unselect_output(self, project_id: UUID, output_id: UUID) -> VideoOutputResponse:
        output = self._get_output(project_id, output_id)
        self.repository.unselect_output(output)
        media_asset = self.repository.media_asset_for_output(output)
        media_assets = {output.media_asset_id: media_asset} if media_asset else {}
        return self._output_response(output, media_assets)

    async def upload_input_image(
        self, project_id: UUID, upload: UploadFile
    ) -> VideoInputUploadResponse:
        self._ensure_project_exists(project_id)
        stored = await self.storage_service.store_project_input_image(str(project_id), upload)
        now = utc_now()
        media_asset = media_record_from_stored_image(str(project_id), stored, now)
        try:
            created = self.repository.create_media_asset(media_asset)
        except SQLAlchemyError:
            self.storage_service.delete_relative_file_safely(stored.relative_path)
            self.storage_service.delete_relative_file_safely(stored.thumbnail_relative_path)
            raise_video_error(VideoGenerationErrorCode.DATABASE_CONFLICT, status.HTTP_409_CONFLICT)
        return VideoInputUploadResponse(media_asset=_media_asset_response(created))

    def build_provider_workflow(
        self,
        run: VideoGenerationRunRecord,
        uploaded_inputs: dict[VideoInputRole, object],
    ) -> dict[str, object]:
        snapshot = VideoRunSnapshot.model_validate_json(run.submitted_payload_snapshot)
        workflow = self.workflow_registry.get_workflow(snapshot.workflow_id)
        return self.workflow_registry.build_workflow(
            workflow,
            VideoWorkflowMappingValues(
                positive_prompt=snapshot.prompt,
                negative_prompt=snapshot.negative_prompt,
                width=snapshot.width,
                height=snapshot.height,
                duration_seconds=int(round(snapshot.duration_seconds)),
                fps=snapshot.fps,
                seed=snapshot.seed,
                motion_strength=snapshot.motion_strength,
                camera_motion=snapshot.camera_motion,
                input_images=uploaded_inputs,
            ),
        )

    def _build_run_snapshot(
        self,
        task: VideoGenerationTaskRecord,
        workflow: LoadedVideoWorkflow,
    ) -> VideoRunSnapshot:
        input_records = self.repository.list_inputs_for_task(task.id)
        input_assets = self.repository.get_media_assets_by_ids(
            sorted({record.media_asset_id for record in input_records if record.media_asset_id})
        )
        effective_inputs = self._effective_inputs(task, input_records, input_assets)
        snapshot_inputs: list[VideoRunInputSnapshot] = []
        for role in workflow.manifest.required_input_roles:
            task_input = effective_inputs.get(role)
            if task_input is None or not task_input.media_asset_id:
                raise_video_error(
                    VideoGenerationErrorCode.VIDEO_INPUT_IMAGE_MISSING,
                    status.HTTP_400_BAD_REQUEST,
                )
            snapshot_inputs.append(
                VideoRunInputSnapshot(role=role, media_asset_id=task_input.media_asset_id)
            )
        if not snapshot_inputs:
            raise_video_error(
                VideoGenerationErrorCode.VIDEO_INPUT_IMAGE_MISSING,
                status.HTTP_400_BAD_REQUEST,
            )
        prompt = _normalize_optional(task.prompt)
        if prompt is None:
            raise_video_error(
                VideoGenerationErrorCode.VIDEO_TASK_NOT_READY,
                status.HTTP_400_BAD_REQUEST,
            )
        seed = task.seed if task.seed is not None else SystemRandom().randint(0, MAX_COMFYUI_SEED)
        return VideoRunSnapshot(
            schema_version=2,
            video_task_id=task.id,
            shot_id=task.shot_id,
            workflow_id=workflow.manifest.workflow_id,
            workflow_version=workflow.manifest.version,
            workflow_mode=workflow.manifest.mode,
            input_media_asset_id=snapshot_inputs[0].media_asset_id,
            inputs=snapshot_inputs,
            prompt=prompt,
            negative_prompt=_normalize_optional(task.negative_prompt),
            duration_seconds=task.duration_seconds,
            fps=task.fps,
            width=task.width,
            height=task.height,
            seed=seed,
            motion_strength=task.motion_strength,
            camera_motion=_normalize_optional(task.camera_motion),
        )

    async def _provider_availability(
        self,
        *,
        raise_when_offline: bool = False,
    ) -> tuple[bool, set[str], dict[str, object]]:
        try:
            provider = create_video_generation_provider(self.settings)
        except GenerationProviderRuntimeError:
            if raise_when_offline:
                raise_video_error(
                    VideoGenerationErrorCode.VIDEO_PROVIDER_NOT_CONFIGURED,
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            return False, set(), {}
        health = await provider.check_health()
        if not health.available:
            if raise_when_offline:
                raise_video_error(
                    VideoGenerationErrorCode.VIDEO_COMFYUI_UNAVAILABLE,
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            return False, set(), {}
        try:
            object_info = await provider.get_object_info()
            return True, {str(key) for key in object_info}, object_info
        except GenerationProviderRuntimeError:
            if raise_when_offline:
                raise_video_error(
                    VideoGenerationErrorCode.VIDEO_COMFYUI_UNAVAILABLE,
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            return True, set(), {}

    def _workflow_missing_requirements(
        self,
        workflow: LoadedVideoWorkflow,
        *,
        provider_available: bool,
        node_types: set[str],
        object_info: dict[str, object] | None = None,
    ) -> list[str]:
        missing = list(workflow.missing_requirements)
        if not provider_available:
            missing.append("provider_offline")
        if provider_available and workflow.manifest.required_node_types:
            if not node_types:
                missing.append("required_node_types_unavailable")
            else:
                for node_type in workflow.manifest.required_node_types:
                    if node_type not in node_types:
                        missing.append(f"node_type_missing:{node_type}")
            missing.extend(_workflow_model_missing_requirements(workflow, object_info or {}))
        return sorted(set(missing))

    def _readiness(
        self,
        task: VideoGenerationTaskRecord,
        media_asset: MediaAssetRecord | None,
        input_records: list[VideoGenerationTaskInputRecord] | None = None,
        input_media_assets: dict[str, MediaAssetRecord] | None = None,
        *,
        forced_workflow: LoadedVideoWorkflow | None = None,
    ):
        workflow_available = False
        workflow_mode = VideoWorkflowMode.SINGLE_IMAGE_TO_VIDEO
        required_roles = [VideoInputRole.START_FRAME]
        if task.workflow_id:
            try:
                workflow = forced_workflow or self.workflow_registry.get_workflow(task.workflow_id)
                workflow_available = workflow.available_locally
                workflow_mode = workflow.manifest.mode
                required_roles = workflow.manifest.required_input_roles
            except GenerationProviderRuntimeError:
                workflow_available = False
        effective_inputs = self._effective_inputs(
            task,
            input_records or [],
            input_media_assets or {},
        )
        assets_by_role: dict[VideoInputRole, MediaAssetRecord | None] = {}
        for role, task_input in effective_inputs.items():
            if task_input.media_asset_id == task.input_media_asset_id:
                assets_by_role[role] = media_asset
            else:
                assets_by_role[role] = (input_media_assets or {}).get(
                    task_input.media_asset_id or ""
                )
        return self.readiness_service.calculate(
            task,
            media_asset,
            workflow_available=workflow_available,
            input_media_asset_ids_by_role={
                role: task_input.media_asset_id for role, task_input in effective_inputs.items()
            },
            input_media_assets_by_role=assets_by_role,
            required_input_roles=required_roles,
            workflow_mode=workflow_mode,
        )

    def _default_workflow_id(self) -> str | None:
        workflows = self.workflow_registry.list_workflows()
        return workflows[0].manifest.workflow_id if workflows else None

    def _update_values(self, payload: VideoTaskUpdateRequest) -> dict[str, object]:
        values: dict[str, object] = {}
        for field in payload.model_fields_set:
            if field == "inputs":
                continue
            values[field] = getattr(payload, field)
        if "name" in values and not _normalize_optional(values["name"]):
            raise_video_error(
                VideoGenerationErrorCode.VIDEO_TASK_NOT_READY,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if "prompt" in values and values["prompt"] is not None:
            values["prompt"] = _normalize_optional(values["prompt"])
        if "negative_prompt" in values:
            values["negative_prompt"] = _normalize_optional(values["negative_prompt"])
        if "camera_motion" in values:
            values["camera_motion"] = _normalize_optional(values["camera_motion"])
        return values

    def _input_records_from_create_payload(
        self,
        project_id: UUID,
        task_id: str,
        payload: VideoTaskCreateRequest,
        now: datetime,
    ) -> list[VideoGenerationTaskInputRecord]:
        if payload.inputs is not None:
            return self._input_records_from_requests(project_id, task_id, payload.inputs, now)
        if (
            not payload.input_media_asset_id
            and not payload.source_keyframe_output_id
            and not payload.source_keyframe_task_id
        ):
            return []
        return self._input_records_from_requests(
            project_id,
            task_id,
            [
                VideoTaskInputRequest(
                    role=VideoInputRole.START_FRAME,
                    media_asset_id=payload.input_media_asset_id,
                    source_keyframe_output_id=payload.source_keyframe_output_id,
                    source_keyframe_task_id=payload.source_keyframe_task_id,
                )
            ],
            now,
        )

    def _input_records_from_requests(
        self,
        project_id: UUID,
        task_id: str,
        inputs: list[VideoTaskInputRequest],
        now: datetime,
    ) -> list[VideoGenerationTaskInputRecord]:
        seen_roles: set[VideoInputRole] = set()
        records: list[VideoGenerationTaskInputRecord] = []
        for item in inputs:
            if item.role in seen_roles:
                raise_video_error(
                    VideoGenerationErrorCode.VIDEO_INPUT_ROLE_DUPLICATE,
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            seen_roles.add(item.role)
            media_asset_id = item.media_asset_id
            if item.source_keyframe_output_id and not media_asset_id:
                media_asset = self.repository.get_keyframe_output_media_asset(
                    str(project_id),
                    item.source_keyframe_output_id,
                )
                if media_asset is None:
                    raise_video_error(
                        VideoGenerationErrorCode.VIDEO_INPUT_IMAGE_UNAVAILABLE,
                        status.HTTP_404_NOT_FOUND,
                    )
                self._ensure_image_media_asset(media_asset)
                media_asset_id = media_asset.id
            if media_asset_id:
                media_asset = self.repository.get_media_asset(str(project_id), media_asset_id)
                if media_asset is None:
                    raise_video_error(
                        VideoGenerationErrorCode.VIDEO_INPUT_IMAGE_UNAVAILABLE,
                        status.HTTP_404_NOT_FOUND,
                    )
                self._ensure_image_media_asset(media_asset)
            records.append(
                VideoGenerationTaskInputRecord(
                    id=str(uuid4()),
                    project_id=str(project_id),
                    task_id=task_id,
                    role=item.role.value,
                    media_asset_id=media_asset_id,
                    source_keyframe_output_id=item.source_keyframe_output_id,
                    source_keyframe_task_id=item.source_keyframe_task_id,
                    sort_order=VIDEO_INPUT_ROLE_ORDER[item.role.value],
                    created_at=now,
                    updated_at=now,
                )
            )
        return sorted(records, key=lambda record: (record.sort_order, record.role))

    def _legacy_start_input_records(
        self,
        task: VideoGenerationTaskRecord,
        values: dict[str, object],
        now: datetime,
    ) -> list[VideoGenerationTaskInputRecord]:
        media_asset_id = values.get("input_media_asset_id", task.input_media_asset_id)
        source_keyframe_output_id = values.get(
            "source_keyframe_output_id", task.source_keyframe_output_id
        )
        source_keyframe_task_id = values.get(
            "source_keyframe_task_id", task.source_keyframe_task_id
        )
        return [
            VideoGenerationTaskInputRecord(
                id=str(uuid4()),
                project_id=task.project_id,
                task_id=task.id,
                role=VideoInputRole.START_FRAME.value,
                media_asset_id=str(media_asset_id) if media_asset_id else None,
                source_keyframe_output_id=(
                    str(source_keyframe_output_id) if source_keyframe_output_id else None
                ),
                source_keyframe_task_id=(
                    str(source_keyframe_task_id) if source_keyframe_task_id else None
                ),
                sort_order=VIDEO_INPUT_ROLE_ORDER[VideoInputRole.START_FRAME.value],
                created_at=now,
                updated_at=now,
            )
        ]

    def _ensure_image_media_asset(self, media_asset: MediaAssetRecord) -> None:
        if media_asset.media_type != MediaType.IMAGE.value:
            raise_video_error(
                VideoGenerationErrorCode.VIDEO_INPUT_IMAGE_INVALID,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

    def _ensure_project_exists(self, project_id: UUID) -> None:
        if not self.repository.project_exists(str(project_id)):
            raise_video_error(VideoGenerationErrorCode.PROJECT_NOT_FOUND, status.HTTP_404_NOT_FOUND)

    def _get_shot(self, project_id: UUID, shot_id: UUID):
        shot = self.repository.get_shot(str(project_id), str(shot_id))
        if shot is None:
            raise_video_error(VideoGenerationErrorCode.SHOT_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        return shot

    def _get_task(self, project_id: UUID, task_id: UUID) -> VideoGenerationTaskRecord:
        task = self.repository.get_task(str(project_id), str(task_id))
        if task is None:
            raise_video_error(
                VideoGenerationErrorCode.VIDEO_TASK_NOT_FOUND,
                status.HTTP_404_NOT_FOUND,
            )
        return task

    def _get_run(self, project_id: UUID, run_id: UUID) -> VideoGenerationRunRecord:
        run = self.repository.get_run(str(project_id), str(run_id))
        if run is None:
            raise_video_error(
                VideoGenerationErrorCode.VIDEO_RUN_NOT_FOUND,
                status.HTTP_404_NOT_FOUND,
            )
        return run

    def _get_output(self, project_id: UUID, output_id: UUID) -> VideoGenerationOutputRecord:
        output = self.repository.get_output(str(project_id), str(output_id))
        if output is None:
            raise_video_error(
                VideoGenerationErrorCode.VIDEO_OUTPUT_NOT_FOUND,
                status.HTTP_404_NOT_FOUND,
            )
        return output

    def _effective_inputs(
        self,
        task: VideoGenerationTaskRecord,
        input_records: list[VideoGenerationTaskInputRecord],
        input_media_assets: dict[str, MediaAssetRecord],
    ) -> dict[VideoInputRole, VideoGenerationTaskInputRecord]:
        if input_records:
            return {
                VideoInputRole(record.role): record
                for record in sorted(input_records, key=lambda item: (item.sort_order, item.role))
            }
        if not task.input_media_asset_id:
            return {}
        return {
            VideoInputRole.START_FRAME: VideoGenerationTaskInputRecord(
                id="",
                project_id=task.project_id,
                task_id=task.id,
                role=VideoInputRole.START_FRAME.value,
                media_asset_id=task.input_media_asset_id,
                source_keyframe_output_id=task.source_keyframe_output_id,
                source_keyframe_task_id=task.source_keyframe_task_id,
                sort_order=VIDEO_INPUT_ROLE_ORDER[VideoInputRole.START_FRAME.value],
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
        }

    def _input_response(
        self,
        task_input: VideoGenerationTaskInputRecord,
        input_media_assets: dict[str, MediaAssetRecord],
        legacy_input_media_asset: MediaAssetRecord | None,
    ) -> VideoTaskInputResponse:
        media_asset = input_media_assets.get(task_input.media_asset_id or "")
        if media_asset is None and task_input.media_asset_id:
            media_asset = legacy_input_media_asset
        return VideoTaskInputResponse(
            id=task_input.id or None,
            role=VideoInputRole(task_input.role),
            media_asset_id=task_input.media_asset_id,
            source_keyframe_output_id=task_input.source_keyframe_output_id,
            source_keyframe_task_id=task_input.source_keyframe_task_id,
            sort_order=task_input.sort_order,
            media_asset=_media_asset_response(media_asset),
            created_at=ensure_utc(task_input.created_at) if task_input.created_at else None,
            updated_at=ensure_utc(task_input.updated_at) if task_input.updated_at else None,
        )

    def _task_response(
        self,
        task: VideoGenerationTaskRecord,
        input_media_asset: MediaAssetRecord | None,
        input_records: list[VideoGenerationTaskInputRecord],
        input_media_assets: dict[str, MediaAssetRecord],
        latest_run_status: str | None,
        selected_output: VideoGenerationOutputRecord | None,
        selected_media_assets: dict[str, MediaAssetRecord],
    ) -> VideoTaskResponse:
        effective_inputs = self._effective_inputs(task, input_records, input_media_assets)
        return VideoTaskResponse(
            id=task.id,
            project_id=task.project_id,
            shot_id=task.shot_id,
            name=task.name,
            status=VideoGenerationTaskStatus(task.status),
            input_media_asset_id=task.input_media_asset_id,
            source_keyframe_output_id=task.source_keyframe_output_id,
            source_keyframe_task_id=task.source_keyframe_task_id,
            prompt=task.prompt,
            negative_prompt=task.negative_prompt,
            duration_seconds=task.duration_seconds,
            fps=task.fps,
            width=task.width,
            height=task.height,
            seed=task.seed,
            motion_strength=task.motion_strength,
            camera_motion=task.camera_motion,
            workflow_id=task.workflow_id,
            input_media_asset=(
                _media_asset_response(input_media_asset) if input_media_asset else None
            ),
            inputs=[
                self._input_response(task_input, input_media_assets, input_media_asset)
                for task_input in sorted(
                    effective_inputs.values(),
                    key=lambda item: (item.sort_order, item.role),
                )
            ],
            readiness=self._readiness(task, input_media_asset, input_records, input_media_assets),
            latest_run_status=(
                VideoGenerationRunStatus(latest_run_status) if latest_run_status else None
            ),
            selected_output=(
                self._output_response(selected_output, selected_media_assets)
                if selected_output
                else None
            ),
            created_at=ensure_utc(task.created_at),
            updated_at=ensure_utc(task.updated_at),
        )

    def _run_response(
        self,
        run: VideoGenerationRunRecord,
        outputs: list[VideoGenerationOutputRecord],
        media_assets: dict[str, MediaAssetRecord],
    ) -> VideoRunResponse:
        return VideoRunResponse(
            id=run.id,
            project_id=run.project_id,
            video_task_id=run.video_task_id,
            run_number=run.run_number,
            provider=run.provider,
            workflow_id=run.workflow_id,
            workflow_version=run.workflow_version,
            status=VideoGenerationRunStatus(run.status),
            provider_job_id=run.provider_job_id,
            submitted_payload_snapshot=VideoRunSnapshot.model_validate_json(
                run.submitted_payload_snapshot
            ),
            error_code=run.error_code,
            error_message_safe=run.error_message_safe,
            queued_at=ensure_utc(run.queued_at) if run.queued_at else None,
            started_at=ensure_utc(run.started_at) if run.started_at else None,
            completed_at=ensure_utc(run.completed_at) if run.completed_at else None,
            created_at=ensure_utc(run.created_at),
            updated_at=ensure_utc(run.updated_at),
            outputs=[self._output_response(output, media_assets) for output in outputs],
        )

    def _output_response(
        self,
        output: VideoGenerationOutputRecord,
        media_assets: dict[str, MediaAssetRecord],
    ) -> VideoOutputResponse:
        return VideoOutputResponse(
            id=output.id,
            project_id=output.project_id,
            run_id=output.run_id,
            media_asset_id=output.media_asset_id,
            output_index=output.output_index,
            width=output.width,
            height=output.height,
            duration_seconds=output.duration_seconds,
            fps=output.fps,
            seed=output.seed,
            is_selected=output.is_selected,
            media_asset=_media_asset_response(media_assets.get(output.media_asset_id)),
            created_at=ensure_utc(output.created_at),
        )


def media_record_from_stored_image(
    project_id: str,
    stored: StoredImage,
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


def media_record_from_stored_video(
    project_id: str,
    stored: StoredVideo,
    now: datetime,
    *,
    width: int,
    height: int,
) -> MediaAssetRecord:
    return MediaAssetRecord(
        id=str(uuid4()),
        project_id=project_id,
        media_type=MediaType.VIDEO.value,
        original_filename=stored.original_filename,
        stored_filename=stored.stored_filename,
        relative_path=stored.relative_path,
        thumbnail_relative_path=None,
        mime_type=stored.mime_type,
        extension=stored.extension,
        size_bytes=stored.size_bytes,
        width=width,
        height=height,
        sha256=stored.sha256,
        created_at=now,
    )


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
        thumbnail_url=(
            f"/api/media/{media_asset.id}/thumbnail"
            if media_asset.thumbnail_relative_path
            else None
        ),
        content_url=f"/api/media/{media_asset.id}/content",
        created_at=ensure_utc(media_asset.created_at),
    )


def _input_by_role(
    inputs: list[VideoGenerationTaskInputRecord],
    role: VideoInputRole,
) -> VideoGenerationTaskInputRecord | None:
    return next((item for item in inputs if item.role == role.value), None)


def _normalize_optional(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _workflow_model_missing_requirements(
    workflow: LoadedVideoWorkflow,
    object_info: dict[str, object],
) -> list[str]:
    if workflow.workflow is None or not object_info:
        return []
    missing: list[str] = []
    for node in workflow.workflow.values():
        if not isinstance(node, dict):
            continue
        class_type = node.get("class_type")
        if not isinstance(class_type, str) or class_type not in MODEL_LOADER_INPUTS:
            continue
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue
        for input_name in MODEL_LOADER_INPUTS[class_type]:
            model_name = inputs.get(input_name)
            if not isinstance(model_name, str) or not model_name.strip():
                continue
            available = _object_info_input_options(object_info, class_type, input_name)
            if available is None:
                continue
            if model_name not in available:
                missing.append(f"model_file_missing:{class_type}.{input_name}:{model_name}")
    return missing


def _object_info_input_options(
    object_info: dict[str, object],
    class_type: str,
    input_name: str,
) -> set[str] | None:
    node_info = object_info.get(class_type)
    if not isinstance(node_info, dict):
        return None
    input_info = node_info.get("input")
    if not isinstance(input_info, dict):
        return None
    required = input_info.get("required")
    if not isinstance(required, dict):
        return None
    spec = required.get(input_name)
    if not isinstance(spec, list) or not spec:
        return None
    options = spec[0]
    if not isinstance(options, list):
        return None
    return {str(option) for option in options}


def utc_now() -> datetime:
    return datetime.now(UTC)


def raise_video_error(
    code: VideoGenerationErrorCode,
    http_status: int,
    details: object | None = None,
) -> None:
    raise AppError(
        code=code.value,
        message=VIDEO_GENERATION_ERROR_MESSAGES[code.value],
        status_code=http_status,
        details=details,
    )
