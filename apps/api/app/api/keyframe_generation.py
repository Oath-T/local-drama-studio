from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.api.schemas.keyframe_generation import (
    KeyframeOutputResponse,
    KeyframeRunCreateRequest,
    KeyframeRunCreateResponse,
    KeyframeRunListResponse,
    KeyframeRunResponse,
    KeyframeWorkflowListResponse,
)
from app.infrastructure.database import get_db_session
from app.repository.keyframe_generation_repository import KeyframeGenerationRepository
from app.service.keyframe_generation_runner import KeyframeGenerationRunner
from app.service.keyframe_generation_service import KeyframeGenerationService

router = APIRouter(tags=["keyframe-generation"])


def get_keyframe_generation_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> KeyframeGenerationService:
    return KeyframeGenerationService(KeyframeGenerationRepository(session))


@router.get(
    "/projects/{project_id}/keyframe-workflows",
    response_model=KeyframeWorkflowListResponse,
)
async def list_keyframe_workflows(
    project_id: UUID,
    service: Annotated[KeyframeGenerationService, Depends(get_keyframe_generation_service)],
) -> KeyframeWorkflowListResponse:
    return await service.list_workflows(project_id)


@router.post(
    "/projects/{project_id}/keyframe-tasks/{task_id}/runs",
    response_model=KeyframeRunCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_keyframe_run(
    project_id: UUID,
    task_id: UUID,
    payload: KeyframeRunCreateRequest,
    background_tasks: BackgroundTasks,
    service: Annotated[KeyframeGenerationService, Depends(get_keyframe_generation_service)],
) -> KeyframeRunCreateResponse:
    run = await service.create_run(project_id, task_id, payload.workflow_id)
    background_tasks.add_task(KeyframeGenerationRunner().run_task, run.run_id)
    return run


@router.get(
    "/projects/{project_id}/keyframe-tasks/{task_id}/runs",
    response_model=KeyframeRunListResponse,
)
def list_keyframe_runs(
    project_id: UUID,
    task_id: UUID,
    service: Annotated[KeyframeGenerationService, Depends(get_keyframe_generation_service)],
) -> KeyframeRunListResponse:
    return service.list_runs(project_id, task_id)


@router.get(
    "/projects/{project_id}/keyframe-runs/{run_id}",
    response_model=KeyframeRunResponse,
)
def get_keyframe_run(
    project_id: UUID,
    run_id: UUID,
    service: Annotated[KeyframeGenerationService, Depends(get_keyframe_generation_service)],
) -> KeyframeRunResponse:
    return service.get_run(project_id, run_id)


@router.post(
    "/projects/{project_id}/keyframe-runs/{run_id}/retry",
    response_model=KeyframeRunCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_keyframe_run(
    project_id: UUID,
    run_id: UUID,
    background_tasks: BackgroundTasks,
    service: Annotated[KeyframeGenerationService, Depends(get_keyframe_generation_service)],
) -> KeyframeRunCreateResponse:
    run = await service.retry_run(project_id, run_id)
    background_tasks.add_task(KeyframeGenerationRunner().run_task, run.run_id)
    return run


@router.post(
    "/projects/{project_id}/keyframe-outputs/{output_id}/select",
    response_model=KeyframeOutputResponse,
)
def select_keyframe_output(
    project_id: UUID,
    output_id: UUID,
    service: Annotated[KeyframeGenerationService, Depends(get_keyframe_generation_service)],
) -> KeyframeOutputResponse:
    return service.select_output(project_id, output_id)


@router.delete(
    "/projects/{project_id}/keyframe-outputs/{output_id}/select",
    response_model=KeyframeOutputResponse,
)
def unselect_keyframe_output(
    project_id: UUID,
    output_id: UUID,
    service: Annotated[KeyframeGenerationService, Depends(get_keyframe_generation_service)],
) -> KeyframeOutputResponse:
    return service.unselect_output(project_id, output_id)
