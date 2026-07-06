from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.generation_task import GenerationTaskSummaryListResponse
from app.infrastructure.database import get_db_session
from app.repository.generation_task_repository import GenerationTaskRepository
from app.service.generation_task_service import GenerationTaskService

router = APIRouter(tags=["generation-tasks"])


def get_generation_task_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> GenerationTaskService:
    return GenerationTaskService(GenerationTaskRepository(session))


@router.get(
    "/projects/{project_id}/generation-tasks",
    response_model=GenerationTaskSummaryListResponse,
)
def list_project_generation_tasks(
    project_id: UUID,
    service: Annotated[GenerationTaskService, Depends(get_generation_task_service)],
) -> GenerationTaskSummaryListResponse:
    return service.list_project_generation_tasks(project_id)
