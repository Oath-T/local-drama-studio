from typing import cast
from uuid import UUID

from fastapi import status

from app.api.schemas.generation_task import (
    GenerationTaskSummaryListResponse,
    GenerationTaskSummaryResponse,
    GenerationTaskType,
)
from app.core.errors import AppError
from app.repository.generation_task_repository import GenerationTaskRepository


class GenerationTaskService:
    def __init__(self, repository: GenerationTaskRepository) -> None:
        self.repository = repository

    def list_project_generation_tasks(self, project_id: UUID) -> GenerationTaskSummaryListResponse:
        if not self.repository.project_exists(str(project_id)):
            raise AppError(
                code="project_not_found",
                message="项目不存在或已被删除。",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        items = [
            GenerationTaskSummaryResponse(
                task_type=cast(GenerationTaskType, item.task_type),
                project_id=item.project_id,
                task_id=item.task_id,
                task_name=item.task_name,
                task_status=item.task_status,
                readiness_status=item.readiness_status,
                shot_id=item.shot_id,
                shot_name=item.shot_name,
                workflow_id=item.workflow_id,
                latest_run_id=item.latest_run_id,
                latest_run_number=item.latest_run_number,
                latest_run_status=item.latest_run_status,
                run_count=item.run_count,
                output_count=item.output_count,
                has_outputs=item.output_count > 0,
                has_selected_output=item.has_selected_output,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in self.repository.list_project_generation_tasks(str(project_id))
        ]
        return GenerationTaskSummaryListResponse(items=items, total=len(items))
