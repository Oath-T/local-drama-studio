from enum import StrEnum


class KeyframeTaskStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"


class KeyframeTaskReadinessStatus(StrEnum):
    INCOMPLETE = "incomplete"
    READY = "ready"


class KeyframeTaskReferenceType(StrEnum):
    CHARACTER = "character"
    SCENE = "scene"


class KeyframeTaskAspectRatio(StrEnum):
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    SQUARE = "1:1"
    STANDARD = "4:3"
    VERTICAL_STANDARD = "3:4"
    CUSTOM = "custom"


class KeyframeTaskBlockingIssue(StrEnum):
    MISSING_NAME = "missing_name"
    NO_PROMPT = "no_prompt"
    INVALID_DIMENSIONS = "invalid_dimensions"
    ASPECT_RATIO_MISMATCH = "aspect_ratio_mismatch"
    INVALID_STEPS = "invalid_steps"
    INVALID_GUIDANCE = "invalid_guidance"
    INVALID_OUTPUT_COUNT = "invalid_output_count"
    MISSING_PRIMARY_CHARACTER_REFERENCE = "missing_primary_character_reference"
    MISSING_SCENE_REFERENCE = "missing_scene_reference"
    UNAVAILABLE_MEDIA = "unavailable_media"


class KeyframeTaskWarningIssue(StrEnum):
    NO_ENGLISH_PROMPT = "no_english_prompt"
    NO_NEGATIVE_PROMPT = "no_negative_prompt"
    NO_MODEL_SELECTED = "no_model_selected"
    SHOT_CHANGED_SINCE_SNAPSHOT = "shot_changed_since_snapshot"
    NO_IDENTITY_REFERENCE = "no_identity_reference"
    NO_SPATIAL_REFERENCE = "no_spatial_reference"
    NO_SEED = "no_seed"
    MISSING_SECONDARY_CHARACTER_REFERENCE = "missing_secondary_character_reference"


class KeyframeTaskErrorCode(StrEnum):
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    SHOT_NOT_FOUND = "SHOT_NOT_FOUND"
    TASK_NOT_FOUND = "KEYFRAME_TASK_NOT_FOUND"
    TASK_REFERENCE_NOT_FOUND = "KEYFRAME_TASK_REFERENCE_NOT_FOUND"
    SHOT_REFERENCE_NOT_FOUND = "SHOT_REFERENCE_NOT_FOUND"
    NAME_REQUIRED = "KEYFRAME_TASK_NAME_REQUIRED"
    NAME_TOO_LONG = "KEYFRAME_TASK_NAME_TOO_LONG"
    INVALID_STATUS = "INVALID_KEYFRAME_TASK_STATUS"
    INVALID_ASPECT_RATIO = "INVALID_KEYFRAME_ASPECT_RATIO"
    INVALID_DIMENSIONS = "INVALID_KEYFRAME_DIMENSIONS"
    INVALID_STEPS = "INVALID_KEYFRAME_STEPS"
    INVALID_GUIDANCE = "INVALID_KEYFRAME_GUIDANCE"
    INVALID_OUTPUT_COUNT = "INVALID_KEYFRAME_OUTPUT_COUNT"
    INVALID_SEED = "INVALID_KEYFRAME_SEED"
    INVALID_REFERENCE_TYPE = "INVALID_KEYFRAME_REFERENCE_TYPE"
    INVALID_REFERENCE_PURPOSE = "INVALID_KEYFRAME_REFERENCE_PURPOSE"
    REFERENCE_ALREADY_EXISTS = "KEYFRAME_TASK_REFERENCE_ALREADY_EXISTS"
    TASK_NOT_READY = "KEYFRAME_TASK_NOT_READY"
    MEDIA_IN_USE_BY_KEYFRAME_TASK = "MEDIA_IN_USE_BY_KEYFRAME_TASK"
    DATABASE_CONFLICT = "DATABASE_CONFLICT"


