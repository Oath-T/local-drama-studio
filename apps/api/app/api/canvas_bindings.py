from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.canvas_binding import (
    CanvasBindingApplyRequest,
    CanvasBindingDeleteRequest,
    CanvasBindingPreviewRequest,
    CanvasBindingPreviewResponse,
)
from app.api.schemas.project_canvas import ProjectCanvasResponse
from app.infrastructure.database import get_db_session
from app.service.canvas_binding_service import CanvasBindingService

router = APIRouter(prefix="/projects/{project_id}/canvas", tags=["canvas-bindings"])


def get_canvas_binding_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> CanvasBindingService:
    return CanvasBindingService(session)


@router.post("/bindings/preview", response_model=CanvasBindingPreviewResponse)
def preview_canvas_binding(
    project_id: UUID,
    payload: CanvasBindingPreviewRequest,
    service: Annotated[CanvasBindingService, Depends(get_canvas_binding_service)],
) -> CanvasBindingPreviewResponse:
    return service.preview_binding(project_id, payload)


@router.post("/bindings/apply", response_model=ProjectCanvasResponse)
def apply_canvas_binding(
    project_id: UUID,
    payload: CanvasBindingApplyRequest,
    service: Annotated[CanvasBindingService, Depends(get_canvas_binding_service)],
) -> ProjectCanvasResponse:
    return service.apply_binding(project_id, payload)


@router.delete("/bindings/{edge_id}", response_model=ProjectCanvasResponse)
def delete_canvas_binding(
    project_id: UUID,
    edge_id: UUID,
    payload: CanvasBindingDeleteRequest,
    service: Annotated[CanvasBindingService, Depends(get_canvas_binding_service)],
) -> ProjectCanvasResponse:
    return service.delete_binding(project_id, edge_id, payload)


@router.get("/import-business-relations/preview")
def preview_canvas_business_relations_import(
    project_id: UUID,
    service: Annotated[CanvasBindingService, Depends(get_canvas_binding_service)],
) -> dict[str, int]:
    return service.import_business_relations_preview(project_id)


@router.post("/import-business-relations", response_model=ProjectCanvasResponse)
def import_canvas_business_relations(
    project_id: UUID,
    expected_revision: int,
    service: Annotated[CanvasBindingService, Depends(get_canvas_binding_service)],
) -> ProjectCanvasResponse:
    return service.import_business_relations(project_id, expected_revision)
