from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.schemas.project import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.infrastructure.database import get_db_session
from app.repository.project_repository import ProjectRepository
from app.service.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ProjectService:
    return ProjectService(ProjectRepository(session))


@router.get("", response_model=ProjectListResponse)
def list_projects(
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectListResponse:
    projects, total = service.list_projects()
    return ProjectListResponse(items=projects, total=total)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreateRequest,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    return service.create_project(payload)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    return service.get_project(project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    payload: ProjectUpdateRequest,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    return service.update_project(project_id, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> Response:
    service.delete_project(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
