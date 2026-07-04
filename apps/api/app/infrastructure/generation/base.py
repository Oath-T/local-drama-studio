from dataclasses import dataclass, field
from typing import Protocol

from app.domain.keyframe_generation import KeyframeGenerationErrorCode


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
class ProviderSubmission:
    provider_job_id: str


@dataclass(frozen=True)
class ProviderJobStatus:
    status: str
    error_code: KeyframeGenerationErrorCode | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class ProviderOutputImage:
    filename: str
    subfolder: str = ""
    output_type: str = "output"
    mime_type: str | None = None
    content: bytes = field(default_factory=bytes)


class GenerationProviderRuntimeError(Exception):
    def __init__(
        self,
        code: KeyframeGenerationErrorCode,
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
