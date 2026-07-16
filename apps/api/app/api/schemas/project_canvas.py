from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.project_canvas import CanvasEdgeType, CanvasNodeType, CanvasViewMode


class CanvasViewport(BaseModel):
    x: float = 0
    y: float = 0
    zoom: float = Field(default=1, ge=0.1, le=4)


class CanvasNodeData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collapsed: bool | None = None
    note: str | None = None
    display_variant: str | None = None
    thumbnail_override: str | None = None
    temporary_label: str | None = None


class CanvasEdgeData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = None
    status: str | None = None
    business_entity_type: str | None = None
    business_entity_id: str | None = None
    error_message: str | None = None
    applied_at: datetime | None = None
    binding_payload: dict[str, Any] | None = None


class CanvasNodeResponse(BaseModel):
    id: str
    node_type: CanvasNodeType
    title: str
    position_x: float
    position_y: float
    width: float
    height: float
    z_index: int
    entity_type: str | None
    entity_id: str | None
    data: CanvasNodeData
    created_at: datetime
    updated_at: datetime


class CanvasEdgeResponse(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str
    source_handle: str | None
    target_handle: str | None
    semantic_type: CanvasEdgeType
    data: CanvasEdgeData
    created_at: datetime
    updated_at: datetime


class ProjectCanvasResponse(BaseModel):
    id: str
    project_id: str
    view_mode: CanvasViewMode
    viewport: CanvasViewport
    layout_version: int
    revision: int
    nodes: list[CanvasNodeResponse]
    edges: list[CanvasEdgeResponse]
    created_at: datetime
    updated_at: datetime


class CanvasNodeUpsert(BaseModel):
    id: str | None = None
    node_type: CanvasNodeType
    title: str | None = None
    position_x: float = 0
    position_y: float = 0
    width: float = Field(default=240, gt=0)
    height: float = Field(default=160, gt=0)
    z_index: int = 0
    entity_type: str | None = None
    entity_id: str | None = None
    data: CanvasNodeData = Field(default_factory=CanvasNodeData)


class CanvasNodePatchRequest(BaseModel):
    expected_revision: int
    title: str | None = None
    position_x: float | None = None
    position_y: float | None = None
    width: float | None = Field(default=None, gt=0)
    height: float | None = Field(default=None, gt=0)
    z_index: int | None = None
    data: CanvasNodeData | None = None


class CanvasEdgeUpsert(BaseModel):
    id: str | None = None
    source_node_id: str
    target_node_id: str
    source_handle: str | None = None
    target_handle: str | None = None
    semantic_type: CanvasEdgeType
    data: CanvasEdgeData = Field(default_factory=CanvasEdgeData)


class CanvasNodeCreateRequest(CanvasNodeUpsert):
    expected_revision: int


class CanvasEdgeCreateRequest(CanvasEdgeUpsert):
    expected_revision: int


class ProjectCanvasSaveRequest(BaseModel):
    expected_revision: int
    view_mode: CanvasViewMode
    viewport: CanvasViewport
    nodes: list[CanvasNodeUpsert]
    edges: list[CanvasEdgeUpsert]


class CanvasEntityBatchRequest(BaseModel):
    expected_revision: int
    include_characters: bool = True
    include_scenes: bool = True
    include_shots: bool = True


class CanvasEntityBatchPreview(BaseModel):
    character_count: int
    scene_count: int
    shot_count: int
    total: int


JsonDict = dict[str, Any]
