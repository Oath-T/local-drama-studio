from enum import StrEnum


class MediaType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"


ALLOWED_IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp")
ALLOWED_IMAGE_MIME_TYPES = ("image/jpeg", "image/png", "image/webp")
ALLOWED_VIDEO_EXTENSIONS = ("mp4", "webm", "mov", "gif")
ALLOWED_VIDEO_MIME_TYPES = (
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "image/gif",
)
