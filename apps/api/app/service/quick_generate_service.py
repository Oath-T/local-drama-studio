import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.schemas.keyframe_task import KeyframeTaskCreateRequest, KeyframeTaskUpdateRequest
from app.api.schemas.quick_generate import (
    CanvasSyncResponse,
    QuickGenerateExecuteRequest,
    QuickGenerateExecuteResponse,
    QuickGenerateMode,
    QuickGeneratePreviewRequest,
    QuickGeneratePreviewResponse,
    QuickGenerateRunType,
    QuickGenerateSyncOutputRequest,
    WorkflowCapabilityResponse,
    WorkflowRouteResponse,
)
from app.api.schemas.video_generation import (
    VideoTaskCreateRequest,
    VideoTaskInputRequest,
    VideoTaskUpdateRequest,
)
from app.core.errors import AppError
from app.domain.keyframe_task import KeyframeTaskErrorCode, KeyframeTaskPurpose, KeyframeTaskStatus
from app.domain.video_generation import VideoInputRole
from app.infrastructure.models.quick_generate import QuickGenerateRequestRecord
from app.repository.keyframe_generation_repository import KeyframeGenerationRepository
from app.repository.keyframe_task_repository import KeyframeTaskRepository
from app.repository.quick_generate_repository import QuickGenerateRepository
from app.repository.video_generation_repository import VideoGenerationRepository
from app.service.canvas_output_sync_service import CanvasOutputSyncService
from app.service.keyframe_generation_service import KeyframeGenerationService
from app.service.keyframe_task_service import KeyframeTaskService
from app.service.video_generation_service import VideoGenerationService
from app.service.workflow_capability_registry import WorkflowCapabilityRegistry

QUICK_GENERATE_NOT_EXECUTABLE = "quick_generate_not_executable"
QUICK_GENERATE_IN_PROGRESS = "quick_generate_request_in_progress"
QUICK_GENERATE_CONFLICT = "quick_generate_conflict"
QUICK_GENERATE_SYNC_UNAVAILABLE = "quick_generate_sync_unavailable"
_QUICK_GENERATE_LOCKS: dict[tuple[str, str, str], asyncio.Lock] = {}


