from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.project import (
    ALLOWED_ASPECT_RATIOS,
    ALLOWED_DEFAULT_FPS,
    ALLOWED_DEFAULT_LANGUAGES,
)


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    aspect_ratio: str = "9:16"
    default_style: str | None = Field(default=None, max_length=200)
    default_language: str = "zh-CN"
    default_fps: int = 24

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, value: str) -> str:
        if value not in ALLOWED_ASPECT_RATIOS:
            raise ValueError("INVALID_ASPECT_RATIO")
        return value

    @field_validator("default_language")
    @classmethod
    def validate_default_language(cls, value: str) -> str:
        if value not in ALLOWED_DEFAULT_LANGUAGES:
            raise ValueError("INVALID_DEFAULT_LANGUAGE")
        return value

    @field_validator("default_fps")
    @classmethod
    def validate_default_fps(cls, value: int) -> int:
        if value not in ALLOWED_DEFAULT_FPS:
            raise ValueError("INVALID_DEFAULT_FPS")
        return value


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    aspect_ratio: str | None = None
    default_style: str | None = Field(default=None, max_length=200)
    default_language: str | None = None
    default_fps: int | None = None

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, value: str | None) -> str | None:
        if value is not None and value not in ALLOWED_ASPECT_RATIOS:
            raise ValueError("INVALID_ASPECT_RATIO")
        return value

    @field_validator("default_language")
    @classmethod
    def validate_default_language(cls, value: str | None) -> str | None:
        if value is not None and value not in ALLOWED_DEFAULT_LANGUAGES:
            raise ValueError("INVALID_DEFAULT_LANGUAGE")
        return value

    @field_validator("default_fps")
    @classmethod
    def validate_default_fps(cls, value: int | None) -> int | None:
        if value is not None and value not in ALLOWED_DEFAULT_FPS:
            raise ValueError("INVALID_DEFAULT_FPS")
        return value


class ProjectResponse(BaseModel):
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

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
