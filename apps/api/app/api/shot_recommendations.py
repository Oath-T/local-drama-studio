from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.shot_recommendation import ShotRecommendationResponse
from app.infrastructure.database import get_db_session
from app.repository.shot_recommendation_repository import ShotRecommendationRepository
from app.service.shot_recommendation_service import ShotRecommendationService

router = APIRouter(
    prefix="/projects/{project_id}/shots",
    tags=["shot-recommendations"],
)


def get_shot_recommendation_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ShotRecommendationService:
    return ShotRecommendationService(ShotRecommendationRepository(session))


@router.get("/{shot_id}/recommendations", response_model=ShotRecommendationResponse)
def get_shot_recommendations(
    project_id: UUID,
    shot_id: UUID,
    service: Annotated[
        ShotRecommendationService,
        Depends(get_shot_recommendation_service),
    ],
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> ShotRecommendationResponse:
    return service.get_recommendations(project_id, shot_id, limit)
