from typing import Annotated

from fastapi import APIRouter, Depends

from app.domain.health import HealthCheckResponse
from app.service.health_service import HealthService, get_health_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthCheckResponse)
def get_health(
    service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthCheckResponse:
    return service.get_health()
