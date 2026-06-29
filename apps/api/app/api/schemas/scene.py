from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.character import MediaAssetResponse
from app.api.schemas.vision_analysis import SceneVisionAnalysisSuggestion
from app.domain.scene import (
    AnalysisStatus,
    CameraPosition,
    CompositionType,
    CrowdLevel,
    Lighting,
    SceneType,
    Season,
    ShotScale,
    SuggestionReviewStatus,
    TimeOfDay,
    ViewDirection,
    Weather,
)


class SceneCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scene_type: SceneType = SceneType.OTHER
    description: str | None = Field(default=None, max_length=1000)
    fixed_environment_description: str | None = Field(default=None, max_length=2000)
    spatial_layout_description: str | None = Field(default=None, max_length=2000)
    visual_style_description: str | None = Field(default=None, max_length=2000)
    prompt_environment: str | None = Field(default=None, max_length=3000)
    notes: str | None = Field(default=None, max_length=2000)


class SceneUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    scene_type: SceneType | None = None
    description: str | None = Field(default=None, max_length=1000)
    fixed_environment_description: str | None = Field(default=None, max_length=2000)
    spatial_layout_description: str | None = Field(default=None, max_length=2000)
    visual_style_description: str | None = Field(default=None, max_length=2000)
    prompt_environment: str | None = Field(default=None, max_length=3000)
    notes: str | None = Field(default=None, max_length=2000)


class SceneStateCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    time_of_day: TimeOfDay = TimeOfDay.UNKNOWN
    weather: Weather = Weather.UNKNOWN
    custom_weather: str | None = Field(default=None, max_length=120)
    lighting: Lighting = Lighting.UNKNOWN
    custom_lighting: str | None = Field(default=None, max_length=120)
    season: Season = Season.UNKNOWN
    environment_condition: str | None = Field(default=None, max_length=2000)
    crowd_level: CrowdLevel = CrowdLevel.UNKNOWN
    prompt_state: str | None = Field(default=None, max_length=3000)


class SceneStateUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    time_of_day: TimeOfDay | None = None
    weather: Weather | None = None
    custom_weather: str | None = Field(default=None, max_length=120)
    lighting: Lighting | None = None
    custom_lighting: str | None = Field(default=None, max_length=120)
    season: Season | None = None
    environment_condition: str | None = Field(default=None, max_length=2000)
    crowd_level: CrowdLevel | None = None
    prompt_state: str | None = Field(default=None, max_length=3000)


class SceneReferenceUpdateRequest(BaseModel):
    shot_scale: ShotScale | None = None
    camera_position: CameraPosition | None = None
    custom_camera_position: str | None = Field(default=None, max_length=120)
    view_direction: ViewDirection | None = None
    custom_view_direction: str | None = Field(default=None, max_length=120)
    composition_type: CompositionType | None = None
    custom_composition: str | None = Field(default=None, max_length=120)
    is_empty_plate: bool | None = None
    is_spatial_anchor: bool | None = None
    tags: list[str] | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=1000)


class SceneReferenceResponse(BaseModel):
    id: str
    state_id: str
    media_asset_id: str
    shot_scale: ShotScale
    camera_position: CameraPosition
    custom_camera_position: str | None
    view_direction: ViewDirection
    custom_view_direction: str | None
    composition_type: CompositionType
    custom_composition: str | None
    is_empty_plate: bool
    is_primary: bool
    is_spatial_anchor: bool
    tags: list[str]
    description: str | None
    notes: str | None
    analysis_status: AnalysisStatus
    suggestion_review_status: SuggestionReviewStatus
    analysis_suggestions: SceneVisionAnalysisSuggestion | None
    media_asset: MediaAssetResponse
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SceneStateResponse(BaseModel):
    id: str
    scene_id: str
    name: str
    description: str | None
    time_of_day: TimeOfDay
    weather: Weather
    custom_weather: str | None
    lighting: Lighting
    custom_lighting: str | None
    season: Season
    environment_condition: str | None
    crowd_level: CrowdLevel
    prompt_state: str | None
    is_default: bool
    reference_count: int = 0
    primary_reference: SceneReferenceResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SceneResponse(BaseModel):
    id: str
    project_id: str
    name: str
    scene_type: SceneType
    description: str | None
    fixed_environment_description: str | None
    spatial_layout_description: str | None
    visual_style_description: str | None
    prompt_environment: str | None
    notes: str | None
    default_state: SceneStateResponse | None = None
    state_count: int = 0
    reference_count: int = 0
    cover_reference: SceneReferenceResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SceneListResponse(BaseModel):
    items: list[SceneResponse]
    total: int


class SceneStateListResponse(BaseModel):
    items: list[SceneStateResponse]
    total: int


class SceneReferenceListResponse(BaseModel):
    items: list[SceneReferenceResponse]
    total: int
