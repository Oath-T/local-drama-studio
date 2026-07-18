from datetime import UTC, datetime
from random import SystemRandom
from uuid import UUID, uuid4

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError

from app.api.schemas.character import MediaAssetResponse
from app.api.schemas.keyframe_generation import (
    KeyframeOutputResponse,
    KeyframeRunCreateResponse,
    KeyframeRunListResponse,
    KeyframeRunResponse,
    KeyframeRunSnapshot,
    KeyframeWorkflowListResponse,
    KeyframeWorkflowResponse,
)
from app.api.schemas.keyframe_task import KeyframeShotSnapshot
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.domain.keyframe_generation import (
    KEYFRAME_GENERATION_ERROR_MESSAGES,
    KeyframeGenerationErrorCode,
    KeyframeGenerationRunStatus,
)
from app.domain.keyframe_task import KeyframeTaskReadinessStatus, KeyframeTaskStatus
from app.domain.media_asset import MediaType
from app.infrastructure.generation.base import GenerationProviderRuntimeError
from app.infrastructure.generation.factory import create_keyframe_generation_provider
from app.infrastructure.generation.workflow_loader import LoadedWorkflow, WorkflowRegistry
from app.infrastructure.generation.workflow_mapper import WorkflowMapper, WorkflowMappingValues
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.keyframe_generation import (
    KeyframeGenerationOutputRecord,
    KeyframeGenerationRunRecord,
)
from app.infrastructure.models.keyframe_task import (
    KeyframeGenerationTaskRecord,
)
from app.repository.keyframe_generation_repository import KeyframeGenerationRepository
from app.service.keyframe_task_readiness_service import (
    KeyframeTaskReadinessService,
    ensure_utc,
)
from app.service.media_storage_service import StoredImage

MAX_COMFYUI_SEED = 2**32 - 1


