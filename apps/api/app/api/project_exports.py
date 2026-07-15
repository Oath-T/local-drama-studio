from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.api.schemas.project_export import (
    ProjectExportCreateRequest,
    ProjectExportListResponse,
    ProjectExportResponse,
    ProjectExportStartResponse,
)
from app.infrastructure.database import get_db_session
from app.service.export.export_runner import run_project_export
from app.service.project_export_service import ProjectExportService

router = APIRouter(prefix="/projects/{project_id}/exports", tags=["project-exports"])


def get_project_export_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ProjectExportService:
    return ProjectExportService(session)


@router.get("", response_model=ProjectExportListResponse)
def list_project_exports(
    project_id: UUID,
    service: Annotated[ProjectExportService, Depends(get_project_export_service)],
) -> ProjectExportListResponse:
    return service.list_exports(project_id)


@router.post("", response_model=ProjectExportResponse, status_code=status.HTTP_201_CREATED)
def create_project_export(
    project_id: UUID,
    payload: ProjectExportCreateRequest,
    service: Annotated[ProjectExportService, Depends(get_project_export_service)],
) -> ProjectExportResponse:
    return service.create_export(project_id, payload)


@router.get("/{export_id}", response_model=ProjectExportResponse)
def get_project_export(
    project_id: UUID,
    export_id: UUID,
    service: Annotated[ProjectExportService, Depends(get_project_export_service)],
) -> ProjectExportResponse:
    return service.get_export(project_id, export_id)


@router.post("/{export_id}/mark-ready", response_model=ProjectExportResponse)
def mark_project_export_ready(
    project_id: UUID,
    export_id: UUID,
    service: Annotated[ProjectExportService, Depends(get_project_export_service)],
) -> ProjectExportResponse:
    return service.mark_ready(project_id, export_id)


@router.post("/{export_id}/start", response_model=ProjectExportStartResponse)
def start_project_export(
    project_id: UUID,
    export_id: UUID,
    background_tasks: BackgroundTasks,
    service: Annotated[ProjectExportService, Depends(get_project_export_service)],
) -> ProjectExportStartResponse:
    response = service.start(project_id, export_id)
    background_tasks.add_task(run_project_export, response.id)
    return response
