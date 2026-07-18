from enum import StrEnum


class ShotErrorCode(StrEnum):
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    SHOT_NOT_FOUND = "SHOT_NOT_FOUND"
    SHOT_CHARACTER_NOT_FOUND = "SHOT_CHARACTER_NOT_FOUND"
    SHOT_REFERENCE_NOT_FOUND = "SHOT_REFERENCE_NOT_FOUND"
    SCENE_NOT_FOUND = "SCENE_NOT_FOUND"
    SCENE_STATE_NOT_FOUND = "SCENE_STATE_NOT_FOUND"
    CHARACTER_NOT_FOUND = "CHARACTER_NOT_FOUND"
    LOOK_NOT_FOUND = "CHARACTER_LOOK_NOT_FOUND"
    CHARACTER_REFERENCE_NOT_FOUND = "CHARACTER_REFERENCE_NOT_FOUND"
    SCENE_REFERENCE_NOT_FOUND = "SCENE_REFERENCE_NOT_FOUND"
    MEDIA_ASSET_NOT_FOUND = "MEDIA_ASSET_NOT_FOUND"
    NAME_REQUIRED = "SHOT_NAME_REQUIRED"
    NAME_TOO_LONG = "SHOT_NAME_TOO_LONG"
    CUSTOM_CAMERA_HEIGHT_REQUIRED = "CUSTOM_CAMERA_HEIGHT_REQUIRED"
    CUSTOM_CAMERA_ANGLE_REQUIRED = "CUSTOM_CAMERA_ANGLE_REQUIRED"
    CUSTOM_COMPOSITION_REQUIRED = "CUSTOM_COMPOSITION_REQUIRED"
    CUSTOM_CAMERA_MOVEMENT_REQUIRED = "CUSTOM_CAMERA_MOVEMENT_REQUIRED"
    SCENE_STATE_REQUIRES_SCENE = "SCENE_STATE_REQUIRES_SCENE"
    SCENE_STATE_MISMATCH = "SCENE_STATE_MISMATCH"
    CHARACTER_ALREADY_IN_SHOT = "CHARACTER_ALREADY_IN_SHOT"
    LOOK_CHARACTER_MISMATCH = "LOOK_CHARACTER_MISMATCH"
    INVALID_REFERENCE_TYPE = "INVALID_REFERENCE_TYPE"
    INVALID_REFERENCE_PURPOSE = "INVALID_REFERENCE_PURPOSE"
    REFERENCE_REQUIRES_SCENE_STATE = "REFERENCE_REQUIRES_SCENE_STATE"
    REFERENCE_SCENE_STATE_MISMATCH = "REFERENCE_SCENE_STATE_MISMATCH"
    REFERENCE_CHARACTER_MISMATCH = "REFERENCE_CHARACTER_MISMATCH"
    REFERENCE_ALREADY_BOUND = "SHOT_REFERENCE_ALREADY_BOUND"
    INVALID_ORDER_INDEX = "INVALID_ORDER_INDEX"
    DATABASE_CONFLICT = "DATABASE_CONFLICT"


class ShotScale(StrEnum):
    EXTREME_WIDE = "extreme_wide"
    WIDE = "wide"
    FULL = "full"
    MEDIUM_WIDE = "medium_wide"
    MEDIUM = "medium"
    MEDIUM_CLOSE = "medium_close"
    CLOSE = "close"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    UNKNOWN = "unknown"


class CameraHeight(StrEnum):
    GROUND = "ground"
    LOW = "low"
    EYE_LEVEL = "eye_level"
    HIGH = "high"
    OVERHEAD = "overhead"
    AERIAL = "aerial"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class CameraAngle(StrEnum):
    FRONT = "front"
    BACK = "back"
    LEFT_PROFILE = "left_profile"
    RIGHT_PROFILE = "right_profile"
    LEFT_THREE_QUARTER = "left_three_quarter"
    RIGHT_THREE_QUARTER = "right_three_quarter"
    TOP_DOWN = "top_down"
    DUTCH_ANGLE = "dutch_angle"
    POV = "pov"
    OVER_THE_SHOULDER = "over_the_shoulder"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class ShotCompositionType(StrEnum):
    CENTERED = "centered"
    SYMMETRICAL = "symmetrical"
    RULE_OF_THIRDS = "rule_of_thirds"
    LEADING_LINES = "leading_lines"
    FRAME_WITHIN_FRAME = "frame_within_frame"
    LAYERED = "layered"
    NEGATIVE_SPACE = "negative_space"
    CLOSE_BLOCKING = "close_blocking"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class CameraMovement(StrEnum):
    STATIC = "static"
    PUSH_IN = "push_in"
    PULL_OUT = "pull_out"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    TRACKING = "tracking"
    ORBIT = "orbit"
    HANDHELD = "handheld"
    CRANE = "crane"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class ReadinessStatus(StrEnum):
    DRAFT = "draft"
    BASIC_READY = "basic_ready"
    ASSET_READY = "asset_ready"


class MissingItem(StrEnum):
    VISUAL_DESCRIPTION = "visual_description"
    SCENE = "scene"
    SCENE_STATE = "scene_state"
    CHARACTERS = "characters"
    PRIMARY_SUBJECT = "primary_subject"
    CHARACTER_REFERENCES = "character_references"
    SCENE_REFERENCES = "scene_references"


class ShotReferenceType(StrEnum):
    CHARACTER = "character"
    SCENE = "scene"
    MEDIA = "media"


class CharacterReferencePurpose(StrEnum):
    IDENTITY = "identity"
    APPEARANCE = "appearance"
    EXPRESSION = "expression"
    POSE = "pose"
    FRAMING = "framing"
    GENERAL = "general"


class SceneReferencePurpose(StrEnum):
    ENVIRONMENT = "environment"
    SPATIAL = "spatial"
    COMPOSITION = "composition"
    LIGHTING = "lighting"
    CAMERA_REFERENCE = "camera_reference"
    GENERAL = "general"


class MediaReferencePurpose(StrEnum):
    GENERAL = "general"


def normalize_required_text(
    value: str | None,
    required_code: ShotErrorCode,
    too_long_code: ShotErrorCode,
    max_length: int,
) -> str:
    if value is None:
        raise ValueError(required_code)
    normalized = value.strip()
    if normalized == "":
        raise ValueError(required_code)
    if len(normalized) > max_length:
        raise ValueError(too_long_code)
    return normalized


def normalize_optional_text(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized == "":
        return None
    if len(normalized) > max_length:
        raise ValueError
    return normalized
