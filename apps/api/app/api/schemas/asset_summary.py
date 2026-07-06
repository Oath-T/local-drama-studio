from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SummaryMediaAsset(BaseModel):
    id: str
    media_type: str
    original_filename: str
    mime_type: str
    width: int
    height: int
    thumbnail_url: str | None
    content_url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SummaryReference(BaseModel):
    id: str
    reference_type: str
    label: str
    purpose: str | None = None
    look_id: str | None = None
    look_name: str | None = None
    state_id: str | None = None
    state_name: str | None = None
    is_primary: bool = False
    is_identity_anchor: bool = False
    is_spatial_anchor: bool = False
    is_empty_plate: bool = False
    media_asset: SummaryMediaAsset | None = None
    created_at: datetime


class RecentShotSummary(BaseModel):
    id: str
    name: str
    order_index: int
    updated_at: datetime


class CharacterAssetSummaryResponse(BaseModel):
    id: str
    project_id: str
    name: str
    default_look_id: str | None
    default_look_name: str | None
    look_count: int
    reference_count: int
    primary_reference_count: int
    identity_anchor_count: int
    face_reference_count: int
    full_body_reference_count: int
    used_shot_count: int
    recent_shots: list[RecentShotSummary]
    featured_references: list[SummaryReference]
    completeness_warnings: list[str]


class SceneAssetSummaryResponse(BaseModel):
    id: str
    project_id: str
    name: str
    default_state_id: str | None
    default_state_name: str | None
    state_count: int
    reference_count: int
    primary_reference_count: int
    spatial_anchor_count: int
    empty_plate_count: int
    wide_reference_count: int
    used_shot_count: int
    recent_shots: list[RecentShotSummary]
    featured_references: list[SummaryReference]
    completeness_warnings: list[str]


class ShotAssetCharacterSummary(BaseModel):
    shot_character_id: str
    character_id: str
    character_name: str
    look_id: str | None
    look_name: str | None
    is_primary_subject: bool
    bound_reference_count: int
    completeness_warnings: list[str]


class ShotAssetSceneSummary(BaseModel):
    scene_id: str | None
    scene_name: str | None
    scene_state_id: str | None
    scene_state_name: str | None
    bound_reference_count: int
    completeness_warnings: list[str]


class ShotGenerationAssetSummary(BaseModel):
    keyframe_task_count: int
    video_task_count: int
    selected_keyframe_output_count: int
    selected_video_output_count: int


class ShotAssetSummaryResponse(BaseModel):
    id: str
    project_id: str
    name: str
    characters: list[ShotAssetCharacterSummary]
    scene: ShotAssetSceneSummary
    references: list[SummaryReference]
    generation: ShotGenerationAssetSummary
    completeness_warnings: list[str]