BLOCKING_ISSUE_ORDER: tuple[KeyframeTaskBlockingIssue, ...] = (
    KeyframeTaskBlockingIssue.MISSING_NAME,
    KeyframeTaskBlockingIssue.NO_PROMPT,
    KeyframeTaskBlockingIssue.INVALID_DIMENSIONS,
    KeyframeTaskBlockingIssue.ASPECT_RATIO_MISMATCH,
    KeyframeTaskBlockingIssue.INVALID_STEPS,
    KeyframeTaskBlockingIssue.INVALID_GUIDANCE,
    KeyframeTaskBlockingIssue.INVALID_OUTPUT_COUNT,
    KeyframeTaskBlockingIssue.MISSING_PRIMARY_CHARACTER_REFERENCE,
    KeyframeTaskBlockingIssue.MISSING_SCENE_REFERENCE,
    KeyframeTaskBlockingIssue.UNAVAILABLE_MEDIA,
)

WARNING_ISSUE_ORDER: tuple[KeyframeTaskWarningIssue, ...] = (
    KeyframeTaskWarningIssue.NO_ENGLISH_PROMPT,
    KeyframeTaskWarningIssue.NO_NEGATIVE_PROMPT,
    KeyframeTaskWarningIssue.NO_MODEL_SELECTED,
    KeyframeTaskWarningIssue.SHOT_CHANGED_SINCE_SNAPSHOT,
    KeyframeTaskWarningIssue.NO_IDENTITY_REFERENCE,
    KeyframeTaskWarningIssue.NO_SPATIAL_REFERENCE,
    KeyframeTaskWarningIssue.NO_SEED,
    KeyframeTaskWarningIssue.MISSING_SECONDARY_CHARACTER_REFERENCE,
)

ASPECT_RATIO_DIMENSIONS: dict[KeyframeTaskAspectRatio, tuple[int, int]] = {
    KeyframeTaskAspectRatio.PORTRAIT: (768, 1360),
    KeyframeTaskAspectRatio.LANDSCAPE: (1360, 768),
    KeyframeTaskAspectRatio.SQUARE: (1024, 1024),
    KeyframeTaskAspectRatio.STANDARD: (1024, 768),
    KeyframeTaskAspectRatio.VERTICAL_STANDARD: (768, 1024),
}

DEFAULT_ASPECT_RATIO = KeyframeTaskAspectRatio.PORTRAIT
DEFAULT_WIDTH, DEFAULT_HEIGHT = ASPECT_RATIO_DIMENSIONS[DEFAULT_ASPECT_RATIO]
DEFAULT_STEPS = 30
DEFAULT_GUIDANCE_SCALE = 7.0
DEFAULT_OUTPUT_COUNT = 1
DEFAULT_NEGATIVE_PROMPT = "低质量，模糊，畸形手部，多余手指，重复人物，错误文字，水印"


def normalize_optional_text(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized == "":
        return None
    if len(normalized) > max_length:
        raise ValueError
    return normalized


def normalize_required_text(
    value: str | None,
    required_code: KeyframeTaskErrorCode,
    too_long_code: KeyframeTaskErrorCode,
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


def is_valid_dimension(value: int) -> bool:
    return 256 <= value <= 4096 and value % 8 == 0


def aspect_ratio_matches(aspect_ratio: KeyframeTaskAspectRatio, width: int, height: int) -> bool:
    if aspect_ratio == KeyframeTaskAspectRatio.CUSTOM:
        return True
    if ASPECT_RATIO_DIMENSIONS.get(aspect_ratio) == (width, height):
        return True
    expected = {
        KeyframeTaskAspectRatio.PORTRAIT: (9, 16),
        KeyframeTaskAspectRatio.LANDSCAPE: (16, 9),
        KeyframeTaskAspectRatio.SQUARE: (1, 1),
        KeyframeTaskAspectRatio.STANDARD: (4, 3),
        KeyframeTaskAspectRatio.VERTICAL_STANDARD: (3, 4),
    }[aspect_ratio]
    return width * expected[1] == height * expected[0]
