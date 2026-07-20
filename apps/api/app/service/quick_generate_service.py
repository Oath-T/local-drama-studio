import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.schemas.keyframe_task import KeyframeTaskCreateRequest, KeyframeTaskUpdateRequest
from app.api.schemas.quick_generate import (
    CanvasSyncResponse,
    QuickGenerateActiveRun,
    QuickGenerateEstimatedOutput,
    QuickGenerateExecuteRequest,
    QuickGenerateExecuteResponse,
    QuickGenerateMode,
    QuickGeneratePreviewRequest,
    QuickGeneratePreviewResponse,
    QuickGenerateResolvedInputs,
    QuickGenerateResolvedParameters,
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
from app.domain.keyframe_task import (
    KeyframeTaskErrorCode,
    KeyframeTaskPurpose,
    KeyframeTaskStatus,
)
from app.domain.media_asset import MediaType
from app.domain.video_generation import VideoInputRole
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.keyframe_generation import KeyframeGenerationOutputRecord
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
_VIDEO_DURATION_PRESETS = {
    "short_test": {"duration_seconds": 2.0, "width": 320, "height": 576, "fps": 8},
    "standard_short": {"duration_seconds": 4.0, "width": 320, "height": 576, "fps": 8},
}
_VIDEO_INPUT_ISSUE_BY_PURPOSE = {
    KeyframeTaskPurpose.FIRST_FRAME.value: {
        "missing": "adopted_first_frame",
        "multiple": "multiple_adopted_first_frame",
        "media_missing": "adopted_first_frame_media_missing",
        "not_image": "adopted_first_frame_not_image",
        "file_missing": "adopted_first_frame_file_missing",
    },
    KeyframeTaskPurpose.END_FRAME.value: {
        "missing": "adopted_end_frame",
        "multiple": "multiple_adopted_end_frame",
        "media_missing": "adopted_end_frame_media_missing",
        "not_image": "adopted_end_frame_not_image",
        "file_missing": "adopted_end_frame_file_missing",
    },
}


@dataclass(frozen=True)
class AdoptedVideoFrameInput:
    role: VideoInputRole
    output: KeyframeGenerationOutputRecord
    media_asset: MediaAssetRecord


@dataclass(frozen=True)
class AdoptedVideoInputs:
    start_frame: AdoptedVideoFrameInput | None
    end_frame: AdoptedVideoFrameInput | None
    missing_inputs: list[str]
    warnings: list[str]


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
        preview_details = self._preview_details(
            project_id=str(project_id),
            shot_id=shot.id,
            payload=payload,
            capabilities=capabilities,
            route=route,
        )
        return QuickGeneratePreviewResponse(
            mode=payload.mode,
            submitted_prompt=payload.prompt,
            submitted_negative_prompt=payload.negative_prompt,
            **preview_details,
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
                duration_preset=payload.duration_preset,
                fps=payload.fps,
                seed=payload.seed,
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
        adopted_inputs = self._resolve_adopted_video_inputs(str(project_id), str(shot_id))
        if adopted_inputs.missing_inputs or (
            adopted_inputs.start_frame is None or adopted_inputs.end_frame is None
        ):
            raise AppError(
                code=QUICK_GENERATE_NOT_EXECUTABLE,
                message="生成视频前需要先采用首帧和尾帧。",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                details={
                    **route.model_dump(mode="json"),
                    "missing_inputs": adopted_inputs.missing_inputs,
                    "warnings": adopted_inputs.warnings,
                },
            )
        inputs = [
            VideoTaskInputRequest(
                role=VideoInputRole.START_FRAME,
                source_keyframe_output_id=adopted_inputs.start_frame.output.id,
            ),
            VideoTaskInputRequest(
                role=VideoInputRole.END_FRAME,
                source_keyframe_output_id=adopted_inputs.end_frame.output.id,
            ),
        ]
        preset = _video_duration_preset(payload.duration_preset)
        fps = payload.fps if payload.fps is not None else int(preset["fps"])
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
                duration_seconds=float(preset["duration_seconds"]),
                fps=fps,
                width=int(preset["width"]),
                height=int(preset["height"]),
                seed=payload.seed,
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
            request_id=payload.request_id,
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
        warnings: list[str] = []
        if not _normalize_text(payload.prompt):
            missing_inputs.append("prompt")
        if payload.mode == QuickGenerateMode.VIDEO:
            required_inputs.extend(["adopted_first_frame", "adopted_end_frame"])
            adopted_inputs = self._resolve_adopted_video_inputs(project_id, shot_id)
            missing_inputs.extend(adopted_inputs.missing_inputs)
            warnings.extend(adopted_inputs.warnings)
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
            warnings=(
                warnings
                if selected.executable
                else sorted(warnings + selected.missing_requirements)
            ),
            fallback=None,
        )

    def _resolve_adopted_video_inputs(
        self,
        project_id: str,
        shot_id: str,
    ) -> AdoptedVideoInputs:
        start_frame, start_missing, start_warnings = self._resolve_adopted_video_frame(
            project_id,
            shot_id,
            KeyframeTaskPurpose.FIRST_FRAME.value,
            VideoInputRole.START_FRAME,
        )
        end_frame, end_missing, end_warnings = self._resolve_adopted_video_frame(
            project_id,
            shot_id,
            KeyframeTaskPurpose.END_FRAME.value,
            VideoInputRole.END_FRAME,
        )
        warnings = sorted(set(start_warnings + end_warnings))
        if (
            start_frame is not None
            and end_frame is not None
            and start_frame.media_asset.id == end_frame.media_asset.id
        ):
            warnings.append("same_start_and_end_frame")
        return AdoptedVideoInputs(
            start_frame=start_frame,
            end_frame=end_frame,
            missing_inputs=start_missing + end_missing,
            warnings=warnings,
        )

    def _resolve_adopted_video_frame(
        self,
        project_id: str,
        shot_id: str,
        purpose: str,
        role: VideoInputRole,
    ) -> tuple[AdoptedVideoFrameInput | None, list[str], list[str]]:
        issue_codes = _VIDEO_INPUT_ISSUE_BY_PURPOSE[purpose]
        selected = self.repository.list_selected_keyframe_outputs(project_id, shot_id, purpose)
        if not selected:
            return None, [issue_codes["missing"]], []
        if len(selected) > 1:
            return None, [issue_codes["multiple"]], []
        selected_output = selected[0]
        media_asset = selected_output.media_asset
        if media_asset is None:
            return None, [issue_codes["media_missing"]], []
        if (
            media_asset.media_type != MediaType.IMAGE.value
            or not media_asset.mime_type.lower().startswith("image/")
        ):
            return None, [issue_codes["not_image"]], []
        try:
            actual_metadata = self.video_generation_service.storage_service.inspect_image_file(
                media_asset.relative_path
            )
        except AppError as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                return None, [issue_codes["file_missing"]], []
            return None, [issue_codes["not_image"]], []
        except Exception:
            return None, [issue_codes["file_missing"]], []
        warnings = []
        if (
            actual_metadata.size_bytes != media_asset.size_bytes
            or actual_metadata.sha256 != media_asset.sha256
            or actual_metadata.width != media_asset.width
            or actual_metadata.height != media_asset.height
            or actual_metadata.mime_type != media_asset.mime_type
        ):
            warnings.append("media_metadata_stale")
        return (
            AdoptedVideoFrameInput(
                role=role,
                output=selected_output.output,
                media_asset=media_asset,
            ),
            [],
            warnings,
        )

    def _preview_details(
        self,
        *,
        project_id: str,
        shot_id: str,
        payload: QuickGeneratePreviewRequest,
        capabilities: list[WorkflowCapabilityResponse],
        route: WorkflowRouteResponse,
    ) -> dict[str, object]:
        selected_capability = next(
            (
                capability
                for capability in capabilities
                if capability.workflow_id == route.selected_workflow_id
            ),
            None,
        )
        active_run = self._active_run_for_mode(project_id, shot_id, payload.mode)
        active_run_response = _active_run_preview(active_run)
        blockers = _preview_blockers(route, active_run_response)
        warnings = _preview_warnings(route, payload)
        resolved_inputs = QuickGenerateResolvedInputs()
        resolved_parameters = QuickGenerateResolvedParameters()
        estimated_output = QuickGenerateEstimatedOutput()
        if payload.mode == QuickGenerateMode.VIDEO:
            adopted_inputs = self._resolve_adopted_video_inputs(project_id, shot_id)
            resolved_inputs = QuickGenerateResolvedInputs(
                start_frame_media_asset_id=(
                    adopted_inputs.start_frame.media_asset.id
                    if adopted_inputs.start_frame is not None
                    else None
                ),
                end_frame_media_asset_id=(
                    adopted_inputs.end_frame.media_asset.id
                    if adopted_inputs.end_frame is not None
                    else None
                ),
                start_frame_available=adopted_inputs.start_frame is not None,
                end_frame_available=adopted_inputs.end_frame is not None,
            )
            preset = _video_duration_preset(payload.duration_preset)
            fps = payload.fps if payload.fps is not None else int(preset["fps"])
            duration_seconds = float(preset["duration_seconds"])
            frame_count = int(duration_seconds * fps) + 1
            expected_duration = frame_count / fps
            resolved_parameters = QuickGenerateResolvedParameters(
                width=int(preset["width"]),
                height=int(preset["height"]),
                frame_count=frame_count,
                fps=fps,
                seed=payload.seed,
                expected_duration=expected_duration,
            )
            estimated_output = QuickGenerateEstimatedOutput(
                media_type="video",
                width=int(preset["width"]),
                height=int(preset["height"]),
                fps=fps,
                duration_seconds=expected_duration,
                frame_count=frame_count,
            )
        ready = not blockers
        return {
            "ready": ready,
            "can_execute": ready,
            "blockers": blockers,
            "warnings": warnings,
            "capability": selected_capability,
            "workflow_id": route.selected_workflow_id,
            "resolved_inputs": resolved_inputs,
            "resolved_parameters": resolved_parameters,
            "estimated_output": estimated_output,
            "active_run": active_run_response,
        }

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


def _video_duration_preset(value: str | None) -> dict[str, float | int]:
    return _VIDEO_DURATION_PRESETS[value or "short_test"]


def _active_run_preview(active_run) -> QuickGenerateActiveRun | None:
    if active_run is None:
        return None
    if hasattr(active_run, "keyframe_task_id"):
        return QuickGenerateActiveRun(
            run_type=QuickGenerateRunType.KEYFRAME,
            task_id=active_run.keyframe_task_id,
            run_id=active_run.id,
            status=active_run.status,
            workflow_id=active_run.workflow_id,
        )
    return QuickGenerateActiveRun(
        run_type=QuickGenerateRunType.VIDEO,
        task_id=active_run.video_task_id,
        run_id=active_run.id,
        status=active_run.status,
        workflow_id=active_run.workflow_id,
    )


def _preview_blockers(
    route: WorkflowRouteResponse,
    active_run: QuickGenerateActiveRun | None,
) -> list[str]:
    blockers: list[str] = []
    for missing_input in route.missing_inputs:
        blocker = _MISSING_INPUT_BLOCKERS.get(missing_input, missing_input)
        if blocker not in blockers:
            blockers.append(blocker)
    if route.selected_workflow_id is None:
        blockers.append("workflow_unavailable")
    if route.missing_models:
        blockers.append("missing_model")
    if route.missing_nodes:
        blockers.append("missing_node")
    if route.selected_workflow_id is not None and not route.executable and not blockers:
        blockers.append("workflow_unavailable")
    if active_run is not None:
        blockers.append("active_run_exists")
    return blockers


def _preview_warnings(
    route: WorkflowRouteResponse,
    payload: QuickGeneratePreviewRequest,
) -> list[str]:
    warnings = list(route.warnings)
    if payload.mode == QuickGenerateMode.VIDEO and "low_resolution_preset" not in warnings:
        warnings.append("low_resolution_preset")
    if not _normalize_text(payload.negative_prompt) and "no_negative_prompt" not in warnings:
        warnings.append("no_negative_prompt")
    return sorted(set(warnings))


_MISSING_INPUT_BLOCKERS = {
    "prompt": "invalid_prompt",
    "adopted_first_frame": "missing_start_frame",
    "adopted_end_frame": "missing_end_frame",
    "adopted_first_frame_file_missing": "start_frame_file_missing",
    "adopted_end_frame_file_missing": "end_frame_file_missing",
    "adopted_first_frame_not_image": "invalid_start_media_type",
    "adopted_end_frame_not_image": "invalid_end_media_type",
    "multiple_adopted_first_frame": "ambiguous_adopted_start_frame",
    "multiple_adopted_end_frame": "ambiguous_adopted_end_frame",
}


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
