from enum import StrEnum

from pydantic import BaseModel, Field

from app.domain.project_canvas import CanvasEdgeType


class CanvasBindingEdgeStatus(StrEnum):
    DRAFT = "draft"
    APPLIED = "applied"
    FAILED = "failed"


class CanvasBindingDeleteMode(StrEnum):
    HIDE_ONLY = "hide_only"
    UNBIND_BUSINESS = "unbind_business"


class CanvasBindingPayload(BaseModel):
    look_id: str | None = None
    action_description: str | None = Field(default=None, max_length=2000)
    expression_description: str | None = Field(default=None, max_length=1000)
    position_description: str | None = Field(default=None, max_length=1000)
    is_primary_subject: bool | None = None
    notes: str | None = Field(default=None, max_length=1000)
    scene_state_id: str | None = None
    replace_existing_scene: bool = False
    shot_character_id: str | None = None
    character_reference_id: str | None = None
    scene_reference_id: str | None = None
    purpose: str | None = None
    video_task_id: str | None = None
    role: str | None = None
    media_asset_id: str | None = None


class CanvasBindingPreviewRequest(BaseModel):
    source_node_id: str
    target_node_id: str
    semantic_type: CanvasEdgeType
    payload: CanvasBindingPayload = Field(default_factory=CanvasBindingPayload)


class CanvasBindingPreviewResponse(BaseModel):
    semantic_type: CanvasEdgeType
    can_apply: bool
    title: str
    summary: str
    warnings: list[str] = Field(default_factory=list)
    required_fields: list[str] = Field(default_factory=list)


class CanvasBindingApplyRequest(CanvasBindingPreviewRequest):
    expected_revision: int = Field(ge=1)
    edge_id: str | None = None
    apply_business: bool = True


class CanvasBindingDeleteRequest(BaseModel):
    expected_revision: int = Field(ge=1)
    mode: CanvasBindingDeleteMode = CanvasBindingDeleteMode.HIDE_ONLY
