from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class ProjectExportStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectExportErrorCode(StrEnum):
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    EXPORT_NOT_FOUND = "PROJECT_EXPORT_NOT_FOUND"
    NAME_REQUIRED = "PROJECT_EXPORT_NAME_REQUIRED"
    INVALID_DIMENSIONS = "PROJECT_EXPORT_INVALID_DIMENSIONS"
    INVALID_FPS = "PROJECT_EXPORT_INVALID_FPS"
    INVALID_CODEC = "PROJECT_EXPORT_INVALID_CODEC"
    NO_CLIPS = "PROJECT_EXPORT_NO_CLIPS"
    TIMELINE_BLOCKED = "PROJECT_EXPORT_TIMELINE_BLOCKED"
    FFMPEG_UNAVAILABLE = "PROJECT_EXPORT_FFMPEG_UNAVAILABLE"
    FFPROBE_UNAVAILABLE = "PROJECT_EXPORT_FFPROBE_UNAVAILABLE"
    MEDIA_FILE_MISSING = "PROJECT_EXPORT_MEDIA_FILE_MISSING"
    MEDIA_FILE_UNSAFE = "PROJECT_EXPORT_MEDIA_FILE_UNSAFE"
    INVALID_STATUS = "PROJECT_EXPORT_INVALID_STATUS"
    RUN_FAILED = "PROJECT_EXPORT_RUN_FAILED"


ALLOWED_VIDEO_CODECS = ("libx264",)
ALLOWED_OUTPUT_FORMATS = ("mp4",)
DEFAULT_PIXEL_FORMAT = "yuv420p"


@dataclass(frozen=True)
class ExportSettings:
    width: int
    height: int
    fps: int
    codec: str = "libx264"
    pixel_format: str = DEFAULT_PIXEL_FORMAT
    output_format: str = "mp4"


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_export_name(value: str | None) -> str:
    if value is None:
        raise ValueError(ProjectExportErrorCode.NAME_REQUIRED)
    normalized = value.strip()
    if normalized == "":
        raise ValueError(ProjectExportErrorCode.NAME_REQUIRED)
    return normalized[:120]


def validate_export_settings(width: int, height: int, fps: int, codec: str) -> ExportSettings:
    if width < 256 or width > 3840 or width % 2 != 0:
        raise ValueError(ProjectExportErrorCode.INVALID_DIMENSIONS)
    if height < 256 or height > 3840 or height % 2 != 0:
        raise ValueError(ProjectExportErrorCode.INVALID_DIMENSIONS)
    if fps < 1 or fps > 60:
        raise ValueError(ProjectExportErrorCode.INVALID_FPS)
    if codec not in ALLOWED_VIDEO_CODECS:
        raise ValueError(ProjectExportErrorCode.INVALID_CODEC)
    return ExportSettings(width=width, height=height, fps=fps, codec=codec)
