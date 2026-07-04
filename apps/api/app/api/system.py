from fastapi import APIRouter

from app.api.schemas.vision_analysis import VisionAnalysisCapabilitiesResponse
from app.core.config import get_settings
from app.infrastructure.generation.base import GenerationProviderRuntimeError
from app.infrastructure.generation.factory import create_keyframe_generation_provider
from app.infrastructure.vision.factory import is_vision_analysis_available

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/capabilities", response_model=VisionAnalysisCapabilitiesResponse)
async def get_capabilities() -> VisionAnalysisCapabilitiesResponse:
    settings = get_settings()
    keyframe_generation = {
        "available": False,
        "provider": settings.keyframe_provider,
        "status": "unconfigured",
    }
    try:
        provider = create_keyframe_generation_provider(settings)
        health = await provider.check_health()
        keyframe_generation = {
            "available": health.available,
            "provider": health.provider,
            "status": health.status,
        }
    except GenerationProviderRuntimeError:
        pass
    return VisionAnalysisCapabilitiesResponse(
        vision_analysis={
            "available": is_vision_analysis_available(settings),
            "provider": settings.vision_provider,
        },
        keyframe_generation=keyframe_generation,
    )
