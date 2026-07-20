from uuid import UUID

from fastapi import status

from app.api.schemas.production_status import (
    ContinuityCandidate,
    ProductionAssetStep,
    ProductionDirectorPromptStep,
    ProductionFrameStep,
    ProductionOverallStatus,
    ProductionSteps,
    ProductionVideoStep,
    ProjectProductionStatusResponse,
    ProjectProductionSummary,
    ShotProductionStatusResponse,
)
from app.core.errors import AppError
from app.domain.keyframe_generation import ACTIVE_RUN_STATUSES as KEYFRAME_ACTIVE_RUN_STATUSES
from app.domain.keyframe_task import KeyframeTaskPurpose, KeyframeTaskStatus
from app.domain.video_generation import (
    ACTIVE_VIDEO_RUN_STATUSES,
    VideoGenerationTaskStatus,
    VideoInputRole,
)
from app.infrastructure.models.keyframe_generation import (
    KeyframeGenerationOutputRecord,
)
from app.infrastructure.models.keyframe_task import KeyframeGenerationTaskRecord
from app.infrastructure.models.shot import ShotRecord
from app.infrastructure.models.video_generation import (
    VideoGenerationOutputRecord,
    VideoGenerationTaskInputRecord,
    VideoGenerationTaskRecord,
)
from app.repository.production_status_repository import (
    ProductionStatusData,
    ProductionStatusRepository,
)
from app.service.director.matcher import recommend_template_id


