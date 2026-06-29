from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.schemas.keyframe_task import (
    KeyframeTaskCreateRequest,
    KeyframeTaskListResponse,
    KeyframeTaskReferenceCreateRequest,
    KeyframeTaskReferenceListResponse,
    KeyframeTaskReferenceUpdateRequest,
    KeyframeTaskResponse,
    KeyframeTaskUpdateRequest,
)
from app.infrastructure.database import get_db_session
from app.repository.keyframe_task_repository import KeyframeTaskRepository
from app.service.keyframe_task_service import KeyframeTaskService

router = APIRouter(tags=["keyframe-tasks"])


def get_keyframe_task_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> KeyframeTaskService:
    repository = KeyframeTaskRepository(session)
    return KeyframeTaskService(repository)


@router.get(
    "/projects/{project_id}/shots/{shot_id}/keyframe-tasks",
    response_model=KeyframeTaskListResponse,
)
def list_keyframe_tasks(
    project_id: UUID,
    shot_id: UUID,
    service: Annotated[KeyframeTaskService, Depends(get_keyframe_task_service)],
) -> KeyframeTaskListResponse:
    return service.list_tasks(project_id, shot_id)


@router.post(
    "/projects/{project_id}/shots/{shot_id}/keyframe-tasks",
    response_model=KeyframeTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_keyframe_task(
    project_id: UUID,
    shot_id: UUID,
    payload: KeyframeTaskCreateRequest,
    service: Annotated[KeyframeTaskService, Depends(get_keyframe_task_service)],
) -> KeyframeTaskResponse:
    return service.create_task(project_id, shot_id, payload)


@router.get(
    "/projects/{project_id}/keyframe-tasks/{task_id}",
    response_model=KeyframeTaskResponse,
)
def get_keyframe_task(
    project_id: UUID,
    task_id: UUID,
    service: Annotated[KeyframeTaskService, Depends(get_keyframe_task_service)],
) -> KeyframeTaskResponse:
    return service.get_task(project_id, task_id)


@router.patch(
    "/projects/{project_id}/keyframe-tasks/{task_id}",
    response_model=KeyframeTaskResponse,
)
def update_keyframe_task(
    project_id: UUID,
    task_id: UUID,
    payload: KeyframeTaskUpdateRequest,
    service: Annotated[KeyframeTaskService, Depends(get_keyframe_task_service)],
) -> KeyframeTaskResponse:
    return service.update_task(project_id, task_id, payload)


@router.delete(
    "/projects/{project_id}/keyframe-tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_keyframe_task(
    project_id: UUID,
    task_id: UUID,
    service: Annotated[KeyframeTaskService, Depends(get_keyframe_task_service)],
) -> Response:
    service.delete_task(project_id, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/projects/{project_id}/keyframe-tasks/{task_id}/duplicate",
    response_model=KeyframeTaskResponse,
)
def duplicate_keyframe_task(
    project_id: UUID,
    task_id: UUID,
    service: Annotated[KeyframeTaskService, Depends(get_keyframe_task_service)],
) -> KeyframeTaskResponse:
    return service.duplicate_task(project_id, task_id)


@router.post(
    "/projects/{project_id}/keyframe-tasks/{task_id}/mark-ready",
    response_model=KeyframeTaskResponse,
)
def mark_keyframe_task_ready(
    project_id: UUID,
    task_id: UUID,
    service: Annotated[KeyframeTaskService, Depends(get_keyframe_task_service)],
) -> KeyframeTaskResponse:
    return service.mark_ready(project_id, task_id)


@router.post(
    "/projects/{project_id}/keyframe-tasks/{task_id}/mark-draft",
    response_model=KeyframeTaskResponse,
)
def mark_keyframe_task_draft(
    project_id: UUID,
    task_id: UUID,
    service: Annotated[KeyframeTaskService, Depends(get_keyframe_task_service)],
) -> KeyframeTaskResponse:
    return service.mark_draft(project_id, task_id)


@router.get(
    "/projects/{project_id}/keyframe-tasks/{task_id}/references",
    response_model=KeyframeTaskReferenceListResponse,
)
def list_keyframe_task_references(
    project_id: UUID,
    task_id: UUID,
    service: Annotated[KeyframeTaskService, Depends(get_keyframe_task_service)],
) -> KeyframeTaskReferenceListResponse:
    return service.list_references(project_id, task_id)


@router.post(
    "/projects/{project_id}/keyframe-tasks/{task_id}/references",
    response_model=KeyframeTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_keyframe_task_reference(
    project_id: UUID,
    task_id: UUID,
    payload: KeyframeTaskReferenceCreateRequest,
    service: Annotated[KeyframeTaskService, Depends(get_keyframe_task_service)],
) -> KeyframeTaskResponse:
    return service.add_reference(project_id, task_id, payload)


@router.patch(
    "/projects/{project_id}/keyframe-tasks/{task_id}/references/{task_reference_id}",
    response_model=KeyframeTaskResponse,
)
def update_keyframe_task_reference(
    project_id: UUID,
    task_id: UUID,
    task_reference_id: UUID,
    payload: KeyframeTaskReferenceUpdateRequest,
    service: Annotated[KeyframeTaskService, Depends(get_keyframe_task_service)],
) -> KeyframeTaskResponse:
    return service.update_reference(project_id, task_id, task_reference_id, payload)


@router.delete(
    "/projects/{project_id}/keyframe-tasks/{task_id}/references/{task_reference_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_keyframe_task_reference(
    project_id: UUID,
    task_id: UUID,
    task_reference_id: UUID,
    service: Annotated[KeyframeTaskService, Depends(get_keyframe_task_service)],
) -> Response:
    service.delete_reference(project_id, task_id, task_reference_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
