from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.character import MediaAssetResponse
from app.domain.keyframe_generation import KeyframeGenerationRunStatus


class KeyframeWorkflowResponse(BaseModel):
    workflow_id: str
    display_name: str
    version: str
    available: bool
    missing_requirements: list[str] = Field(default_factory=list)
    uses_reference_inputs: bool = False


class KeyframeWorkflowListResponse(BaseModel):
    items: list[KeyframeWorkflowResponse]
    total: int


class KeyframeRunCreateRequest(BaseModel):
    workflow_id: str = Field(min_length=1, max_length=120)


class KeyframeRunCreateResponse(BaseModel):
    run_id: str
    status: KeyframeGenerationRunStatus


class KeyframeRunSnapshot(BaseModel):
    schema_version: Literal[1] = 1
    task_id: str
    task_updated_at: datetime
    workflow_id: str
    workflow_version: str
    prompt_zh: str | None
    prompt_en: str | None
    effective_prompt_language: Literal["zh", "en"]
    effective_positive_prompt: str
    negative_prompt: str | None
    width: int
    height: int
    seed: int
    steps: int
    guidance_scale: float
    sampler_name: str
    scheduler_name: str
    output_count: int
    task_reference_ids: list[str] = Field(default_factory=list)
    media_asset_ids: list[str] = Field(default_factory=list)
    reference_inputs_used: bool = False


class KeyframeOutputResponse(BaseModel):
    id: str
    project_id: str
    run_id: str
    media_asset_id: str
    output_index: int
    width: int | None
    height: int | None
    seed: int | None
    is_selected: bool
    media_asset: MediaAssetResponse | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KeyframeRunResponse(BaseModel):
    id: str
    project_id: str
    keyframe_task_id: str
    run_number: int
    provider: str
    workflow_id: str
    workflow_version: str
    status: KeyframeGenerationRunStatus
    provider_job_id: str | None
    submitted_payload_snapshot: KeyframeRunSnapshot
    error_code: str | None
    error_message_safe: str | None
    queued_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    outputs: list[KeyframeOutputResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class KeyframeRunListResponse(BaseModel):
    items: list[KeyframeRunResponse]
    total: int


class KeyframeOutputSelectResponse(BaseModel):
    output: KeyframeOutputResponse
