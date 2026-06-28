from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.character import Expression, PoseType, ShotType, ViewAngle
from app.domain.scene import (
    CameraPosition,
    CompositionType,
    ViewDirection,
)
from app.domain.scene import (
    ShotScale as SceneShotScale,
)
from app.domain.shot import CharacterReferencePurpose, SceneReferencePurpose
from app.domain.shot_recommendation import SceneRecommendationStatus


class CharacterReferenceRecommendationItem(BaseModel):
    reference_id: str
    media_asset_id: str
    thumbnail_url: str
    content_url: str
    source_look_id: str
    source_look_name: str
    shot_type: ShotType
    view_angle: ViewAngle
    expression: Expression
    pose_type: PoseType
    is_primary: bool
    is_identity_anchor: bool
    score: int = Field(ge=0, le=100)
    suggested_purpose: CharacterReferencePurpose
    reasons: list[str]
    bound_purposes: list[CharacterReferencePurpose]
    is_already_bound_for_suggested_purpose: bool


class CharacterRecommendationGroup(BaseModel):
    shot_character_id: str
    character_id: str
    character_name: str
    look_id: str | None
    look_name: str | None
    items: list[CharacterReferenceRecommendationItem]


class SceneReferenceRecommendationItem(BaseModel):
    reference_id: str
    media_asset_id: str
    thumbnail_url: str
    content_url: str
    source_state_id: str
    source_state_name: str
    shot_scale: SceneShotScale
    camera_position: CameraPosition
    view_direction: ViewDirection
    composition_type: CompositionType
    is_primary: bool
    is_spatial_anchor: bool
    is_empty_plate: bool
    score: int = Field(ge=0, le=100)
    suggested_purpose: SceneReferencePurpose
    reasons: list[str]
    bound_purposes: list[SceneReferencePurpose]
    is_already_bound_for_suggested_purpose: bool


class SceneRecommendationGroup(BaseModel):
    status_code: SceneRecommendationStatus
    items: list[SceneReferenceRecommendationItem]


class ShotRecommendationResponse(BaseModel):
    shot_id: str
    generated_from_updated_at: datetime
    character_recommendations: list[CharacterRecommendationGroup]
    scene_recommendations: SceneRecommendationGroup
