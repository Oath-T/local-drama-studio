from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.api.schemas.video_generation import (
    VideoInputUploadResponse,
    VideoOutputResponse,
    VideoRunCreateRequest,
    VideoRunCreateResponse,
    VideoRunListResponse,
    VideoRunResponse,
    VideoTaskCreateRequest,
    VideoTaskListResponse,
    VideoTaskResponse,
    VideoTaskUpdateRequest,
    VideoWorkflowListResponse,
)
from app.infrastructure.database import get_db_session
from app.repository.video_generation_repository import VideoGenerationRepository
from app.service.video_generation_runner import VideoGenerationRunner
from app.service.video_generation_service import VideoGenerationService

router = APIRouter(tags=["video-generation"])


def get_video_generation_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> VideoGenerationService:
    return VideoGenerationService(VideoGenerationRepository(session))


@router.get(
    "/projects/{project_id}/video-workflows",
    response_model=VideoWorkflowListResponse,
)
async def list_video_workflows(
    project_id: UUID,
    service: Annotated[VideoGenerationService, Depends(get_video_generation_service)],
) -> VideoWorkflowListResponse:
    return await service.list_workflows(project_id)


@router.get(
    "/projects/{project_id}/shots/{shot_id}/video-tasks",
    response_model=VideoTaskListResponse,
)
def list_video_tasks(
    project_id: UUID,
    shot_id: UUID,
    service: Annotated[VideoGenerationService, Depends(get_video_generation_service)],
) -> VideoTaskListResponse:
    return service.list_tasks(project_id, shot_id)


@router.post(
    "/projects/{project_id}/shots/{shot_id}/video-tasks",
    response_model=VideoTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_video_task(
    project_id: UUID,
    shot_id: UUID,
    payload: VideoTaskCreateRequest,
    service: Annotated[VideoGenerationService, Depends(get_video_generation_service)],
) -> VideoTaskResponse:
    return service.create_task(project_id, shot_id, payload)


@router.get(
    "/projects/{project_id}/video-tasks/{task_id}",
    response_model=VideoTaskResponse,
)
def get_video_task(
    project_id: UUID,
    task_id: UUID,
    service: Annotated[VideoGenerationService, Depends(get_video_generation_service)],
) -> VideoTaskResponse:
    return service.get_task(project_id, task_id)


@router.patch(
    "/projects/{project_id}/video-tasks/{task_id}",
    response_model=VideoTaskResponse,
)
def update_video_task(
    project_id: UUID,
    task_id: UUID,
    payload: VideoTaskUpdateRequest,
    service: Annotated[VideoGenerationService, Depends(get_video_generation_service)],
) -> VideoTaskResponse:
    return service.update_task(project_id, task_id, payload)


@router.delete(
    "/projects/{project_id}/video-tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_video_task(
    project_id: UUID,
    task_id: UUID,
    service: Annotated[VideoGenerationService, Depends(get_video_generation_service)],
) -> None:
    service.delete_task(project_id, task_id)


@router.post(
    "/projects/{project_id}/video-tasks/{task_id}/mark-ready",
    response_model=VideoTaskResponse,
)
async def mark_video_task_ready(
    project_id: UUID,
    task_id: UUID,
    service: Annotated[VideoGenerationService, Depends(get_video_generation_service)],
) -> VideoTaskResponse:
    return await service.mark_ready(project_id, task_id)


@router.post(
    "/projects/{project_id}/video-tasks/{task_id}/mark-draft",
    response_model=VideoTaskResponse,
)
def mark_video_task_draft(
    project_id: UUID,
    task_id: UUID,
    service: Annotated[VideoGenerationService, Depends(get_video_generation_service)],
) -> VideoTaskResponse:
    return service.mark_draft(project_id, task_id)


@router.post(
    "/projects/{project_id}/video-tasks/{task_id}/runs",
    response_model=VideoRunCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_video_run(
    project_id: UUID,
    task_id: UUID,
    payload: VideoRunCreateRequest,
    background_tasks: BackgroundTasks,
    service: Annotated[VideoGenerationService, Depends(get_video_generation_service)],
) -> VideoRunCreateResponse:
    run = await service.create_run(project_id, task_id, payload.workflow_id)
    background_tasks.add_task(VideoGenerationRunner().run_task, run.run_id)
    return run


@router.get(
    "/projects/{project_id}/video-tasks/{task_id}/runs",
    response_model=VideoRunListResponse,
)
def list_video_runs(
    project_id: UUID,
    task_id: UUID,
    service: Annotated[VideoGenerationService, Depends(get_video_generation_service)],
) -> VideoRunListResponse:
    return service.list_runs(project_id, task_id)


@router.get(
    "/projects/{project_id}/video-runs/{run_id}",
    response_model=VideoRunResponse,
)
def get_video_run(
    project_id: UUID,
    run_id: UUID,
    service: Annotated[VideoGenerationService, Depends(get_video_generation_service)],
) -> VideoRunResponse:
    return service.get_run(project_id, run_id)


@router.post(
    "/projects/{project_id}/video-outputs/{output_id}/select",
    response_model=VideoOutputResponse,
)
def select_video_output(
    project_id: UUID,
    output_id: UUID,
    service: Annotated[VideoGenerationService, Depends(get_video_generation_service)],
) -> VideoOutputResponse:
    return service.select_output(project_id, output_id)


@router.delete(
    "/projects/{project_id}/video-outputs/{output_id}/select",
    response_model=VideoOutputResponse,
)
def unselect_video_output(
    project_id: UUID,
    output_id: UUID,
    service: Annotated[VideoGenerationService, Depends(get_video_generation_service)],
) -> VideoOutputResponse:
    return service.unselect_output(project_id, output_id)


@router.post(
    "/projects/{project_id}/video-inputs/images",
    response_model=VideoInputUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_video_input_image(
    project_id: UUID,
    service: Annotated[VideoGenerationService, Depends(get_video_generation_service)],
    file: Annotated[UploadFile, File()],
) -> VideoInputUploadResponse:
    return await service.upload_input_image(project_id, file)
