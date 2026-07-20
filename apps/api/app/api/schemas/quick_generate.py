from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class QuickGenerateMode(StrEnum):
    FIRST_FRAME = "first_frame"
    END_FRAME = "end_frame"
    VIDEO = "video"


class QuickGenerateRunType(StrEnum):
    KEYFRAME = "keyframe"
    VIDEO = "video"


class WorkflowQualityTier(StrEnum):
    BASIC = "basic"
    STANDARD = "standard"
    PRODUCTION = "production"


class WorkflowSpeedTier(StrEnum):
    FAST = "fast"
    NORMAL = "normal"
    SLOW = "slow"


class WorkflowCapabilityResponse(BaseModel):
    workflow_id: str
    display_name: str
    task_type: QuickGenerateRunType
    supports: list[QuickGenerateMode] = Field(default_factory=list)
    requires: list[str] = Field(default_factory=list)
    recommended_for: list[str] = Field(default_factory=list)
    executable: bool
    missing_models: list[str] = Field(default_factory=list)
    missing_nodes: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    quality_tier: WorkflowQualityTier
    speed_tier: WorkflowSpeedTier
    visual_only: bool = False
    available: bool = False
    blockers: list[str] = Field(default_factory=list)
    checked_at: datetime | None = None


class WorkflowRouteResponse(BaseModel):
    selected_workflow_id: str | None
    executable: bool
    reason_zh: str
    required_inputs: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    missing_models: list[str] = Field(default_factory=list)
    missing_nodes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    fallback: str | None = None


class QuickGenerateResolvedInputs(BaseModel):
    start_frame_media_asset_id: str | None = None
    end_frame_media_asset_id: str | None = None
    start_frame_available: bool = False
    end_frame_available: bool = False


class QuickGenerateResolvedParameters(BaseModel):
    width: int | None = None
    height: int | None = None
    frame_count: int | None = None
    fps: int | None = None
    seed: int | None = None
    expected_duration: float | None = None


class QuickGenerateEstimatedOutput(BaseModel):
    media_type: str | None = None
    width: int | None = None
    height: int | None = None
    fps: int | None = None
    duration_seconds: float | None = None
    frame_count: int | None = None


class QuickGenerateActiveRun(BaseModel):
    run_type: QuickGenerateRunType
    task_id: str
    run_id: str
    status: str
    workflow_id: str


class QuickGeneratePreviewRequest(BaseModel):
    mode: QuickGenerateMode
    prompt: str | None = Field(default=None, max_length=8000)
    negative_prompt: str | None = Field(default=None, max_length=4000)
    workflow_id: str | None = Field(default=None, max_length=120)
    duration_preset: Literal["short_test", "standard_short"] | None = None
    fps: int | None = Field(default=None, ge=1, le=60)
    seed: int | None = Field(default=None, ge=0, le=2**32 - 1)


class QuickGeneratePreviewResponse(BaseModel):
    mode: QuickGenerateMode
    submitted_prompt: str | None = None
    submitted_negative_prompt: str | None = None
    ready: bool = False
    can_execute: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    capability: WorkflowCapabilityResponse | None = None
    workflow_id: str | None = None
    resolved_inputs: QuickGenerateResolvedInputs = Field(
        default_factory=QuickGenerateResolvedInputs
    )
    resolved_parameters: QuickGenerateResolvedParameters = Field(
        default_factory=QuickGenerateResolvedParameters
    )
    estimated_output: QuickGenerateEstimatedOutput = Field(
        default_factory=QuickGenerateEstimatedOutput
    )
    active_run: QuickGenerateActiveRun | None = None
    route: WorkflowRouteResponse
    capabilities: list[WorkflowCapabilityResponse] = Field(default_factory=list)


class QuickGenerateExecuteRequest(QuickGeneratePreviewRequest):
    request_id: str = Field(min_length=1, max_length=120)


class CanvasSyncResponse(BaseModel):
    attempted: bool = False
    synced: bool = False
    node_id: str | None = None
    edge_id: str | None = None
    error_message: str | None = None


class QuickGenerateSyncOutputRequest(BaseModel):
    run_type: QuickGenerateRunType
    run_id: str = Field(min_length=1, max_length=36)


class QuickGenerateExecuteResponse(BaseModel):
    mode: QuickGenerateMode
    run_type: QuickGenerateRunType
    request_id: str
    idempotent_replay: bool = False
    reused_active_run: bool = False
    task_id: str
    run_id: str
    status: str
    workflow_id: str
    route: WorkflowRouteResponse
    canvas_sync: CanvasSyncResponse = Field(default_factory=CanvasSyncResponse)
