from typing import Literal

from pydantic import BaseModel, Field

ProductionOverallStatus = Literal["blocked", "in_progress", "ready_for_video", "completed"]
AssetStepStatus = Literal["complete", "warning", "missing"]
DirectorPromptStatus = Literal["not_created", "available"]
FrameStepStatus = Literal["not_created", "draft", "ready", "running", "completed", "adopted"]
VideoStepStatus = Literal[
    "not_created", "missing_inputs", "draft", "ready", "running", "completed", "adopted"
]
ProductionAction = Literal[
    "complete_assets",
    "generate_director_prompt",
    "create_first_frame_task",
    "select_first_frame_output",
    "create_end_frame_task",
    "select_end_frame_output",
    "create_video_task",
    "select_video_frames",
    "mark_video_ready",
    "start_video_generation",
    "select_video_output",
]


class ProductionAssetStep(BaseModel):
    status: AssetStepStatus
    warnings: list[str] = Field(default_factory=list)


class ProductionDirectorPromptStep(BaseModel):
    status: DirectorPromptStatus
    director_template_available: bool
    recommended_template_id: str


class ProductionFrameStep(BaseModel):
    status: FrameStepStatus
    task_id: str | None = None
    adopted_output_id: str | None = None
    adopted_media_asset_id: str | None = None
    content_url: str | None = None


class ProductionVideoStep(BaseModel):
    status: VideoStepStatus
    task_id: str | None = None
    adopted_output_id: str | None = None
    adopted_media_asset_id: str | None = None
    content_url: str | None = None
    has_start_frame: bool = False
    has_end_frame: bool = False


class ProductionSteps(BaseModel):
    assets: ProductionAssetStep
    director_prompt: ProductionDirectorPromptStep
    first_frame: ProductionFrameStep
    end_frame: ProductionFrameStep
    video: ProductionVideoStep


class ContinuityCandidate(BaseModel):
    previous_shot_id: str
    previous_shot_name: str
    media_asset_id: str
    content_url: str
    source: Literal["adopted_end_frame", "adopted_video"]


class ShotProductionStatusResponse(BaseModel):
    shot_id: str
    shot_name: str
    order_index: int
    character_summary: str | None = None
    scene_summary: str | None = None
    overall_status: ProductionOverallStatus
    steps: ProductionSteps
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[ProductionAction] = Field(default_factory=list)
    continuity_candidate: ContinuityCandidate | None = None


class ProjectProductionSummary(BaseModel):
    total_shots: int
    blocked: int
    in_progress: int
    ready_for_video: int
    completed: int


class ProjectProductionStatusResponse(BaseModel):
    summary: ProjectProductionSummary
    shots: list[ShotProductionStatusResponse]
