from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.schemas.character import MediaAssetResponse
from app.domain.video_generation import (
    VideoGenerationRunStatus,
    VideoGenerationTaskStatus,
    VideoInputRole,
    VideoTaskBlockingIssue,
    VideoTaskReadinessStatus,
    VideoTaskWarning,
    VideoWorkflowMode,
)


class VideoTaskReadinessResponse(BaseModel):
    readiness_status: VideoTaskReadinessStatus
    blocking_issues: list[VideoTaskBlockingIssue] = Field(default_factory=list)
    warnings: list[VideoTaskWarning] = Field(default_factory=list)


class VideoTaskInputRequest(BaseModel):
    role: VideoInputRole
    media_asset_id: str | None = None
    source_keyframe_output_id: str | None = None
    source_keyframe_task_id: str | None = None


class VideoTaskInputResponse(BaseModel):
    id: str | None = None
    role: VideoInputRole
    media_asset_id: str | None
    source_keyframe_output_id: str | None = None
    source_keyframe_task_id: str | None = None
    sort_order: int
    media_asset: MediaAssetResponse | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class VideoTaskCreateRequest(BaseModel):
    input_media_asset_id: str | None = None
    source_keyframe_output_id: str | None = None
    source_keyframe_task_id: str | None = None
    inputs: list[VideoTaskInputRequest] | None = None


class VideoTaskUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    input_media_asset_id: str | None = None
    source_keyframe_output_id: str | None = None
    source_keyframe_task_id: str | None = None
    inputs: list[VideoTaskInputRequest] | None = None
    prompt: str | None = Field(default=None, max_length=4000)
    negative_prompt: str | None = Field(default=None, max_length=2000)
    duration_seconds: float | None = None
    fps: int | None = None
    width: int | None = None
    height: int | None = None
    seed: int | None = None
    motion_strength: float | None = None
    camera_motion: str | None = Field(default=None, max_length=200)
    workflow_id: str | None = Field(default=None, max_length=120)

    @field_validator("name", "prompt", "negative_prompt", "camera_motion")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class VideoTaskResponse(BaseModel):
    id: str
    project_id: str
    shot_id: str
    name: str
    status: VideoGenerationTaskStatus
    input_media_asset_id: str | None
    source_keyframe_output_id: str | None
    source_keyframe_task_id: str | None
    prompt: str | None
    negative_prompt: str | None
    duration_seconds: float
    fps: int
    width: int
    height: int
    seed: int | None
    motion_strength: float | None
    camera_motion: str | None
    workflow_id: str | None
    input_media_asset: MediaAssetResponse | None
    inputs: list[VideoTaskInputResponse] = Field(default_factory=list)
    readiness: VideoTaskReadinessResponse
    latest_run_status: VideoGenerationRunStatus | None = None
    selected_output: "VideoOutputResponse | None" = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VideoTaskListResponse(BaseModel):
    items: list[VideoTaskResponse]
    total: int


class VideoWorkflowResponse(BaseModel):
    workflow_id: str
    display_name: str
    version: str
    mode: VideoWorkflowMode
    required_input_roles: list[VideoInputRole] = Field(default_factory=list)
    available: bool
    missing_requirements: list[str] = Field(default_factory=list)
    reference_inputs_used: bool = True


class VideoWorkflowListResponse(BaseModel):
    items: list[VideoWorkflowResponse]
    total: int


class VideoRunCreateRequest(BaseModel):
    workflow_id: str = Field(min_length=1, max_length=120)


class VideoRunCreateResponse(BaseModel):
    run_id: str
    status: VideoGenerationRunStatus


class VideoRunInputSnapshot(BaseModel):
    role: VideoInputRole
    media_asset_id: str


class VideoRunSnapshot(BaseModel):
    schema_version: Literal[1, 2] = 2
    video_task_id: str
    shot_id: str
    workflow_id: str
    workflow_version: str
    workflow_mode: VideoWorkflowMode | None = None
    input_media_asset_id: str | None = None
    inputs: list[VideoRunInputSnapshot] = Field(default_factory=list)
    prompt: str
    negative_prompt: str | None
    duration_seconds: float
    fps: int
    width: int
    height: int
    seed: int
    motion_strength: float | None
    camera_motion: str | None
    reference_inputs_used: bool = True


class VideoOutputResponse(BaseModel):
    id: str
    project_id: str
    run_id: str
    media_asset_id: str
    output_index: int
    width: int | None
    height: int | None
    duration_seconds: float | None
    fps: int | None
    seed: int | None
    is_selected: bool
    media_asset: MediaAssetResponse | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VideoRunResponse(BaseModel):
    id: str
    project_id: str
    video_task_id: str
    run_number: int
    provider: str
    workflow_id: str
    workflow_version: str
    status: VideoGenerationRunStatus
    provider_job_id: str | None
    submitted_payload_snapshot: VideoRunSnapshot
    error_code: str | None
    error_message_safe: str | None
    queued_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    outputs: list[VideoOutputResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class VideoRunListResponse(BaseModel):
    items: list[VideoRunResponse]
    total: int


class VideoInputUploadResponse(BaseModel):
    media_asset: MediaAssetResponse


VideoTaskResponse.model_rebuild()
