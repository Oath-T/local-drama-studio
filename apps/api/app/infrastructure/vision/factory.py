from app.core.config import Settings
from app.domain.vision_analysis import VisionAnalysisErrorCode, VisionProviderRuntimeError
from app.infrastructure.vision.base import VisionAnalysisProvider
from app.infrastructure.vision.openai_provider import OpenAIVisionAnalysisProvider


def create_vision_analysis_provider(settings: Settings) -> VisionAnalysisProvider:
    provider = settings.vision_provider.strip().lower()
    if provider != "openai":
        raise VisionProviderRuntimeError(
            VisionAnalysisErrorCode.PROVIDER_NOT_CONFIGURED,
            "Configured vision provider is not supported.",
            retryable=False,
        )
    if not settings.openai_api_key or not settings.openai_vision_model:
        raise VisionProviderRuntimeError(
            VisionAnalysisErrorCode.PROVIDER_NOT_CONFIGURED,
            "OpenAI vision provider is not configured.",
            retryable=False,
        )
    return OpenAIVisionAnalysisProvider(
        api_key=settings.openai_api_key,
        model_name=settings.openai_vision_model,
        timeout_seconds=settings.vision_analysis_timeout_seconds,
    )


def is_vision_analysis_available(settings: Settings) -> bool:
    return (
        settings.vision_provider.strip().lower() == "openai"
        and bool(settings.openai_api_key)
        and bool(settings.openai_vision_model)
    )
