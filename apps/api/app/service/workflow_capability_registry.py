from datetime import UTC, datetime
from uuid import UUID

from app.api.schemas.keyframe_generation import KeyframeWorkflowResponse
from app.api.schemas.quick_generate import (
    QuickGenerateMode,
    QuickGenerateRunType,
    WorkflowCapabilityResponse,
    WorkflowQualityTier,
    WorkflowSpeedTier,
)
from app.api.schemas.video_generation import VideoWorkflowResponse
from app.service.keyframe_generation_service import KeyframeGenerationService
from app.service.video_generation_service import VideoGenerationService


class WorkflowCapabilityRegistry:
    def __init__(
        self,
        keyframe_service: KeyframeGenerationService,
        video_service: VideoGenerationService,
    ) -> None:
        self.keyframe_service = keyframe_service
        self.video_service = video_service

    async def list_capabilities(self, project_id: UUID) -> list[WorkflowCapabilityResponse]:
        keyframe_workflows = await self.keyframe_service.list_workflows(project_id)
        video_workflows = await self.video_service.list_workflows(project_id)
        checked_at = datetime.now(UTC)
        capabilities = [
            self._keyframe_capability(workflow, checked_at) for workflow in keyframe_workflows.items
        ] + [self._video_capability(workflow, checked_at) for workflow in video_workflows.items]
        return sorted(capabilities, key=lambda item: (item.task_type.value, item.workflow_id))

    def _keyframe_capability(
        self,
        workflow: KeyframeWorkflowResponse,
        checked_at: datetime,
    ) -> WorkflowCapabilityResponse:
        missing_models, missing_nodes = _split_missing_requirements(workflow.missing_requirements)
        return WorkflowCapabilityResponse(
            workflow_id=workflow.workflow_id,
            display_name=workflow.display_name,
            task_type=QuickGenerateRunType.KEYFRAME,
            supports=[QuickGenerateMode.FIRST_FRAME, QuickGenerateMode.END_FRAME],
            requires=["prompt", "shot_references"],
            recommended_for=["first_frame", "end_frame"],
            executable=workflow.available,
            missing_models=missing_models,
            missing_nodes=missing_nodes,
            missing_requirements=workflow.missing_requirements,
            quality_tier=WorkflowQualityTier.BASIC,
            speed_tier=WorkflowSpeedTier.NORMAL,
            visual_only=False,
            available=workflow.available,
            blockers=workflow.missing_requirements,
            checked_at=checked_at,
        )

    def _video_capability(
        self,
        workflow: VideoWorkflowResponse,
        checked_at: datetime,
    ) -> WorkflowCapabilityResponse:
        missing_models, missing_nodes = _split_missing_requirements(workflow.missing_requirements)
        return WorkflowCapabilityResponse(
            workflow_id=workflow.workflow_id,
            display_name=workflow.display_name,
            task_type=QuickGenerateRunType.VIDEO,
            supports=[QuickGenerateMode.VIDEO],
            requires=["adopted_first_frame", "adopted_end_frame"],
            recommended_for=["video"],
            executable=workflow.available,
            missing_models=missing_models,
            missing_nodes=missing_nodes,
            missing_requirements=workflow.missing_requirements,
            quality_tier=WorkflowQualityTier.PRODUCTION,
            speed_tier=WorkflowSpeedTier.SLOW,
            visual_only=False,
            available=workflow.available,
            blockers=workflow.missing_requirements,
            checked_at=checked_at,
        )


def _split_missing_requirements(requirements: list[str]) -> tuple[list[str], list[str]]:
    missing_models: list[str] = []
    missing_nodes: list[str] = []
    for item in requirements:
        if item.startswith("model_file_missing:") or item == "default_checkpoint_not_configured":
            missing_models.append(item)
        elif item.startswith("node_type_missing:") or item == "required_node_types_unavailable":
            missing_nodes.append(item)
    return sorted(set(missing_models)), sorted(set(missing_nodes))
