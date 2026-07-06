from datetime import datetime
from typing import Literal

from pydantic import BaseModel

GenerationTaskType = Literal["keyframe", "video"]


class GenerationTaskSummaryResponse(BaseModel):
    task_type: GenerationTaskType
    project_id: str
    task_id: str
    task_name: str
    task_status: str
    readiness_status: str | None = None
    shot_id: str
    shot_name: str
    workflow_id: str | None = None
    latest_run_id: str | None = None
    latest_run_number: int | None = None
    latest_run_status: str | None = None
    run_count: int
    output_count: int
    has_outputs: bool
    has_selected_output: bool
    created_at: datetime
    updated_at: datetime


class GenerationTaskSummaryListResponse(BaseModel):
    items: list[GenerationTaskSummaryResponse]
    total: int