class ProductionStatusService:
    def __init__(self, repository: ProductionStatusRepository) -> None:
        self.repository = repository

    def get_shot_status(self, project_id: UUID, shot_id: UUID) -> ShotProductionStatusResponse:
        data = self.repository.load_shot(str(project_id), str(shot_id))
        if data is None:
            if not self.repository.project_exists(str(project_id)):
                raise AppError(
                    code="PROJECT_NOT_FOUND",
                    message="项目不存在或已被删除。",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            raise AppError(
                code="SHOT_NOT_FOUND",
                message="镜头不存在或已被删除。",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        for index, shot in enumerate(data.shots):
            if shot.id == str(shot_id):
                return self._shot_status(data, shot, index)
        raise AppError(
            code="SHOT_NOT_FOUND",
            message="镜头不存在或已被删除。",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    def list_project_status(self, project_id: UUID) -> ProjectProductionStatusResponse:
        if not self.repository.project_exists(str(project_id)):
            raise AppError(
                code="PROJECT_NOT_FOUND",
                message="项目不存在或已被删除。",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        data = self.repository.load_project(str(project_id))
        shots = [self._shot_status(data, shot, index) for index, shot in enumerate(data.shots)]
        counts: dict[ProductionOverallStatus, int] = {
            "blocked": 0,
            "in_progress": 0,
            "ready_for_video": 0,
            "completed": 0,
        }
        for item in shots:
            counts[item.overall_status] += 1
        return ProjectProductionStatusResponse(
            summary=ProjectProductionSummary(
                total_shots=len(shots),
                blocked=counts["blocked"],
                in_progress=counts["in_progress"],
                ready_for_video=counts["ready_for_video"],
                completed=counts["completed"],
            ),
            shots=shots,
        )

    def _shot_status(
        self,
        data: ProductionStatusData,
        shot: ShotRecord,
        shot_index: int,
    ) -> ShotProductionStatusResponse:
        keyframe_tasks = data.keyframe_tasks_by_shot.get(shot.id, [])
        video_tasks = data.video_tasks_by_shot.get(shot.id, [])
        first_frame = self._frame_step(
            keyframe_tasks,
            data,
            KeyframeTaskPurpose.FIRST_FRAME.value,
        )
        end_frame = self._frame_step(
            keyframe_tasks,
            data,
            KeyframeTaskPurpose.END_FRAME.value,
        )
        video = self._video_step(video_tasks, data, first_frame, end_frame)
        assets = self._asset_step(data, shot)
        director_prompt = ProductionDirectorPromptStep(
            status="available",
            director_template_available=True,
            recommended_template_id=recommend_template_id(shot),
        )
        blockers = self._blockers(assets, first_frame, end_frame, video)
        overall = self._overall_status(assets, first_frame, end_frame, video)
        return ShotProductionStatusResponse(
            shot_id=shot.id,
            shot_name=shot.name,
            order_index=shot.order_index,
            character_summary=self._character_summary(data, shot),
            scene_summary=self._scene_summary(data, shot),
            overall_status=overall,
            steps=ProductionSteps(
                assets=assets,
                director_prompt=director_prompt,
                first_frame=first_frame,
                end_frame=end_frame,
                video=video,
            ),
            blockers=blockers,
            next_actions=self._next_actions(assets, first_frame, end_frame, video),
            continuity_candidate=self._continuity_candidate(data, shot_index),
        )

    def _asset_step(self, data: ProductionStatusData, shot: ShotRecord) -> ProductionAssetStep:
        warnings: list[str] = []
        if data.shot_character_counts.get(shot.id, 0) == 0:
            warnings.append("missing_characters")
        if data.primary_subject_counts.get(shot.id, 0) == 0:
            warnings.append("missing_primary_subject")
        if shot.scene_id is None:
            warnings.append("missing_scene")
        if data.shot_reference_counts.get(shot.id, 0) == 0:
            warnings.append("missing_shot_references")
        if "missing_characters" in warnings or "missing_scene" in warnings:
            return ProductionAssetStep(status="missing", warnings=warnings)
        if warnings:
            return ProductionAssetStep(status="warning", warnings=warnings)
        return ProductionAssetStep(status="complete", warnings=[])

    def _frame_step(
        self,
        tasks: list[KeyframeGenerationTaskRecord],
        data: ProductionStatusData,
        purpose: str,
    ) -> ProductionFrameStep:
        purpose_tasks = [task for task in tasks if task.purpose == purpose]
        if not purpose_tasks:
            return ProductionFrameStep(status="not_created")
        selected = self._selected_keyframe_output(purpose_tasks, data)
        if selected is not None:
            return ProductionFrameStep(
                status="adopted",
                task_id=self._task_id_for_keyframe_output(selected, data),
                adopted_output_id=selected.id,
                adopted_media_asset_id=selected.media_asset_id,
                content_url=self._content_url(selected.media_asset_id, data),
            )
        active_task = self._active_keyframe_task(purpose_tasks, data)
        if active_task is not None:
            return ProductionFrameStep(status="running", task_id=active_task.id)
        completed_task = self._completed_keyframe_task(purpose_tasks, data)
        if completed_task is not None:
            return ProductionFrameStep(status="completed", task_id=completed_task.id)
        ready_task = next(
            (task for task in purpose_tasks if task.status == KeyframeTaskStatus.READY.value), None
        )
        if ready_task is not None:
            return ProductionFrameStep(status="ready", task_id=ready_task.id)
        return ProductionFrameStep(status="draft", task_id=purpose_tasks[0].id)

    def _video_step(
        self,
        tasks: list[VideoGenerationTaskRecord],
        data: ProductionStatusData,
        first_frame: ProductionFrameStep | None = None,
        end_frame: ProductionFrameStep | None = None,
    ) -> ProductionVideoStep:
        adopted_start = first_frame is not None and first_frame.status == "adopted"
        adopted_end = end_frame is not None and end_frame.status == "adopted"
        if not tasks:
            return ProductionVideoStep(
                status="not_created",
                has_start_frame=adopted_start,
                has_end_frame=adopted_end,
            )
        selected = self._selected_video_output(tasks, data)
        task = self._task_for_video_output(selected, data) if selected is not None else tasks[0]
        inputs = data.video_inputs_by_task.get(task.id, [])
        has_start = _has_video_input(inputs, VideoInputRole.START_FRAME.value) or adopted_start
        has_end = _has_video_input(inputs, VideoInputRole.END_FRAME.value) or adopted_end
        if selected is not None:
            return ProductionVideoStep(
                status="adopted",
                task_id=task.id,
                adopted_output_id=selected.id,
                adopted_media_asset_id=selected.media_asset_id,
                content_url=self._content_url(selected.media_asset_id, data),
                has_start_frame=has_start,
                has_end_frame=has_end,
            )
        active_task = self._active_video_task(tasks, data)
        if active_task is not None:
            return ProductionVideoStep(
                status="running",
                task_id=active_task.id,
                has_start_frame=has_start,
                has_end_frame=has_end,
            )
        completed_task = self._completed_video_task(tasks, data)
        if completed_task is not None:
            return ProductionVideoStep(
                status="completed",
                task_id=completed_task.id,
                has_start_frame=has_start,
                has_end_frame=has_end,
            )
        if not has_start or not has_end:
            return ProductionVideoStep(
                status="missing_inputs",
                task_id=task.id,
                has_start_frame=has_start,
                has_end_frame=has_end,
            )
        if task.status == VideoGenerationTaskStatus.READY.value:
            return ProductionVideoStep(
                status="ready",
                task_id=task.id,
                has_start_frame=has_start,
                has_end_frame=has_end,
            )
        return ProductionVideoStep(
            status="draft",
            task_id=task.id,
            has_start_frame=has_start,
            has_end_frame=has_end,
        )

    def _overall_status(
        self,
        assets: ProductionAssetStep,
        first_frame: ProductionFrameStep,
        end_frame: ProductionFrameStep,
        video: ProductionVideoStep,
    ) -> ProductionOverallStatus:
        if video.status == "adopted":
            return "completed"
        if assets.status == "missing":
            return "blocked"
        if first_frame.status == "adopted" and end_frame.status == "adopted":
            return "ready_for_video"
        return "in_progress"

    def _blockers(
        self,
        assets: ProductionAssetStep,
        first_frame: ProductionFrameStep,
        end_frame: ProductionFrameStep,
        video: ProductionVideoStep,
    ) -> list[str]:
        blockers = list(assets.warnings if assets.status == "missing" else [])
        if video.status == "missing_inputs":
            if not video.has_start_frame:
                blockers.append("video_missing_start_frame")
            if not video.has_end_frame:
                blockers.append("video_missing_end_frame")
        if first_frame.status != "adopted":
            blockers.append("first_frame_not_adopted")
        if end_frame.status != "adopted":
            blockers.append("end_frame_not_adopted")
        return blockers

    def _next_actions(
        self,
        assets: ProductionAssetStep,
        first_frame: ProductionFrameStep,
        end_frame: ProductionFrameStep,
        video: ProductionVideoStep,
    ) -> list[str]:
        actions: list[str] = []
        if assets.status == "missing":
            actions.append("complete_assets")
        actions.append("generate_director_prompt")
        if first_frame.status == "not_created":
            actions.append("create_first_frame_task")
        elif first_frame.status == "completed":
            actions.append("select_first_frame_output")
        if first_frame.status == "adopted":
            if end_frame.status == "not_created":
                actions.append("create_end_frame_task")
            elif end_frame.status == "completed":
                actions.append("select_end_frame_output")
        if first_frame.status == "adopted" and end_frame.status == "adopted":
            if video.status == "not_created":
                actions.append("create_video_task")
            elif video.status == "missing_inputs":
                actions.append("select_video_frames")
            elif video.status == "draft":
                actions.append("mark_video_ready")
            elif video.status == "ready":
                actions.append("start_video_generation")
            elif video.status == "completed":
                actions.append("select_video_output")
        return actions

    def _continuity_candidate(
        self,
        data: ProductionStatusData,
        shot_index: int,
    ) -> ContinuityCandidate | None:
        if shot_index <= 0:
            return None
        previous = data.shots[shot_index - 1]
        video = self._video_step(data.video_tasks_by_shot.get(previous.id, []), data)
        if video.status == "adopted" and video.adopted_media_asset_id:
            return ContinuityCandidate(
                previous_shot_id=previous.id,
                previous_shot_name=previous.name,
                media_asset_id=video.adopted_media_asset_id,
                content_url=video.content_url
                or self._content_url(video.adopted_media_asset_id, data)
                or "",
                source="adopted_video",
            )
        end_frame = self._frame_step(
            data.keyframe_tasks_by_shot.get(previous.id, []),
            data,
            KeyframeTaskPurpose.END_FRAME.value,
        )
        if end_frame.status == "adopted" and end_frame.adopted_media_asset_id:
            return ContinuityCandidate(
                previous_shot_id=previous.id,
                previous_shot_name=previous.name,
                media_asset_id=end_frame.adopted_media_asset_id,
                content_url=end_frame.content_url
                or self._content_url(end_frame.adopted_media_asset_id, data)
                or "",
                source="adopted_end_frame",
            )
        return None

    def _selected_keyframe_output(
        self,
        tasks: list[KeyframeGenerationTaskRecord],
        data: ProductionStatusData,
    ) -> KeyframeGenerationOutputRecord | None:
        for task in tasks:
            for output in data.keyframe_outputs_by_task.get(task.id, []):
                if output.is_selected:
                    return output
        return None

    def _selected_video_output(
        self,
        tasks: list[VideoGenerationTaskRecord],
        data: ProductionStatusData,
    ) -> VideoGenerationOutputRecord | None:
        for task in tasks:
            for output in data.video_outputs_by_task.get(task.id, []):
                if output.is_selected:
                    return output
        return None

    def _active_keyframe_task(
        self,
        tasks: list[KeyframeGenerationTaskRecord],
        data: ProductionStatusData,
    ) -> KeyframeGenerationTaskRecord | None:
        return next(
            (
                task
                for task in tasks
                if any(
                    run.status in KEYFRAME_ACTIVE_RUN_STATUSES
                    for run in data.keyframe_runs_by_task.get(task.id, [])
                )
            ),
            None,
        )

    def _active_video_task(
        self,
        tasks: list[VideoGenerationTaskRecord],
        data: ProductionStatusData,
    ) -> VideoGenerationTaskRecord | None:
        return next(
            (
                task
                for task in tasks
                if any(
                    run.status in ACTIVE_VIDEO_RUN_STATUSES
                    for run in data.video_runs_by_task.get(task.id, [])
                )
            ),
            None,
        )

    def _completed_keyframe_task(
        self,
        tasks: list[KeyframeGenerationTaskRecord],
        data: ProductionStatusData,
    ) -> KeyframeGenerationTaskRecord | None:
        return next(
            (
                task
                for task in tasks
                if data.keyframe_outputs_by_task.get(task.id)
                or any(
                    run.status == "completed" for run in data.keyframe_runs_by_task.get(task.id, [])
                )
            ),
            None,
        )

    def _completed_video_task(
        self,
        tasks: list[VideoGenerationTaskRecord],
        data: ProductionStatusData,
    ) -> VideoGenerationTaskRecord | None:
        return next(
            (
                task
                for task in tasks
                if data.video_outputs_by_task.get(task.id)
                or any(
                    run.status == "completed" for run in data.video_runs_by_task.get(task.id, [])
                )
            ),
            None,
        )

    def _task_id_for_keyframe_output(
        self,
        output: KeyframeGenerationOutputRecord,
        data: ProductionStatusData,
    ) -> str | None:
        for task_id, outputs in data.keyframe_outputs_by_task.items():
            if any(item.id == output.id for item in outputs):
                return task_id
        return None

    def _task_for_video_output(
        self,
        output: VideoGenerationOutputRecord | None,
        data: ProductionStatusData,
    ) -> VideoGenerationTaskRecord | None:
        if output is None:
            return None
        for task_id, outputs in data.video_outputs_by_task.items():
            if any(item.id == output.id for item in outputs):
                for tasks in data.video_tasks_by_shot.values():
                    for task in tasks:
                        if task.id == task_id:
                            return task
        return None

    def _content_url(self, media_asset_id: str | None, data: ProductionStatusData) -> str | None:
        if media_asset_id is None or media_asset_id not in data.media_assets:
            return None
        return f"/api/media/{media_asset_id}/content"

    def _character_summary(self, data: ProductionStatusData, shot: ShotRecord) -> str | None:
        names = data.character_names_by_shot.get(shot.id, [])
        if not names:
            return None
        return "、".join(names[:3]) + (" 等" if len(names) > 3 else "")

    def _scene_summary(self, data: ProductionStatusData, shot: ShotRecord) -> str | None:
        parts: list[str] = []
        if shot.scene_id and shot.scene_id in data.scenes:
            parts.append(data.scenes[shot.scene_id].name)
        if shot.scene_state_id and shot.scene_state_id in data.scene_states:
            parts.append(data.scene_states[shot.scene_state_id].name)
        return " / ".join(parts) if parts else None


def _has_video_input(inputs: list[VideoGenerationTaskInputRecord], role: str) -> bool:
    return any(item.role == role and item.media_asset_id for item in inputs)