class QuickGenerateService:
    def __init__(
        self,
        repository: QuickGenerateRepository,
        keyframe_task_service: KeyframeTaskService,
        keyframe_generation_service: KeyframeGenerationService,
        video_generation_service: VideoGenerationService,
        capability_registry: WorkflowCapabilityRegistry,
        canvas_sync_service: CanvasOutputSyncService,
    ) -> None:
        self.repository = repository
        self.keyframe_task_service = keyframe_task_service
        self.keyframe_generation_service = keyframe_generation_service
        self.video_generation_service = video_generation_service
        self.capability_registry = capability_registry
        self.canvas_sync_service = canvas_sync_service

    async def preview(
        self,
        project_id: UUID,
        shot_id: UUID,
        payload: QuickGeneratePreviewRequest,
    ) -> QuickGeneratePreviewResponse:
        shot = self._get_shot(project_id, shot_id)
        capabilities = await self.capability_registry.list_capabilities(project_id)
        route = self._route(
            project_id=str(project_id),
            shot_id=shot.id,
            payload=payload,
            capabilities=capabilities,
        )
        return QuickGeneratePreviewResponse(
            mode=payload.mode,
            route=route,
            capabilities=capabilities,
        )

    async def execute(
        self,
        project_id: UUID,
        shot_id: UUID,
        payload: QuickGenerateExecuteRequest,
    ) -> QuickGenerateExecuteResponse:
        shot = self._get_shot(project_id, shot_id)
        existing = self.repository.get_request(
            str(project_id), shot.id, payload.mode.value, payload.request_id
        )
        if existing is not None:
            if existing.response_json:
                response = QuickGenerateExecuteResponse.model_validate_json(existing.response_json)
                response.idempotent_replay = True
                return response
            raise AppError(
                code=QUICK_GENERATE_IN_PROGRESS,
                message="相同生成请求正在处理中，请稍后刷新。",
                status_code=status.HTTP_409_CONFLICT,
            )
        preview = await self.preview(
            project_id,
            shot_id,
            QuickGeneratePreviewRequest(
                mode=payload.mode,
                prompt=payload.prompt,
                negative_prompt=payload.negative_prompt,
                workflow_id=payload.workflow_id,
            ),
        )
        active = self._active_run_for_mode(str(project_id), shot.id, payload.mode)
        if active is not None:
            response = self._active_run_response(
                payload.request_id,
                payload.mode,
                preview.route,
                active,
            )
            request_record = self._create_request_record(project_id, shot_id, payload)
            self._store_request_response(request_record, response)
            return response
        if not preview.route.executable or preview.route.selected_workflow_id is None:
            raise AppError(
                code=QUICK_GENERATE_NOT_EXECUTABLE,
                message=preview.route.reason_zh,
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                details=preview.route.model_dump(mode="json"),
            )
        request_record = self._create_request_record(project_id, shot_id, payload)
        async with _quick_generate_lock(str(project_id), shot.id, payload.mode.value):
            active_after_claim = self._active_run_for_mode(str(project_id), shot.id, payload.mode)
            if active_after_claim is not None:
                response = self._active_run_response(
                    payload.request_id,
                    payload.mode,
                    preview.route,
                    active_after_claim,
                )
            else:
                response = await self._execute_after_request_record(
                    project_id,
                    shot_id,
                    payload,
                    preview.route,
                )
        self._store_request_response(request_record, response)
        return response

    def sync_output(
        self,
        project_id: UUID,
        shot_id: UUID,
        payload: QuickGenerateSyncOutputRequest,
    ) -> CanvasSyncResponse:
        shot = self._get_shot(project_id, shot_id)
        if payload.run_type == QuickGenerateRunType.KEYFRAME:
            run = KeyframeGenerationRepository(self.repository.session).get_run(
                str(project_id), payload.run_id
            )
            if run is None or run.project_id != str(project_id):
                raise_sync_unavailable()
            task = KeyframeTaskRepository(self.repository.session).get_task(
                str(project_id), run.keyframe_task_id
            )
            if task is None or task.shot_id != shot.id:
                raise_sync_unavailable()
            result = self.canvas_sync_service.sync_keyframe_run_outputs(run.id)
            return CanvasSyncResponse(
                attempted=True,
                synced=result is not None,
                node_id=result.node_id if result is not None else None,
                edge_id=result.edge_id if result is not None else None,
            )
        run = VideoGenerationRepository(self.repository.session).get_run(
            str(project_id), payload.run_id
        )
        if run is None or run.project_id != str(project_id):
            raise_sync_unavailable()
        task = VideoGenerationRepository(self.repository.session).get_task(
            str(project_id), run.video_task_id
        )
        if task is None or task.shot_id != shot.id:
            raise_sync_unavailable()
        result = self.canvas_sync_service.sync_video_run_outputs(run.id)
        return CanvasSyncResponse(
            attempted=True,
            synced=result is not None,
            node_id=result.node_id if result is not None else None,
            edge_id=result.edge_id if result is not None else None,
        )

    async def _execute_after_request_record(
        self,
        project_id: UUID,
        shot_id: UUID,
        payload: QuickGenerateExecuteRequest,
        route: WorkflowRouteResponse,
    ) -> QuickGenerateExecuteResponse:
        if payload.mode in (QuickGenerateMode.FIRST_FRAME, QuickGenerateMode.END_FRAME):
            return await self._execute_keyframe(project_id, shot_id, payload, route)
        return await self._execute_video(project_id, shot_id, payload, route)

    async def _execute_keyframe(
        self,
        project_id: UUID,
        shot_id: UUID,
        payload: QuickGenerateExecuteRequest,
        route: WorkflowRouteResponse,
    ) -> QuickGenerateExecuteResponse:
        purpose = (
            KeyframeTaskPurpose.FIRST_FRAME
            if payload.mode == QuickGenerateMode.FIRST_FRAME
            else KeyframeTaskPurpose.END_FRAME
        )
        existing = self.repository.get_keyframe_task_by_purpose(
            str(project_id), str(shot_id), purpose.value
        )
        if existing is None:
            task = self.keyframe_task_service.create_task(
                project_id,
                shot_id,
                KeyframeTaskCreateRequest(
                    name=_keyframe_task_name(payload.mode),
                    purpose=purpose,
                    copy_current_references=True,
                ),
            )
            task_id = UUID(task.id)
        else:
            task_id = UUID(existing.id)
            self._ensure_keyframe_task_has_current_references(project_id, task_id)
        updated = self.keyframe_task_service.update_task(
            project_id,
            task_id,
            KeyframeTaskUpdateRequest(
                name=_keyframe_task_name(payload.mode),
                purpose=purpose,
                prompt_en=_required_prompt(payload.prompt),
                negative_prompt=payload.negative_prompt,
                aspect_ratio="9:16",
                width=768,
                height=1360,
                output_count=1,
                steps=28,
                guidance_scale=6.5,
            ),
        )
        ready = self._mark_quick_keyframe_task_ready(project_id, UUID(updated.id))
        run = await self.keyframe_generation_service.create_run(
            project_id,
            UUID(ready.id),
            route.selected_workflow_id or "",
            skip_task_readiness=True,
        )
        return QuickGenerateExecuteResponse(
            mode=payload.mode,
            run_type=QuickGenerateRunType.KEYFRAME,
            request_id=payload.request_id,
            task_id=ready.id,
            run_id=run.run_id,
            status=run.status.value,
            workflow_id=route.selected_workflow_id or "",
            route=route,
        )

    async def _execute_video(
        self,
        project_id: UUID,
        shot_id: UUID,
        payload: QuickGenerateExecuteRequest,
        route: WorkflowRouteResponse,
    ) -> QuickGenerateExecuteResponse:
        start_output = self.repository.get_selected_keyframe_output(
            str(project_id), str(shot_id), KeyframeTaskPurpose.FIRST_FRAME.value
        )
        end_output = self.repository.get_selected_keyframe_output(
            str(project_id), str(shot_id), KeyframeTaskPurpose.END_FRAME.value
        )
        if start_output is None or end_output is None:
            raise AppError(
                code=QUICK_GENERATE_NOT_EXECUTABLE,
                message="生成视频前需要先采用首帧和尾帧。",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                details=route.model_dump(mode="json"),
            )
        inputs = [
            VideoTaskInputRequest(
                role=VideoInputRole.START_FRAME,
                source_keyframe_output_id=start_output.id,
            ),
            VideoTaskInputRequest(
                role=VideoInputRole.END_FRAME,
                source_keyframe_output_id=end_output.id,
            ),
        ]
        existing = self.repository.get_video_task(str(project_id), str(shot_id))
        if existing is None:
            task = self.video_generation_service.create_task(
                project_id,
                shot_id,
                VideoTaskCreateRequest(inputs=inputs),
            )
            task_id = UUID(task.id)
        else:
            task_id = UUID(existing.id)
        updated = self.video_generation_service.update_task(
            project_id,
            task_id,
            VideoTaskUpdateRequest(
                name="视频生成任务",
                inputs=inputs,
                prompt=_required_prompt(payload.prompt),
                negative_prompt=payload.negative_prompt,
                duration_seconds=2,
                fps=16,
                width=640,
                height=640,
                seed=None,
                motion_strength=0.45,
                camera_motion=None,
                workflow_id=route.selected_workflow_id,
            ),
        )
        ready = await self.video_generation_service.mark_ready(project_id, UUID(updated.id))
        run = await self.video_generation_service.create_run(
            project_id,
            UUID(ready.id),
            route.selected_workflow_id or "",
        )
        return QuickGenerateExecuteResponse(
            mode=payload.mode,
            run_type=QuickGenerateRunType.VIDEO,
            request_id=payload.request_id,
            task_id=ready.id,
            run_id=run.run_id,
            status=run.status.value,
            workflow_id=route.selected_workflow_id or "",
            route=route,
        )

    def _route(
        self,
        *,
        project_id: str,
        shot_id: str,
        payload: QuickGeneratePreviewRequest,
        capabilities: list[WorkflowCapabilityResponse],
    ) -> WorkflowRouteResponse:
        candidates = sorted(
            [
                capability
                for capability in capabilities
                if payload.mode in capability.supports
                and (payload.workflow_id is None or capability.workflow_id == payload.workflow_id)
            ],
            key=lambda item: (
                _workflow_mode_priority(payload.mode, item.workflow_id),
                not item.executable,
                item.task_type.value,
                item.workflow_id,
            ),
        )
        selected = candidates[0] if candidates else None
        required_inputs = ["prompt"]
        missing_inputs: list[str] = []
        if not _normalize_text(payload.prompt):
            missing_inputs.append("prompt")
        if payload.mode == QuickGenerateMode.VIDEO:
            required_inputs.extend(["adopted_first_frame", "adopted_end_frame"])
            if (
                self.repository.get_selected_keyframe_output(
                    project_id,
                    shot_id,
                    KeyframeTaskPurpose.FIRST_FRAME.value,
                )
                is None
            ):
                missing_inputs.append("adopted_first_frame")
            if (
                self.repository.get_selected_keyframe_output(
                    project_id,
                    shot_id,
                    KeyframeTaskPurpose.END_FRAME.value,
                )
                is None
            ):
                missing_inputs.append("adopted_end_frame")
        if selected is None:
            return WorkflowRouteResponse(
                selected_workflow_id=None,
                executable=False,
                reason_zh="当前没有可用于该生成类型的工作流。",
                required_inputs=required_inputs,
                missing_inputs=missing_inputs,
            )
        executable = selected.executable and not missing_inputs
        if missing_inputs:
            reason = "缺少必要输入，暂不能开始生成。"
        elif not selected.executable:
            reason = "推荐工作流当前不可用。"
        else:
            reason = "已选择可执行工作流。"
        return WorkflowRouteResponse(
            selected_workflow_id=selected.workflow_id,
            executable=executable,
            reason_zh=reason,
            required_inputs=required_inputs,
            missing_inputs=missing_inputs,
            missing_models=selected.missing_models,
            missing_nodes=selected.missing_nodes,
            warnings=[] if selected.executable else selected.missing_requirements,
            fallback=None,
        )

    def _active_run_for_mode(
        self,
        project_id: str,
        shot_id: str,
        mode: QuickGenerateMode,
    ):
        if mode in (QuickGenerateMode.FIRST_FRAME, QuickGenerateMode.END_FRAME):
            return self.repository.get_active_keyframe_run_for_purpose(
                project_id,
                shot_id,
                mode.value,
            )
        return self.repository.get_active_video_run(project_id, shot_id)

    def _active_run_response(
        self,
        request_id: str,
        mode: QuickGenerateMode,
        route: WorkflowRouteResponse,
        active_run,
    ) -> QuickGenerateExecuteResponse:
        if hasattr(active_run, "keyframe_task_id"):
            return QuickGenerateExecuteResponse(
                mode=mode,
                run_type=QuickGenerateRunType.KEYFRAME,
                request_id=request_id,
                reused_active_run=True,
                task_id=active_run.keyframe_task_id,
                run_id=active_run.id,
                status=active_run.status,
                workflow_id=active_run.workflow_id,
                route=route,
            )
        return QuickGenerateExecuteResponse(
            mode=mode,
            run_type=QuickGenerateRunType.VIDEO,
            request_id=request_id,
            reused_active_run=True,
            task_id=active_run.video_task_id,
            run_id=active_run.id,
            status=active_run.status,
            workflow_id=active_run.workflow_id,
            route=route,
        )

    def _create_request_record(
        self,
        project_id: UUID,
        shot_id: UUID,
        payload: QuickGenerateExecuteRequest,
    ) -> QuickGenerateRequestRecord:
        now = utc_now()
        record = QuickGenerateRequestRecord(
            id=str(uuid4()),
            project_id=str(project_id),
            shot_id=str(shot_id),
            mode=payload.mode.value,
            request_id=payload.request_id,
            task_id=None,
            run_id=None,
            run_type=None,
            response_json=None,
            created_at=now,
            updated_at=now,
        )
        try:
            return self.repository.create_request(record)
        except IntegrityError as exc:
            raise AppError(
                code=QUICK_GENERATE_IN_PROGRESS,
                message="相同生成请求正在处理中，请稍后刷新。",
                status_code=status.HTTP_409_CONFLICT,
            ) from exc

    def _store_request_response(
        self,
        request_record: QuickGenerateRequestRecord,
        response: QuickGenerateExecuteResponse,
    ) -> None:
        try:
            self.repository.update_request(
                request_record,
                {
                    "task_id": response.task_id,
                    "run_id": response.run_id,
                    "run_type": response.run_type.value,
                    "response_json": response.model_dump_json(),
                    "updated_at": utc_now(),
                },
            )
        except SQLAlchemyError as exc:
            raise AppError(
                code=QUICK_GENERATE_CONFLICT,
                message="生成请求已启动，但幂等记录更新失败，请刷新页面查看运行记录。",
                status_code=status.HTTP_409_CONFLICT,
            ) from exc

    def _ensure_keyframe_task_has_current_references(
        self,
        project_id: UUID,
        task_id: UUID,
    ) -> None:
        task_repository = KeyframeTaskRepository(self.repository.session)
        task = task_repository.get_task(str(project_id), str(task_id))
        if task is None:
            return
        existing_shot_reference_ids = {
            reference.shot_reference_id
            for reference in task_repository.list_references(task.id)
            if reference.shot_reference_id
        }
        for shot_reference in task_repository.list_shot_references(task.shot_id):
            if shot_reference.id in existing_shot_reference_ids:
                continue
            try:
                self.keyframe_task_service.add_reference(
                    project_id,
                    task_id,
                    payload=_reference_payload(shot_reference.id),
                )
            except AppError as exc:
                if exc.code != KeyframeTaskErrorCode.REFERENCE_ALREADY_EXISTS.value:
                    raise

    def _mark_quick_keyframe_task_ready(
        self,
        project_id: UUID,
        task_id: UUID,
    ):
        task_repository = KeyframeTaskRepository(self.repository.session)
        task = task_repository.get_task(str(project_id), str(task_id))
        if task is None:
            return self.keyframe_task_service.get_task(project_id, task_id)
        if task.status != KeyframeTaskStatus.READY.value:
            task_repository.update_task(
                task,
                {"status": KeyframeTaskStatus.READY.value, "updated_at": utc_now()},
            )
        return self.keyframe_task_service.get_task(project_id, task_id)

    def _get_shot(self, project_id: UUID, shot_id: UUID):
        shot = self.repository.get_shot(str(project_id), str(shot_id))
        if shot is None:
            raise AppError(
                code="shot_not_found",
                message="镜头不存在或已被删除。",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return shot


def _reference_payload(shot_reference_id: str):
    from app.api.schemas.keyframe_task import KeyframeTaskReferenceCreateRequest

    return KeyframeTaskReferenceCreateRequest(shot_reference_id=shot_reference_id)


def _keyframe_task_name(mode: QuickGenerateMode) -> str:
    return "画布快速首帧" if mode == QuickGenerateMode.FIRST_FRAME else "画布快速尾帧"


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _required_prompt(value: str | None) -> str:
    normalized = _normalize_text(value)
    if normalized is None:
        raise AppError(
            code=QUICK_GENERATE_NOT_EXECUTABLE,
            message="请先填写生成提示词。",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return normalized


def _workflow_mode_priority(mode: QuickGenerateMode, workflow_id: str) -> int:
    if mode != QuickGenerateMode.VIDEO:
        return 0
    lowered = workflow_id.lower()
    if "flf2v" in lowered or "first_last" in lowered or "wan22" in lowered:
        return 0
    return 1


def utc_now() -> datetime:
    return datetime.now(UTC)


def _quick_generate_lock(project_id: str, shot_id: str, mode: str) -> asyncio.Lock:
    key = (project_id, shot_id, mode)
    lock = _QUICK_GENERATE_LOCKS.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _QUICK_GENERATE_LOCKS[key] = lock
    return lock


def raise_sync_unavailable() -> None:
    raise AppError(
        code=QUICK_GENERATE_SYNC_UNAVAILABLE,
        message="找不到可同步的生成结果。",
        status_code=status.HTTP_404_NOT_FOUND,
    )
