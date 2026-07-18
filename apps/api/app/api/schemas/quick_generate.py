from enum import StrEnum

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


class QuickGeneratePreviewRequest(BaseModel):
    mode: QuickGenerateMode
    prompt: str | None = Field(default=None, max_length=8000)
    negative_prompt: str | None = Field(default=None, max_length=4000)
    workflow_id: str | None = Field(default=None, max_length=120)


class QuickGeneratePreviewResponse(BaseModel):
    mode: QuickGenerateMode
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
