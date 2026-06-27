from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class ProjectErrorCode(StrEnum):
    NOT_FOUND = "PROJECT_NOT_FOUND"
    NAME_REQUIRED = "PROJECT_NAME_REQUIRED"
    NAME_TOO_LONG = "PROJECT_NAME_TOO_LONG"
    DESCRIPTION_TOO_LONG = "PROJECT_DESCRIPTION_TOO_LONG"
    STYLE_TOO_LONG = "PROJECT_STYLE_TOO_LONG"
    INVALID_ASPECT_RATIO = "INVALID_ASPECT_RATIO"
    INVALID_DEFAULT_LANGUAGE = "INVALID_DEFAULT_LANGUAGE"
    INVALID_DEFAULT_FPS = "INVALID_DEFAULT_FPS"
    INVALID_ID = "INVALID_PROJECT_ID"


ALLOWED_ASPECT_RATIOS = ("9:16", "16:9", "1:1", "4:3")
ALLOWED_DEFAULT_LANGUAGES = ("zh-CN", "en-US")
ALLOWED_DEFAULT_FPS = (24, 25, 30)


@dataclass(frozen=True)
class ProjectData:
    id: str
    name: str
    description: str | None
    aspect_ratio: str
    default_style: str | None
    default_language: str
    default_fps: int
    cover_image_path: str | None
    created_at: datetime
    updated_at: datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalize_required_name(value: str | None) -> str:
    if value is None:
        raise ValueError(ProjectErrorCode.NAME_REQUIRED)
    normalized = value.strip()
    if normalized == "":
        raise ValueError(ProjectErrorCode.NAME_REQUIRED)
    if len(normalized) > 100:
        raise ValueError(ProjectErrorCode.NAME_TOO_LONG)
    return normalized


def normalize_nullable_text(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized == "":
        return None
    if len(normalized) > max_length:
        raise ValueError
    return normalized
