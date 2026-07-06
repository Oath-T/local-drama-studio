from typing import Literal

from pydantic import BaseModel, Field

PickerAssetType = Literal["character", "scene", "frame_image"]
PickerScope = Literal["project", "shot"]
PickerSourceKind = Literal[
    "character",
    "scene",
    "keyframe_output",
    "media_asset",
]


class PickerOptionSource(BaseModel):
    kind: PickerSourceKind
    label: str


class PickerOptionItem(BaseModel):
    id: str
    type: PickerAssetType
    name: str
    description: str | None = None
    thumbnail_url: str | None = None
    content_url: str | None = None
    badges: list[str] = Field(default_factory=list)
    source: PickerOptionSource
    is_selected: bool = False
    is_adopted: bool = False
    metadata: dict[str, str | int | bool | None] = Field(default_factory=dict)


class PickerOptionListResponse(BaseModel):
    items: list[PickerOptionItem]
    total: int
