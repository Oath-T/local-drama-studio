from datetime import UTC, datetime
from enum import StrEnum


class ProjectCanvasErrorCode(StrEnum):
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    CANVAS_NOT_FOUND = "PROJECT_CANVAS_NOT_FOUND"
    NODE_NOT_FOUND = "PROJECT_CANVAS_NODE_NOT_FOUND"
    EDGE_NOT_FOUND = "PROJECT_CANVAS_EDGE_NOT_FOUND"
    REVISION_CONFLICT = "PROJECT_CANVAS_REVISION_CONFLICT"
    INVALID_VIEW_MODE = "INVALID_CANVAS_VIEW_MODE"
    INVALID_NODE_TYPE = "INVALID_CANVAS_NODE_TYPE"
    INVALID_EDGE_TYPE = "INVALID_CANVAS_EDGE_TYPE"
    INVALID_ENTITY = "INVALID_CANVAS_ENTITY"
    INVALID_CONNECTION = "INVALID_CANVAS_CONNECTION"
    INVALID_NODE_DATA = "INVALID_CANVAS_NODE_DATA"


class CanvasViewMode(StrEnum):
    WORKFLOW = "workflow"
    STORYBOARD = "storyboard"


class CanvasNodeType(StrEnum):
    TEXT = "text"
    CHARACTER = "character"
    SCENE = "scene"
    SHOT = "shot"
    IMAGE = "image"
    VIDEO = "video"
    EXPORT = "export"


class CanvasEdgeType(StrEnum):
    USES_CHARACTER = "uses_character"
    USES_SCENE = "uses_scene"
    SHOT_REFERENCE = "shot_reference"
    IDENTITY_REFERENCE = "identity_reference"
    LOOK_REFERENCE = "look_reference"
    SCENE_REFERENCE = "scene_reference"
    POSE_REFERENCE = "pose_reference"
    START_FRAME = "start_frame"
    END_FRAME = "end_frame"
    CONTINUITY_FROM = "continuity_from"
    GENERATED_FROM = "generated_from"
    INCLUDED_IN_EXPORT = "included_in_export"


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_title(value: str | None, fallback: str) -> str:
    normalized = (value or fallback).strip()
    if normalized == "":
        normalized = fallback
    return normalized[:120]
