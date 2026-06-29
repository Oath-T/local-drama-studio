from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.vision_analysis import CharacterVisionAnalysisSuggestion
from app.domain.character import (
    AnalysisStatus,
    Expression,
    PoseType,
    RoleType,
    ShotType,
    SuggestionReviewStatus,
    ViewAngle,
)


class CharacterCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    aliases: str | None = Field(default=None, max_length=200)
    role_type: RoleType = RoleType.SUPPORTING
    description: str | None = Field(default=None, max_length=1000)
    appearance_description: str | None = Field(default=None, max_length=2000)
    personality_description: str | None = Field(default=None, max_length=2000)
    prompt_identity: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)


class CharacterUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    aliases: str | None = Field(default=None, max_length=200)
    role_type: RoleType | None = None
    description: str | None = Field(default=None, max_length=1000)
    appearance_description: str | None = Field(default=None, max_length=2000)
    personality_description: str | None = Field(default=None, max_length=2000)
    prompt_identity: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)


class CharacterLookCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    costume_description: str | None = Field(default=None, max_length=2000)
    hair_description: str | None = Field(default=None, max_length=1000)
    makeup_description: str | None = Field(default=None, max_length=1000)
    condition_description: str | None = Field(default=None, max_length=1000)
    prompt_appearance: str | None = Field(default=None, max_length=3000)


class CharacterLookUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    costume_description: str | None = Field(default=None, max_length=2000)
    hair_description: str | None = Field(default=None, max_length=1000)
    makeup_description: str | None = Field(default=None, max_length=1000)
    condition_description: str | None = Field(default=None, max_length=1000)
    prompt_appearance: str | None = Field(default=None, max_length=3000)


VisionAnalysisSuggestion = CharacterVisionAnalysisSuggestion


class CharacterReferenceUpdateRequest(BaseModel):
    shot_type: ShotType | None = None
    view_angle: ViewAngle | None = None
    expression: Expression | None = None
    pose_type: PoseType | None = None
    custom_expression: str | None = Field(default=None, max_length=100)
    custom_pose: str | None = Field(default=None, max_length=100)
    tags: list[str] | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=1000)
    is_identity_anchor: bool | None = None


class MediaAssetResponse(BaseModel):
    id: str
    project_id: str
    media_type: str
    original_filename: str
    mime_type: str
    extension: str
    size_bytes: int
    width: int
    height: int
    sha256: str
    thumbnail_url: str
    content_url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CharacterReferenceResponse(BaseModel):
    id: str
    look_id: str
    media_asset_id: str
    shot_type: ShotType
    view_angle: ViewAngle
    expression: Expression
    pose_type: PoseType
    custom_expression: str | None
    custom_pose: str | None
    tags: list[str]
    description: str | None
    notes: str | None
    is_primary: bool
    is_identity_anchor: bool
    analysis_status: AnalysisStatus
    suggestion_review_status: SuggestionReviewStatus
    analysis_suggestions: VisionAnalysisSuggestion | None
    media_asset: MediaAssetResponse
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CharacterLookResponse(BaseModel):
    id: str
    character_id: str
    name: str
    description: str | None
    costume_description: str | None
    hair_description: str | None
    makeup_description: str | None
    condition_description: str | None
    prompt_appearance: str | None
    is_default: bool
    reference_count: int = 0
    primary_reference: CharacterReferenceResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CharacterResponse(BaseModel):
    id: str
    project_id: str
    name: str
    aliases: str | None
    role_type: RoleType
    description: str | None
    appearance_description: str | None
    personality_description: str | None
    prompt_identity: str | None
    notes: str | None
    default_look: CharacterLookResponse | None = None
    look_count: int = 0
    reference_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CharacterListResponse(BaseModel):
    items: list[CharacterResponse]
    total: int


class CharacterLookListResponse(BaseModel):
    items: list[CharacterLookResponse]
    total: int


class CharacterReferenceListResponse(BaseModel):
    items: list[CharacterReferenceResponse]
    total: int
