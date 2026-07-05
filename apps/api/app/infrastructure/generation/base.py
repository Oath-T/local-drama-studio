from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


@dataclass(frozen=True)
class GenerationProviderHealth:
    available: bool
    provider: str
    status: str


@dataclass(frozen=True)
class KeyframeProviderRequest:
    workflow: dict[str, object]
    client_id: str


@dataclass(frozen=True)
class VideoProviderRequest:
    workflow: dict[str, object]
    client_id: str


@dataclass(frozen=True)
class ProviderSubmission:
    provider_job_id: str


@dataclass(frozen=True)
class ProviderJobStatus:
    status: str
    error_code: StrEnum | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class ProviderOutputImage:
    filename: str
    subfolder: str = ""
    output_type: str = "output"
    mime_type: str | None = None
    content: bytes = field(default_factory=bytes)


@dataclass(frozen=True)
class ProviderUploadedImage:
    filename: str
    subfolder: str = ""
    input_type: str = "input"


@dataclass(frozen=True)
class ProviderOutputFile:
    filename: str
    subfolder: str = ""
    output_type: str = "output"
    mime_type: str | None = None
    content: bytes = field(default_factory=bytes)


class GenerationProviderRuntimeError(Exception):
    def __init__(
        self,
        code: StrEnum,
        message: str,
        *,
        retryable: bool = False,
    ) -> None:
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


class KeyframeGenerationProvider(Protocol):
    async def check_health(self) -> GenerationProviderHealth: ...

    async def get_required_node_types(self) -> set[str]: ...

    async def submit(self, request: KeyframeProviderRequest) -> ProviderSubmission: ...

    async def get_status(self, provider_job_id: str) -> ProviderJobStatus: ...

    async def fetch_outputs(self, provider_job_id: str) -> list[ProviderOutputImage]: ...

    async def cancel(self, provider_job_id: str) -> None: ...


class VideoGenerationProvider(Protocol):
    async def check_health(self) -> GenerationProviderHealth: ...

    async def get_required_node_types(self) -> set[str]: ...

    async def upload_input_image(
        self,
        *,
        filename: str,
        content: bytes,
        mime_type: str | None,
    ) -> ProviderUploadedImage: ...

    async def submit(self, request: VideoProviderRequest) -> ProviderSubmission: ...

    async def get_status(self, provider_job_id: str) -> ProviderJobStatus: ...

    async def fetch_video_outputs(
        self,
        provider_job_id: str,
        *,
        output_node_ids: list[str],
        output_file_keys: list[str],
        allowed_extensions: list[str],
    ) -> list[ProviderOutputFile]: ...
