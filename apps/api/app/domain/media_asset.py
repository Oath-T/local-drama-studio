from enum import StrEnum


class MediaType(StrEnum):
    IMAGE = "image"


ALLOWED_IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp")
ALLOWED_IMAGE_MIME_TYPES = ("image/jpeg", "image/png", "image/webp")
