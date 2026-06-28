from enum import StrEnum


class CharacterErrorCode(StrEnum):
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    CHARACTER_NOT_FOUND = "CHARACTER_NOT_FOUND"
    LOOK_NOT_FOUND = "CHARACTER_LOOK_NOT_FOUND"
    REFERENCE_NOT_FOUND = "CHARACTER_REFERENCE_NOT_FOUND"
    MEDIA_NOT_FOUND = "MEDIA_NOT_FOUND"
    NAME_REQUIRED = "CHARACTER_NAME_REQUIRED"
    NAME_TOO_LONG = "CHARACTER_NAME_TOO_LONG"
    LOOK_NAME_REQUIRED = "CHARACTER_LOOK_NAME_REQUIRED"
    LOOK_NAME_TOO_LONG = "CHARACTER_LOOK_NAME_TOO_LONG"
    INVALID_ROLE_TYPE = "INVALID_ROLE_TYPE"
    INVALID_SHOT_TYPE = "INVALID_SHOT_TYPE"
    INVALID_VIEW_ANGLE = "INVALID_VIEW_ANGLE"
    INVALID_EXPRESSION = "INVALID_EXPRESSION"
    INVALID_POSE_TYPE = "INVALID_POSE_TYPE"
    INVALID_ANALYSIS_STATUS = "INVALID_ANALYSIS_STATUS"
    INVALID_SUGGESTION_REVIEW_STATUS = "INVALID_SUGGESTION_REVIEW_STATUS"
    LAST_LOOK_DELETE_FORBIDDEN = "LAST_LOOK_DELETE_FORBIDDEN"
    IMAGE_EXTENSION_NOT_ALLOWED = "IMAGE_EXTENSION_NOT_ALLOWED"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    IMAGE_INVALID = "IMAGE_INVALID"
    IMAGE_UPLOAD_FAILED = "IMAGE_UPLOAD_FAILED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"


class RoleType(StrEnum):
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
    EXTRA = "extra"
    OTHER = "other"


class ShotType(StrEnum):
    FACE_CLOSEUP = "face_closeup"
    CLOSEUP = "closeup"
    UPPER_BODY = "upper_body"
    HALF_BODY = "half_body"
    THREE_QUARTER = "three_quarter"
    FULL_BODY = "full_body"
    UNKNOWN = "unknown"


class ViewAngle(StrEnum):
    FRONT = "front"
    LEFT_45 = "left_45"
    RIGHT_45 = "right_45"
    LEFT_PROFILE = "left_profile"
    RIGHT_PROFILE = "right_profile"
    BACK = "back"
    HIGH_ANGLE = "high_angle"
    LOW_ANGLE = "low_angle"
    UNKNOWN = "unknown"


class Expression(StrEnum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SMILE = "smile"
    SAD = "sad"
    ANGRY = "angry"
    SHOCKED = "shocked"
    FEARFUL = "fearful"
    CRYING = "crying"
    COLD_SMIRK = "cold_smirk"
    SERIOUS = "serious"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class PoseType(StrEnum):
    STANDING = "standing"
    SITTING = "sitting"
    WALKING = "walking"
    LOOKING_CAMERA = "looking_camera"
    LOOKING_AWAY = "looking_away"
    HOLDING_OBJECT = "holding_object"
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
    required_code: CharacterErrorCode,
    too_long_code: CharacterErrorCode,
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
