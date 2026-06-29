from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.schemas.character import MediaAssetResponse
from app.domain.keyframe_task import (
    DEFAULT_ASPECT_RATIO,
    DEFAULT_GUIDANCE_SCALE,
    DEFAULT_HEIGHT,
    DEFAULT_OUTPUT_COUNT,
    DEFAULT_STEPS,
    DEFAULT_WIDTH,
    KeyframeTaskAspectRatio,
    KeyframeTaskBlockingIssue,
    KeyframeTaskReadinessStatus,
    KeyframeTaskReferenceType,
    KeyframeTaskStatus,
    KeyframeTaskWarningIssue,
    is_valid_dimension,
)


class KeyframeShotSnapshotCharacter(BaseModel):
    shot_character_id: str
    character_id: str
    character_name: str
    look_id: str | None = None
    look_name: str | None = None
    action_description: str | None = None
    expression_description: str | None = None
    position_description: str | None = None
    is_primary_subject: bool
    order_index: int


class KeyframeShotSnapshot(BaseModel):
    schema_version: Literal[1] = 1
    shot_id: str
    order_index: int
    title: str
    story_description: str | None = None
    visual_description: str | None = None
    action_summary: str | None = None
    dialogue: str | None = None
    mood_description: str | None = None
    duration_seconds: float | None = None
    shot_scale: str
    camera_angle: str
    custom_camera_angle: str | None = None
    camera_height: str
    custom_camera_height: str | None = None
    lens: str | None = None
    composition_type: str
    custom_composition: str | None = None
    camera_movement: str
    custom_camera_movement: str | None = None
    scene_id: str | None = None
    scene_name: str | None = None
    scene_state_id: str | None = None
    scene_state_name: str | None = None
    characters: list[KeyframeShotSnapshotCharacter] = Field(default_factory=list)


class KeyframeTaskCreateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    copy_current_references: bool = True


class KeyframeTaskUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    prompt_zh: str | None = Field(default=None, max_length=8000)
    prompt_en: str | None = Field(default=None, max_length=8000)
    negative_prompt: str | None = Field(default=None, max_length=4000)
    aspect_ratio: KeyframeTaskAspectRatio | None = None
    width: int | None = None
    height: int | None = None
    seed: int | None = Field(default=None, ge=0)
    steps: int | None = Field(default=None, ge=1, le=150)
    guidance_scale: float | None = Field(default=None, ge=0, le=30)
    sampler_name: str | None = Field(default=None, max_length=120)
    scheduler_name: str | None = Field(default=None, max_length=120)
    model_provider: str | None = Field(default=None, max_length=120)
    model_name: str | None = Field(default=None, max_length=200)
    model_version: str | None = Field(default=None, max_length=120)
    output_count: int | None = Field(default=None, ge=1, le=8)

    @field_validator("width", "height")
    @classmethod
    def dimensions_must_be_valid(cls, value: int | None) -> int | None:
        if value is not None and not is_valid_dimension(value):
            raise ValueError("INVALID_KEYFRAME_DIMENSIONS")
        return value


class KeyframeTaskReferenceCreateRequest(BaseModel):
    shot_reference_id: str
    purpose: str | None = Field(default=None, max_length=40)


class KeyframeTaskReferenceUpdateRequest(BaseModel):
    purpose: str | None = Field(default=None, max_length=40)
    order_index: int | None = Field(default=None, ge=1)


class KeyframeTaskReadinessResponse(BaseModel):
    readiness_status: KeyframeTaskReadinessStatus
    blocking_issues: list[KeyframeTaskBlockingIssue]
    warnings: list[KeyframeTaskWarningIssue]


class KeyframeTaskReferenceResponse(BaseModel):
    id: str
    task_id: str
    reference_type: KeyframeTaskReferenceType
    shot_reference_id: str | None
    character_reference_id: str | None
    scene_reference_id: str | None
    media_asset_id: str
    purpose: str
    order_index: int
    source_shot_character_id: str | None
    source_character_id: str | None
    source_look_id: str | None
    source_scene_id: str | None
    source_scene_state_id: str | None
    source_reference_deleted: bool
    media_asset: MediaAssetResponse | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KeyframeTaskResponse(BaseModel):
    id: str
    project_id: str
    shot_id: str
    name: str
    status: KeyframeTaskStatus
    shot_snapshot: KeyframeShotSnapshot
    source_shot_updated_at: datetime
    prompt_zh: str | None
    prompt_en: str | None
    negative_prompt: str | None
    aspect_ratio: KeyframeTaskAspectRatio
    width: int
    height: int
    seed: int | None
    steps: int
    guidance_scale: float
    sampler_name: str | None
    scheduler_name: str | None
    model_provider: str | None
    model_name: str | None
    model_version: str | None
    output_count: int
    readiness: KeyframeTaskReadinessResponse
    shot_changed_since_snapshot: bool
    references: list[KeyframeTaskReferenceResponse] = Field(default_factory=list)
    reference_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KeyframeTaskListResponse(BaseModel):
    items: list[KeyframeTaskResponse]
    total: int


class KeyframeTaskReferenceListResponse(BaseModel):
    items: list[KeyframeTaskReferenceResponse]
    total: int


def default_generation_parameters() -> dict[str, int | float | str]:
    return {
        "aspect_ratio": DEFAULT_ASPECT_RATIO.value,
        "width": DEFAULT_WIDTH,
        "height": DEFAULT_HEIGHT,
        "steps": DEFAULT_STEPS,
        "guidance_scale": DEFAULT_GUIDANCE_SCALE,
        "output_count": DEFAULT_OUTPUT_COUNT,
    }
