from ipaddress import ip_address
from urllib.parse import urlparse

from app.core.config import Settings, get_settings
from app.domain.keyframe_generation import KeyframeGenerationErrorCode
from app.domain.video_generation import VideoGenerationErrorCode
from app.infrastructure.generation.base import (
    GenerationProviderRuntimeError,
    KeyframeGenerationProvider,
    VideoGenerationProvider,
)
from app.infrastructure.generation.comfyui_provider import ComfyUIKeyframeGenerationProvider
from app.infrastructure.generation.comfyui_video_provider import ComfyUIVideoGenerationProvider


def create_keyframe_generation_provider(
    settings: Settings | None = None,
) -> KeyframeGenerationProvider:
    current_settings = settings or get_settings()
    if current_settings.keyframe_provider != "comfyui":
        raise GenerationProviderRuntimeError(
            KeyframeGenerationErrorCode.PROVIDER_NOT_CONFIGURED,
            "Keyframe generation provider is not configured.",
        )
    _validate_comfyui_base_url(current_settings.comfyui_base_url)
    return ComfyUIKeyframeGenerationProvider(current_settings)


def is_keyframe_provider_configured(settings: Settings | None = None) -> bool:
    current_settings = settings or get_settings()
    try:
        if current_settings.keyframe_provider != "comfyui":
            return False
        _validate_comfyui_base_url(current_settings.comfyui_base_url)
    except GenerationProviderRuntimeError:
        return False
    return True


def create_video_generation_provider(settings: Settings | None = None) -> VideoGenerationProvider:
    current_settings = settings or get_settings()
    if current_settings.keyframe_provider != "comfyui":
        raise GenerationProviderRuntimeError(
            VideoGenerationErrorCode.PROVIDER_NOT_CONFIGURED,
            "Video generation provider is not configured.",
        )
    _validate_comfyui_base_url_for_video(current_settings.comfyui_base_url)
    return ComfyUIVideoGenerationProvider(current_settings)


def _validate_comfyui_base_url_for_video(value: str) -> None:
    try:
        _validate_comfyui_base_url(value)
    except GenerationProviderRuntimeError as exc:
        raise GenerationProviderRuntimeError(
            VideoGenerationErrorCode.PROVIDER_NOT_CONFIGURED,
            "ComfyUI base URL is invalid.",
        ) from exc


def _validate_comfyui_base_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise GenerationProviderRuntimeError(
            KeyframeGenerationErrorCode.PROVIDER_NOT_CONFIGURED,
            "ComfyUI base URL is invalid.",
        )
    if parsed.username or parsed.password:
        raise GenerationProviderRuntimeError(
            KeyframeGenerationErrorCode.PROVIDER_NOT_CONFIGURED,
            "ComfyUI base URL must not contain credentials.",
        )
    hostname = parsed.hostname.lower()
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        return
    try:
        address = ip_address(hostname)
    except ValueError as exc:
        raise GenerationProviderRuntimeError(
            KeyframeGenerationErrorCode.PROVIDER_NOT_CONFIGURED,
            "ComfyUI base URL must point to localhost or a LAN address.",
        ) from exc
    if not (address.is_private or address.is_loopback):
        raise GenerationProviderRuntimeError(
            KeyframeGenerationErrorCode.PROVIDER_NOT_CONFIGURED,
            "ComfyUI base URL must point to localhost or a LAN address.",
        )
