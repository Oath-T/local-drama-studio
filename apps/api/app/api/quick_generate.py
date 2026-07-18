from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.api.schemas.quick_generate import (
    CanvasSyncResponse,
    QuickGenerateExecuteRequest,
    QuickGenerateExecuteResponse,
    QuickGeneratePreviewRequest,
    QuickGeneratePreviewResponse,
    QuickGenerateRunType,
    QuickGenerateSyncOutputRequest,
)
from app.infrastructure.database import get_db_session
from app.repository.keyframe_generation_repository import KeyframeGenerationRepository
from app.repository.keyframe_task_repository import KeyframeTaskRepository
from app.repository.quick_generate_repository import QuickGenerateRepository
from app.repository.video_generation_repository import VideoGenerationRepository
from app.service.canvas_output_sync_service import CanvasOutputSyncService
from app.service.keyframe_generation_runner import KeyframeGenerationRunner
from app.service.keyframe_generation_service import KeyframeGenerationService
from app.service.keyframe_task_service import KeyframeTaskService
from app.service.quick_generate_service import QuickGenerateService
from app.service.video_generation_runner import VideoGenerationRunner
from app.service.video_generation_service import VideoGenerationService
from app.service.workflow_capability_registry import WorkflowCapabilityRegistry

router = APIRouter(tags=["quick-generate"])


def get_quick_generate_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> QuickGenerateService:
    keyframe_generation_service = KeyframeGenerationService(KeyframeGenerationRepository(session))
    video_generation_service = VideoGenerationService(VideoGenerationRepository(session))
    return QuickGenerateService(
        QuickGenerateRepository(session),
        KeyframeTaskService(KeyframeTaskRepository(session)),
        keyframe_generation_service,
        video_generation_service,
        WorkflowCapabilityRegistry(keyframe_generation_service, video_generation_service),
        CanvasOutputSyncService(session),
    )


@router.post(
    "/projects/{project_id}/shots/{shot_id}/quick-generate/preview",
    response_model=QuickGeneratePreviewResponse,
)
async def preview_quick_generate(
    project_id: UUID,
    shot_id: UUID,
    payload: QuickGeneratePreviewRequest,
    service: Annotated[QuickGenerateService, Depends(get_quick_generate_service)],
) -> QuickGeneratePreviewResponse:
    return await service.preview(project_id, shot_id, payload)


@router.post(
    "/projects/{project_id}/shots/{shot_id}/quick-generate",
    response_model=QuickGenerateExecuteResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def execute_quick_generate(
    project_id: UUID,
    shot_id: UUID,
    payload: QuickGenerateExecuteRequest,
    background_tasks: BackgroundTasks,
    service: Annotated[QuickGenerateService, Depends(get_quick_generate_service)],
) -> QuickGenerateExecuteResponse:
    response = await service.execute(project_id, shot_id, payload)
    if not response.idempotent_replay and not response.reused_active_run:
        if response.run_type == QuickGenerateRunType.KEYFRAME:
            background_tasks.add_task(KeyframeGenerationRunner().run_task, response.run_id)
        else:
            background_tasks.add_task(VideoGenerationRunner().run_task, response.run_id)
    return response


@router.post(
    "/projects/{project_id}/shots/{shot_id}/quick-generate/sync-output",
    response_model=CanvasSyncResponse,
)
def sync_quick_generate_output(
    project_id: UUID,
    shot_id: UUID,
    payload: QuickGenerateSyncOutputRequest,
    service: Annotated[QuickGenerateService, Depends(get_quick_generate_service)],
) -> CanvasSyncResponse:
    return service.sync_output(project_id, shot_id, payload)