class KeyframeGenerationService:
    def __init__(
        self,
        repository: KeyframeGenerationRepository,
        settings: Settings | None = None,
        workflow_registry: WorkflowRegistry | None = None,
        workflow_mapper: WorkflowMapper | None = None,
        readiness_service: KeyframeTaskReadinessService | None = None,
    ) -> None:
        self.repository = repository
        self.settings = settings or get_settings()
        self.workflow_registry = workflow_registry or WorkflowRegistry(self.settings)
        self.workflow_mapper = workflow_mapper or WorkflowMapper()
        self.readiness_service = readiness_service or KeyframeTaskReadinessService()

    async def list_workflows(self, project_id: UUID) -> KeyframeWorkflowListResponse:
        self._ensure_project_exists(project_id)
        provider_available, node_types = await self._provider_availability()
        items: list[KeyframeWorkflowResponse] = []
        try:
            workflows = self.workflow_registry.list_workflows()
        except GenerationProviderRuntimeError as exc:
            _raise_provider_error(exc, status.HTTP_400_BAD_REQUEST)
        for workflow in workflows:
            missing = self._workflow_missing_requirements(
                workflow,
                provider_available=provider_available,
                node_types=node_types,
            )
            items.append(
                KeyframeWorkflowResponse(
                    workflow_id=workflow.manifest.workflow_id,
                    display_name=workflow.manifest.display_name,
                    version=workflow.manifest.version,
                    available=len(missing) == 0,
                    missing_requirements=missing,
                    uses_reference_inputs=workflow.manifest.uses_reference_inputs,
                )
            )
        return KeyframeWorkflowListResponse(items=items, total=len(items))

    async def create_run(
        self,
        project_id: UUID,
        task_id: UUID,
        workflow_id: str,
        *,
        skip_task_readiness: bool = False,
    ) -> KeyframeRunCreateResponse:
        task = self._get_task(project_id, task_id)
        try:
            workflow = self.workflow_registry.get_workflow(workflow_id)
        except GenerationProviderRuntimeError as exc:
            _raise_provider_error(exc, status.HTTP_400_BAD_REQUEST)
        self._ensure_task_can_run(task, skip_readiness=skip_task_readiness)
        if task.output_count != 1:
            raise_generation_error(
                KeyframeGenerationErrorCode.WORKFLOW_OUTPUT_COUNT_UNSUPPORTED,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if self.repository.get_active_run_for_task(task.id) is not None:
            raise_generation_error(
                KeyframeGenerationErrorCode.GENERATION_ALREADY_RUNNING,
                status.HTTP_409_CONFLICT,
            )
        provider_available, node_types = await self._provider_availability(raise_when_offline=True)
        missing = self._workflow_missing_requirements(
            workflow,
            provider_available=provider_available,
            node_types=node_types,
        )
        if missing:
            code = (
                KeyframeGenerationErrorCode.WORKFLOW_MODEL_MISSING
                if "default_checkpoint_not_configured" in missing
                else KeyframeGenerationErrorCode.WORKFLOW_NODE_MISSING
            )
            raise_generation_error(code, status.HTTP_400_BAD_REQUEST, details={"missing": missing})
        try:
            snapshot = self._build_run_snapshot(task, workflow)
            self._validate_mapping(workflow, snapshot)
        except GenerationProviderRuntimeError as exc:
            _raise_provider_error(exc, status.HTTP_422_UNPROCESSABLE_ENTITY)
        now = utc_now()
        run = KeyframeGenerationRunRecord(
            id=str(uuid4()),
            project_id=task.project_id,
            keyframe_task_id=task.id,
            run_number=self.repository.next_run_number(task.id),
            provider=self.settings.keyframe_provider,
            workflow_id=workflow.manifest.workflow_id,
            workflow_version=workflow.manifest.version,
            status=KeyframeGenerationRunStatus.QUEUED.value,
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
            raise_generation_error(
                KeyframeGenerationErrorCode.DATABASE_CONFLICT,
                status.HTTP_409_CONFLICT,
            )
        return KeyframeRunCreateResponse(
            run_id=created.id,
            status=KeyframeGenerationRunStatus(created.status),
        )

    async def retry_run(self, project_id: UUID, run_id: UUID) -> KeyframeRunCreateResponse:
        run = self._get_run(project_id, run_id)
        return await self.create_run(project_id, UUID(run.keyframe_task_id), run.workflow_id)

    def list_runs(self, project_id: UUID, task_id: UUID) -> KeyframeRunListResponse:
        task = self._get_task(project_id, task_id)
        data = self.repository.list_runs_for_task(task.project_id, task.id)
        return KeyframeRunListResponse(
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

    def get_run(self, project_id: UUID, run_id: UUID) -> KeyframeRunResponse:
        run = self._get_run(project_id, run_id)
        outputs = self.repository.list_outputs_for_runs([run.id]).get(run.id, [])
        media_assets = self.repository.get_media_assets_by_ids(
            sorted({output.media_asset_id for output in outputs})
        )
        return self._run_response(run, outputs, media_assets)

    def select_output(self, project_id: UUID, output_id: UUID) -> KeyframeOutputResponse:
        output = self._get_output(project_id, output_id)
        try:
            self.repository.select_output(output)
        except SQLAlchemyError:
            raise_generation_error(
                KeyframeGenerationErrorCode.DATABASE_CONFLICT,
                status.HTTP_409_CONFLICT,
            )
        media_asset = self.repository.media_asset_for_output(output)
        media_assets = {output.media_asset_id: media_asset} if media_asset else {}
        return self._output_response(output, media_assets)

    def unselect_output(self, project_id: UUID, output_id: UUID) -> KeyframeOutputResponse:
        output = self._get_output(project_id, output_id)
        try:
            self.repository.unselect_output(output)
        except SQLAlchemyError:
            raise_generation_error(
                KeyframeGenerationErrorCode.DATABASE_CONFLICT,
                status.HTTP_409_CONFLICT,
            )
        media_asset = self.repository.media_asset_for_output(output)
        media_assets = {output.media_asset_id: media_asset} if media_asset else {}
        return self._output_response(output, media_assets)

    def build_provider_workflow(self, run: KeyframeGenerationRunRecord) -> dict[str, object]:
        snapshot = KeyframeRunSnapshot.model_validate_json(run.submitted_payload_snapshot)
        workflow = self.workflow_registry.get_workflow(snapshot.workflow_id)
        return self.workflow_mapper.build_workflow(
            workflow,
            WorkflowMappingValues(
                positive_prompt=snapshot.effective_positive_prompt,
                negative_prompt=snapshot.negative_prompt,
                width=snapshot.width,
                height=snapshot.height,
                seed=snapshot.seed,
                steps=snapshot.steps,
                guidance_scale=snapshot.guidance_scale,
                sampler_name=snapshot.sampler_name,
                scheduler_name=snapshot.scheduler_name,
                checkpoint_name=self._default_checkpoint(),
            ),
        )

    def _ensure_task_can_run(
        self,
        task: KeyframeGenerationTaskRecord,
        *,
        skip_readiness: bool = False,
    ) -> None:
        if task.status != KeyframeTaskStatus.READY.value:
            raise_generation_error(
                KeyframeGenerationErrorCode.TASK_NOT_READY,
                status.HTTP_400_BAD_REQUEST,
            )
        if skip_readiness:
            return
        references = self.repository.list_task_references(task.id)
        media_assets = self.repository.get_media_assets_by_ids(
            sorted({reference.media_asset_id for reference in references})
        )
        current_shot = self.repository.get_shot(task.project_id, task.shot_id)
        readiness = self.readiness_service.calculate(
            task,
            KeyframeShotSnapshot.model_validate_json(task.shot_snapshot),
            references,
            media_assets,
            current_shot,
        )
        if readiness.readiness_status != KeyframeTaskReadinessStatus.READY:
            raise AppError(
                code=KeyframeGenerationErrorCode.TASK_NOT_READY.value,
                message=KEYFRAME_GENERATION_ERROR_MESSAGES[
                    KeyframeGenerationErrorCode.TASK_NOT_READY.value
                ],
                status_code=status.HTTP_400_BAD_REQUEST,
                details=readiness.model_dump(mode="json"),
            )

    def _build_run_snapshot(
        self,
        task: KeyframeGenerationTaskRecord,
        workflow: LoadedWorkflow,
    ) -> KeyframeRunSnapshot:
        references = self.repository.list_task_references(task.id)
        seed = task.seed if task.seed is not None else SystemRandom().randint(0, MAX_COMFYUI_SEED)
        prompt_en = _normalize_optional(task.prompt_en)
        prompt_zh = _normalize_optional(task.prompt_zh)
        effective_language = "en" if prompt_en else "zh"
        effective_prompt = prompt_en or prompt_zh
        if effective_prompt is None:
            raise_generation_error(
                KeyframeGenerationErrorCode.TASK_NOT_READY,
                status.HTTP_400_BAD_REQUEST,
            )
        sampler_name = self._resolve_snapshot_sampler(workflow, task.sampler_name)
        scheduler_name = self._resolve_snapshot_scheduler(workflow, task.scheduler_name)
        return KeyframeRunSnapshot(
            task_id=task.id,
            task_updated_at=ensure_utc(task.updated_at),
            workflow_id=workflow.manifest.workflow_id,
            workflow_version=workflow.manifest.version,
            prompt_zh=prompt_zh,
            prompt_en=prompt_en,
            effective_prompt_language=effective_language,
            effective_positive_prompt=effective_prompt,
            negative_prompt=_normalize_optional(task.negative_prompt),
            width=task.width,
            height=task.height,
            seed=seed,
            steps=task.steps,
            guidance_scale=task.guidance_scale,
            sampler_name=sampler_name,
            scheduler_name=scheduler_name,
            output_count=task.output_count,
            task_reference_ids=[reference.id for reference in references],
            media_asset_ids=[reference.media_asset_id for reference in references],
            reference_inputs_used=False,
        )

    def _validate_mapping(self, workflow: LoadedWorkflow, snapshot: KeyframeRunSnapshot) -> None:
        self.workflow_mapper.build_workflow(
            workflow,
            WorkflowMappingValues(
                positive_prompt=snapshot.effective_positive_prompt,
                negative_prompt=snapshot.negative_prompt,
                width=snapshot.width,
                height=snapshot.height,
                seed=snapshot.seed,
                steps=snapshot.steps,
                guidance_scale=snapshot.guidance_scale,
                sampler_name=snapshot.sampler_name,
                scheduler_name=snapshot.scheduler_name,
                checkpoint_name=self._default_checkpoint(),
            ),
        )

    async def _provider_availability(
        self,
        *,
        raise_when_offline: bool = False,
    ) -> tuple[bool, set[str]]:
        try:
            provider = create_keyframe_generation_provider(self.settings)
        except GenerationProviderRuntimeError:
            if raise_when_offline:
                raise_generation_error(
                    KeyframeGenerationErrorCode.PROVIDER_NOT_CONFIGURED,
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            return False, set()
        health = await provider.check_health()
        if not health.available:
            if raise_when_offline:
                raise_generation_error(
                    KeyframeGenerationErrorCode.COMFYUI_UNAVAILABLE,
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            return False, set()
        try:
            return True, await provider.get_required_node_types()
        except GenerationProviderRuntimeError:
            if raise_when_offline:
                raise_generation_error(
                    KeyframeGenerationErrorCode.COMFYUI_UNAVAILABLE,
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            return True, set()

    def _workflow_missing_requirements(
        self,
        workflow: LoadedWorkflow,
        *,
        provider_available: bool,
        node_types: set[str],
    ) -> list[str]:
        missing: list[str] = []
        if not provider_available:
            missing.append("provider_offline")
        if not self._default_checkpoint():
            missing.append("default_checkpoint_not_configured")
        if provider_available and workflow.manifest.required_node_types:
            if not node_types:
                missing.append("required_node_types_unavailable")
            else:
                for node_type in workflow.manifest.required_node_types:
                    if node_type not in node_types:
                        missing.append(f"node_type_missing:{node_type}")
        return missing

    def _resolve_snapshot_sampler(self, workflow: LoadedWorkflow, value: str | None) -> str:
        resolved = value.strip() if value else workflow.manifest.default_sampler_name
        if not resolved or (
            workflow.manifest.allowed_samplers
            and resolved not in workflow.manifest.allowed_samplers
        ):
            raise_generation_error(
                KeyframeGenerationErrorCode.WORKFLOW_SAMPLER_UNSUPPORTED,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return resolved

    def _resolve_snapshot_scheduler(self, workflow: LoadedWorkflow, value: str | None) -> str:
        resolved = value.strip() if value else workflow.manifest.default_scheduler_name
        if not resolved or (
            workflow.manifest.allowed_schedulers
            and resolved not in workflow.manifest.allowed_schedulers
        ):
            raise_generation_error(
                KeyframeGenerationErrorCode.WORKFLOW_SCHEDULER_UNSUPPORTED,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return resolved

    def _default_checkpoint(self) -> str:
        return (self.settings.comfyui_default_checkpoint or "").strip()

    def _ensure_project_exists(self, project_id: UUID) -> None:
        if not self.repository.project_exists(str(project_id)):
            raise_generation_error(
                KeyframeGenerationErrorCode.PROJECT_NOT_FOUND,
                status.HTTP_404_NOT_FOUND,
            )

    def _get_task(self, project_id: UUID, task_id: UUID) -> KeyframeGenerationTaskRecord:
        task = self.repository.get_task(str(project_id), str(task_id))
        if task is None:
            raise_generation_error(
                KeyframeGenerationErrorCode.KEYFRAME_TASK_NOT_FOUND,
                status.HTTP_404_NOT_FOUND,
            )
        return task

    def _get_run(self, project_id: UUID, run_id: UUID) -> KeyframeGenerationRunRecord:
        run = self.repository.get_run(str(project_id), str(run_id))
        if run is None:
            raise_generation_error(
                KeyframeGenerationErrorCode.GENERATION_RUN_NOT_FOUND,
                status.HTTP_404_NOT_FOUND,
            )
        return run

    def _get_output(self, project_id: UUID, output_id: UUID) -> KeyframeGenerationOutputRecord:
        output = self.repository.get_output(str(project_id), str(output_id))
        if output is None:
            raise_generation_error(
                KeyframeGenerationErrorCode.GENERATION_OUTPUT_NOT_FOUND,
                status.HTTP_404_NOT_FOUND,
            )
        return output

    def _run_response(
        self,
        run: KeyframeGenerationRunRecord,
        outputs: list[KeyframeGenerationOutputRecord],
        media_assets: dict[str, MediaAssetRecord],
    ) -> KeyframeRunResponse:
        return KeyframeRunResponse(
            id=run.id,
            project_id=run.project_id,
            keyframe_task_id=run.keyframe_task_id,
            run_number=run.run_number,
            provider=run.provider,
            workflow_id=run.workflow_id,
            workflow_version=run.workflow_version,
            status=KeyframeGenerationRunStatus(run.status),
            provider_job_id=run.provider_job_id,
            submitted_payload_snapshot=KeyframeRunSnapshot.model_validate_json(
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
        output: KeyframeGenerationOutputRecord,
        media_assets: dict[str, MediaAssetRecord],
    ) -> KeyframeOutputResponse:
        media_asset = media_assets.get(output.media_asset_id)
        return KeyframeOutputResponse(
            id=output.id,
            project_id=output.project_id,
            run_id=output.run_id,
            media_asset_id=output.media_asset_id,
            output_index=output.output_index,
            width=output.width,
            height=output.height,
            seed=output.seed,
            is_selected=output.is_selected,
            media_asset=_media_asset_response(media_asset),
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


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def utc_now() -> datetime:
    return datetime.now(UTC)


def raise_generation_error(
    code: KeyframeGenerationErrorCode,
    http_status: int,
    details: object | None = None,
) -> None:
    raise AppError(
        code=code.value,
        message=KEYFRAME_GENERATION_ERROR_MESSAGES[code.value],
        status_code=http_status,
        details=details,
    )


def _raise_provider_error(exc: GenerationProviderRuntimeError, http_status: int) -> None:
    raise_generation_error(exc.code, http_status)
