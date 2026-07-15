from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.project_timeline import ProjectTimelineResponse
from app.infrastructure.database import get_db_session
from app.service.project_timeline_service import ProjectTimelineService

router = APIRouter(prefix="/projects/{project_id}", tags=["project-timeline"])


def get_project_timeline_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ProjectTimelineService:
    return ProjectTimelineService(session)


@router.get("/timeline", response_model=ProjectTimelineResponse)
def get_project_timeline(
    project_id: UUID,
    service: Annotated[ProjectTimelineService, Depends(get_project_timeline_service)],
) -> ProjectTimelineResponse:
    return service.get_timeline(project_id)
