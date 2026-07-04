from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.character import Expression, PoseType, ShotType, ViewAngle
from app.domain.scene import (
    CameraPosition,
    CompositionType,
    Lighting,
    ShotScale,
    TimeOfDay,
    ViewDirection,
    Weather,
)
from app.domain.vision_analysis import VisionAnalysisTargetType, VisionAnalysisTaskStatus


class CharacterVisionAnalysisSuggestion(BaseModel):
    schema_version: int = 1
    shot_type: ShotType = ShotType.UNKNOWN
    view_angle: ViewAngle = ViewAngle.UNKNOWN
    expression: Expression = Expression.UNKNOWN
    custom_expression: str | None = Field(default=None, max_length=100)
    pose_type: PoseType = PoseType.UNKNOWN
    custom_pose: str | None = Field(default=None, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=12)
    description: str | None = Field(default=None, max_length=1000)
    quality_notes: list[str] = Field(default_factory=list, max_length=8)
    identity_anchor_recommended: bool = False
    appearance_summary: str | None = Field(default=None, max_length=1000)
    costume_summary: str | None = Field(default=None, max_length=1000)
    hair_summary: str | None = Field(default=None, max_length=1000)
    confidence_notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_custom_fields(self) -> "CharacterVisionAnalysisSuggestion":
        if self.expression == Expression.CUSTOM and not _has_text(self.custom_expression):
            raise ValueError("custom_expression is required when expression is custom")
        if self.expression != Expression.CUSTOM:
            self.custom_expression = None
        if self.pose_type == PoseType.CUSTOM and not _has_text(self.custom_pose):
            raise ValueError("custom_pose is required when pose_type is custom")
        if self.pose_type != PoseType.CUSTOM:
            self.custom_pose = None
        self.tags = _normalize_tags(self.tags)
        self.quality_notes = _normalize_list(self.quality_notes, 8, 200)
        return self


class SceneVisionAnalysisSuggestion(BaseModel):
    schema_version: int = 1
    shot_scale: ShotScale = ShotScale.UNKNOWN
    camera_position: CameraPosition = CameraPosition.UNKNOWN
    custom_camera_position: str | None = Field(default=None, max_length=120)
    view_direction: ViewDirection = ViewDirection.UNKNOWN
    custom_view_direction: str | None = Field(default=None, max_length=120)
    composition_type: CompositionType = CompositionType.UNKNOWN
    custom_composition: str | None = Field(default=None, max_length=120)
    tags: list[str] = Field(default_factory=list, max_length=12)
    description: str | None = Field(default=None, max_length=1000)
    quality_notes: list[str] = Field(default_factory=list, max_length=8)
    spatial_anchor_recommended: bool = False
    empty_plate_recommended: bool = False
    detected_time_of_day: TimeOfDay = TimeOfDay.UNKNOWN
    detected_weather: Weather = Weather.UNKNOWN
    detected_lighting: Lighting = Lighting.UNKNOWN
    confidence_notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_custom_fields(self) -> "SceneVisionAnalysisSuggestion":
        if self.camera_position == CameraPosition.CUSTOM and not _has_text(
            self.custom_camera_position
        ):
            raise ValueError("custom_camera_position is required when camera_position is custom")
        if self.camera_position != CameraPosition.CUSTOM:
            self.custom_camera_position = None
        if self.view_direction == ViewDirection.CUSTOM and not _has_text(
            self.custom_view_direction
        ):
            raise ValueError("custom_view_direction is required when view_direction is custom")
        if self.view_direction != ViewDirection.CUSTOM:
            self.custom_view_direction = None
        if self.composition_type == CompositionType.CUSTOM and not _has_text(
            self.custom_composition
        ):
            raise ValueError("custom_composition is required when composition_type is custom")
        if self.composition_type != CompositionType.CUSTOM:
            self.custom_composition = None
        self.tags = _normalize_tags(self.tags)
        self.quality_notes = _normalize_list(self.quality_notes, 8, 200)
        return self


class VisionAnalysisTaskResponse(BaseModel):
    id: str
    project_id: str
    target_type: VisionAnalysisTargetType
    character_reference_id: str | None
    scene_reference_id: str | None
    provider: str
    status: VisionAnalysisTaskStatus
    attempt_count: int
    error_code: str | None
    error_message_safe: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LatestVisionAnalysisTaskResponse(BaseModel):
    task: VisionAnalysisTaskResponse | None


class KeyframeGenerationCapabilityResponse(BaseModel):
    available: bool
    provider: str
    status: str


class VisionAnalysisCapabilitiesResponse(BaseModel):
    vision_analysis: dict[Literal["available", "provider"], bool | str]
    keyframe_generation: KeyframeGenerationCapabilityResponse | None = None


class AnalysisConfirmRequest(BaseModel):
    accepted_fields: list[str] = Field(min_length=1, max_length=20)
    values: dict[str, Any]


class AnalysisConfirmResponse(BaseModel):
    suggestion_review_status: str


class AnalysisRejectResponse(BaseModel):
    suggestion_review_status: str


def _has_text(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    for tag in tags:
        value = tag.strip()
        if value and value not in normalized:
            normalized.append(value[:50])
    return normalized[:12]


def _normalize_list(values: list[str], max_items: int, max_length: int) -> list[str]:
    normalized: list[str] = []
    for item in values:
        value = item.strip()
        if value and value not in normalized:
            normalized.append(value[:max_length])
    return normalized[:max_items]
