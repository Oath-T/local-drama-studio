from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.production_status import (
    ProjectProductionStatusResponse,
    ShotProductionStatusResponse,
)
from app.infrastructure.database import get_db_session
from app.repository.production_status_repository import ProductionStatusRepository
from app.service.production_status_service import ProductionStatusService

router = APIRouter(tags=["production-status"])


def get_production_status_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ProductionStatusService:
    return ProductionStatusService(ProductionStatusRepository(session))


@router.get(
    "/projects/{project_id}/production-status",
    response_model=ProjectProductionStatusResponse,
)
def get_project_production_status(
    project_id: UUID,
    service: Annotated[ProductionStatusService, Depends(get_production_status_service)],
) -> ProjectProductionStatusResponse:
    return service.list_project_status(project_id)


@router.get(
    "/projects/{project_id}/shots/{shot_id}/production-status",
    response_model=ShotProductionStatusResponse,
)
def get_shot_production_status(
    project_id: UUID,
    shot_id: UUID,
    service: Annotated[ProductionStatusService, Depends(get_production_status_service)],
) -> ShotProductionStatusResponse:
    return service.get_shot_status(project_id, shot_id)
