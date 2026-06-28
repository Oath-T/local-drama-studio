from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def get_default_storage_dir() -> Path:
    return get_repository_root() / "storage"


def get_default_database_url() -> str:
    database_path = get_default_storage_dir() / "local-drama-studio.db"
    return f"sqlite:///{database_path.as_posix()}"


class Settings(BaseSettings):
    app_name: str = "Local Drama Studio API"
    app_version: str = "0.1.0"
    database_url: str = Field(default_factory=get_default_database_url)
    storage_dir: Path = Field(default_factory=get_default_storage_dir)
    max_image_upload_mb: int = 15
    thumbnail_max_size: int = 512
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    model_config = SettingsConfigDict(
        env_prefix="LDS_API_",
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def use_default_database_url_when_empty(cls, value: str | None) -> str:
        if value is None or value == "":
            return get_default_database_url()
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("storage_dir", mode="before")
    @classmethod
    def parse_storage_dir(cls, value: str | Path | None) -> Path:
        if value is None or value == "":
            return get_default_storage_dir()
        return Path(value)

    @property
    def resolved_storage_dir(self) -> Path:
        if self.storage_dir.is_absolute():
            return self.storage_dir
        return get_repository_root() / self.storage_dir


@lru_cache
def get_settings() -> Settings:
    return Settings()
