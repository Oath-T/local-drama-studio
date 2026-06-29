from fastapi import APIRouter

from app.api.schemas.vision_analysis import VisionAnalysisCapabilitiesResponse
from app.core.config import get_settings
from app.infrastructure.vision.factory import is_vision_analysis_available

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/capabilities", response_model=VisionAnalysisCapabilitiesResponse)
def get_capabilities() -> VisionAnalysisCapabilitiesResponse:
    settings = get_settings()
    return VisionAnalysisCapabilitiesResponse(
        vision_analysis={
            "available": is_vision_analysis_available(settings),
            "provider": settings.vision_provider,
        }
    )
