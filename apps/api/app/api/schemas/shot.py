from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.schemas.character import CharacterReferenceResponse, MediaAssetResponse
from app.api.schemas.scene import SceneReferenceResponse
from app.domain.shot import (
    CameraAngle,
    CameraHeight,
    CameraMovement,
    CharacterReferencePurpose,
    MediaReferencePurpose,
    MissingItem,
    ReadinessStatus,
    SceneReferencePurpose,
    ShotCompositionType,
    ShotReferenceType,
    ShotScale,
)


class ShotCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    story_description: str | None = Field(default=None, max_length=3000)
    visual_description: str | None = Field(default=None, max_length=3000)
    dialogue: str | None = Field(default=None, max_length=3000)
    action_summary: str | None = Field(default=None, max_length=2000)
    duration_seconds: float | None = Field(default=None, le=3600)
    shot_scale: ShotScale = ShotScale.UNKNOWN
    camera_height: CameraHeight = CameraHeight.UNKNOWN
    custom_camera_height: str | None = Field(default=None, max_length=120)
    camera_angle: CameraAngle = CameraAngle.UNKNOWN
    custom_camera_angle: str | None = Field(default=None, max_length=120)
    composition_type: ShotCompositionType = ShotCompositionType.UNKNOWN
    custom_composition: str | None = Field(default=None, max_length=120)
    camera_movement: CameraMovement = CameraMovement.UNKNOWN
    custom_camera_movement: str | None = Field(default=None, max_length=120)
    focal_subject: str | None = Field(default=None, max_length=200)
    mood_description: str | None = Field(default=None, max_length=1000)
    scene_id: str | None = None
    scene_state_id: str | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("duration_seconds")
    @classmethod
    def duration_seconds_must_be_positive(cls, value: float | None) -> float | None:
        if value is not None and value <= 0:
            raise ValueError("SHOT_DURATION_SECONDS_POSITIVE")
        return value


class ShotUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    story_description: str | None = Field(default=None, max_length=3000)
    visual_description: str | None = Field(default=None, max_length=3000)
    dialogue: str | None = Field(default=None, max_length=3000)
    action_summary: str | None = Field(default=None, max_length=2000)
    duration_seconds: float | None = Field(default=None, le=3600)
    shot_scale: ShotScale | None = None
    camera_height: CameraHeight | None = None
    custom_camera_height: str | None = Field(default=None, max_length=120)
    camera_angle: CameraAngle | None = None
    custom_camera_angle: str | None = Field(default=None, max_length=120)
    composition_type: ShotCompositionType | None = None
    custom_composition: str | None = Field(default=None, max_length=120)
    camera_movement: CameraMovement | None = None
    custom_camera_movement: str | None = Field(default=None, max_length=120)
    focal_subject: str | None = Field(default=None, max_length=200)
    mood_description: str | None = Field(default=None, max_length=1000)
    scene_id: str | None = None
    scene_state_id: str | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("duration_seconds")
    @classmethod
    def duration_seconds_must_be_positive(cls, value: float | None) -> float | None:
        if value is not None and value <= 0:
            raise ValueError("SHOT_DURATION_SECONDS_POSITIVE")
        return value


class ShotMoveRequest(BaseModel):
    order_index: int = Field(ge=1)


class ShotCharacterCreateRequest(BaseModel):
    character_id: str
    look_id: str | None = None
    action_description: str | None = Field(default=None, max_length=2000)
    expression_description: str | None = Field(default=None, max_length=1000)
    position_description: str | None = Field(default=None, max_length=1000)
    is_primary_subject: bool = False
    notes: str | None = Field(default=None, max_length=1000)


class ShotCharacterUpdateRequest(BaseModel):
    look_id: str | None = None
    action_description: str | None = Field(default=None, max_length=2000)
    expression_description: str | None = Field(default=None, max_length=1000)
    position_description: str | None = Field(default=None, max_length=1000)
    is_primary_subject: bool | None = None
    notes: str | None = Field(default=None, max_length=1000)


class ShotReferenceCreateRequest(BaseModel):
    reference_type: ShotReferenceType
    character_reference_id: str | None = None
    scene_reference_id: str | None = None
    media_asset_id: str | None = None
    shot_character_id: str | None = None
    purpose: CharacterReferencePurpose | SceneReferencePurpose | MediaReferencePurpose
    notes: str | None = Field(default=None, max_length=1000)


class ShotReferenceUpdateRequest(BaseModel):
    purpose: CharacterReferencePurpose | SceneReferencePurpose | MediaReferencePurpose | None = None
    notes: str | None = Field(default=None, max_length=1000)


class ShotReferenceMoveRequest(BaseModel):
    order_index: int = Field(ge=1)


class ShotSceneSummary(BaseModel):
    id: str
    name: str


class ShotSceneStateSummary(BaseModel):
    id: str
    name: str


class ShotCharacterResponse(BaseModel):
    id: str
    shot_id: str
    character_id: str
    character_name: str
    look_id: str | None
    look_name: str | None
    action_description: str | None
    expression_description: str | None
    position_description: str | None
    is_primary_subject: bool
    order_index: int
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShotReferenceResponse(BaseModel):
    id: str
    shot_id: str
    reference_type: ShotReferenceType
    character_reference_id: str | None
    scene_reference_id: str | None
    media_asset_id: str | None
    shot_character_id: str | None
    purpose: str
    order_index: int
    notes: str | None
    media_asset: MediaAssetResponse | None
    character_reference: CharacterReferenceResponse | None = None
    scene_reference: SceneReferenceResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShotResponse(BaseModel):
    id: str
    project_id: str
    name: str
    order_index: int
    story_description: str | None
    visual_description: str | None
    dialogue: str | None
    action_summary: str | None
    duration_seconds: float | None
    shot_scale: ShotScale
    camera_height: CameraHeight
    custom_camera_height: str | None
    camera_angle: CameraAngle
    custom_camera_angle: str | None
    composition_type: ShotCompositionType
    custom_composition: str | None
    camera_movement: CameraMovement
    custom_camera_movement: str | None
    focal_subject: str | None
    mood_description: str | None
    scene_id: str | None
    scene_state_id: str | None
    scene: ShotSceneSummary | None = None
    scene_state: ShotSceneStateSummary | None = None
    notes: str | None
    readiness_status: ReadinessStatus
    missing_items: list[MissingItem]
    character_count: int = 0
    reference_count: int = 0
    characters: list[ShotCharacterResponse] = Field(default_factory=list)
    references: list[ShotReferenceResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShotListResponse(BaseModel):
    items: list[ShotResponse]
    total: int


class ShotCharacterListResponse(BaseModel):
    items: list[ShotCharacterResponse]
    total: int


class ShotReferenceListResponse(BaseModel):
    items: list[ShotReferenceResponse]
    total: int
