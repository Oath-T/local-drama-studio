from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.schemas.project_canvas import (
    CanvasEdgeCreateRequest,
    CanvasEntityBatchPreview,
    CanvasEntityBatchRequest,
    CanvasNodeCreateRequest,
    CanvasNodePatchRequest,
    ProjectCanvasResponse,
    ProjectCanvasSaveRequest,
)
from app.infrastructure.database import get_db_session
from app.service.project_canvas_service import ProjectCanvasService

router = APIRouter(prefix="/projects/{project_id}/canvas", tags=["project-canvas"])


def get_project_canvas_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ProjectCanvasService:
    return ProjectCanvasService(session)


@router.get("", response_model=ProjectCanvasResponse)
def get_project_canvas(
    project_id: UUID,
    service: Annotated[ProjectCanvasService, Depends(get_project_canvas_service)],
) -> ProjectCanvasResponse:
    return service.get_canvas(project_id)


@router.put("", response_model=ProjectCanvasResponse)
def save_project_canvas(
    project_id: UUID,
    payload: ProjectCanvasSaveRequest,
    service: Annotated[ProjectCanvasService, Depends(get_project_canvas_service)],
) -> ProjectCanvasResponse:
    return service.save_canvas(project_id, payload)


@router.post("/nodes", response_model=ProjectCanvasResponse, status_code=status.HTTP_201_CREATED)
def create_canvas_node(
    project_id: UUID,
    payload: CanvasNodeCreateRequest,
    service: Annotated[ProjectCanvasService, Depends(get_project_canvas_service)],
) -> ProjectCanvasResponse:
    return service.create_node(project_id, payload)


@router.patch("/nodes/{node_id}", response_model=ProjectCanvasResponse)
def patch_canvas_node(
    project_id: UUID,
    node_id: UUID,
    payload: CanvasNodePatchRequest,
    service: Annotated[ProjectCanvasService, Depends(get_project_canvas_service)],
) -> ProjectCanvasResponse:
    return service.patch_node(project_id, node_id, payload)


@router.delete("/nodes/{node_id}", response_model=ProjectCanvasResponse)
def delete_canvas_node(
    project_id: UUID,
    node_id: UUID,
    expected_revision: Annotated[int, Query(ge=1)],
    service: Annotated[ProjectCanvasService, Depends(get_project_canvas_service)],
) -> ProjectCanvasResponse:
    return service.delete_node(project_id, node_id, expected_revision)


@router.post("/edges", response_model=ProjectCanvasResponse, status_code=status.HTTP_201_CREATED)
def create_canvas_edge(
    project_id: UUID,
    payload: CanvasEdgeCreateRequest,
    service: Annotated[ProjectCanvasService, Depends(get_project_canvas_service)],
) -> ProjectCanvasResponse:
    return service.create_edge(project_id, payload)


@router.delete("/edges/{edge_id}", response_model=ProjectCanvasResponse)
def delete_canvas_edge(
    project_id: UUID,
    edge_id: UUID,
    expected_revision: Annotated[int, Query(ge=1)],
    service: Annotated[ProjectCanvasService, Depends(get_project_canvas_service)],
) -> ProjectCanvasResponse:
    return service.delete_edge(project_id, edge_id, expected_revision)


@router.get("/entity-batch-preview", response_model=CanvasEntityBatchPreview)
def preview_canvas_entity_batch(
    project_id: UUID,
    service: Annotated[ProjectCanvasService, Depends(get_project_canvas_service)],
) -> CanvasEntityBatchPreview:
    return service.preview_existing_entities(project_id)


@router.post("/entity-batch", response_model=ProjectCanvasResponse)
def add_canvas_entity_batch(
    project_id: UUID,
    payload: CanvasEntityBatchRequest,
    service: Annotated[ProjectCanvasService, Depends(get_project_canvas_service)],
) -> ProjectCanvasResponse:
    return service.add_existing_entities(project_id, payload)
