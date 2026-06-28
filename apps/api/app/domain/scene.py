from enum import StrEnum


class SceneErrorCode(StrEnum):
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    SCENE_NOT_FOUND = "SCENE_NOT_FOUND"
    STATE_NOT_FOUND = "SCENE_STATE_NOT_FOUND"
    REFERENCE_NOT_FOUND = "SCENE_REFERENCE_NOT_FOUND"
    MEDIA_NOT_FOUND = "MEDIA_NOT_FOUND"
    NAME_REQUIRED = "SCENE_NAME_REQUIRED"
    NAME_TOO_LONG = "SCENE_NAME_TOO_LONG"
    STATE_NAME_REQUIRED = "SCENE_STATE_NAME_REQUIRED"
    STATE_NAME_TOO_LONG = "SCENE_STATE_NAME_TOO_LONG"
    CUSTOM_WEATHER_REQUIRED = "CUSTOM_WEATHER_REQUIRED"
    CUSTOM_LIGHTING_REQUIRED = "CUSTOM_LIGHTING_REQUIRED"
    CUSTOM_CAMERA_POSITION_REQUIRED = "CUSTOM_CAMERA_POSITION_REQUIRED"
    CUSTOM_VIEW_DIRECTION_REQUIRED = "CUSTOM_VIEW_DIRECTION_REQUIRED"
    CUSTOM_COMPOSITION_REQUIRED = "CUSTOM_COMPOSITION_REQUIRED"
    LAST_STATE_DELETE_FORBIDDEN = "LAST_SCENE_STATE_DELETE_FORBIDDEN"


class SceneType(StrEnum):
    INTERIOR = "interior"
    EXTERIOR = "exterior"
    MIXED = "mixed"
    VEHICLE = "vehicle"
    VIRTUAL = "virtual"
    OTHER = "other"


class TimeOfDay(StrEnum):
    DAWN = "dawn"
    MORNING = "morning"
    NOON = "noon"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    NIGHT = "night"
    LATE_NIGHT = "late_night"
    UNKNOWN = "unknown"


class Weather(StrEnum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    LIGHT_RAIN = "light_rain"
    HEAVY_RAIN = "heavy_rain"
    STORM = "storm"
    SNOW = "snow"
    FOG = "fog"
    INDOOR = "indoor"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class Lighting(StrEnum):
    NATURAL_SOFT = "natural_soft"
    NATURAL_HARD = "natural_hard"
    WARM_INDOOR = "warm_indoor"
    COOL_INDOOR = "cool_indoor"
    NEON = "neon"
    LOW_KEY = "low_key"
    HIGH_KEY = "high_key"
    BACKLIGHT = "backlight"
    MIXED = "mixed"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class Season(StrEnum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class CrowdLevel(StrEnum):
    EMPTY = "empty"
    SPARSE = "sparse"
    NORMAL = "normal"
    CROWDED = "crowded"
    PACKED = "packed"
    UNKNOWN = "unknown"


class ShotScale(StrEnum):
    EXTREME_WIDE = "extreme_wide"
    WIDE = "wide"
    FULL = "full"
    MEDIUM_WIDE = "medium_wide"
    MEDIUM = "medium"
    CLOSE = "close"
    DETAIL = "detail"
    UNKNOWN = "unknown"


class CameraPosition(StrEnum):
    EYE_LEVEL = "eye_level"
    LOW_ANGLE = "low_angle"
    HIGH_ANGLE = "high_angle"
    GROUND_LEVEL = "ground_level"
    OVERHEAD = "overhead"
    AERIAL = "aerial"
    DOORWAY = "doorway"
    CORNER = "corner"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class ViewDirection(StrEnum):
    FRONT = "front"
    LEFT = "left"
    RIGHT = "right"
    BACK = "back"
    DIAGONAL_LEFT = "diagonal_left"
    DIAGONAL_RIGHT = "diagonal_right"
    INWARD = "inward"
    OUTWARD = "outward"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class CompositionType(StrEnum):
    CENTERED = "centered"
    SYMMETRICAL = "symmetrical"
    RULE_OF_THIRDS = "rule_of_thirds"
    LEADING_LINES = "leading_lines"
    FRAME_WITHIN_FRAME = "frame_within_frame"
    DEEP_FOCUS = "deep_focus"
    LAYERED = "layered"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class AnalysisStatus(StrEnum):
    NOT_ANALYZED = "not_analyzed"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class SuggestionReviewStatus(StrEnum):
    NOT_REVIEWED = "not_reviewed"
    ACCEPTED = "accepted"
    EDITED_AND_ACCEPTED = "edited_and_accepted"
    REJECTED = "rejected"


def normalize_required_text(
    value: str | None,
    required_code: SceneErrorCode,
    too_long_code: SceneErrorCode,
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


def normalize_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    normalized: list[str] = []
    for tag in tags:
        value = tag.strip()
        if value and value not in normalized:
            normalized.append(value[:50])
    return normalized[:20]
