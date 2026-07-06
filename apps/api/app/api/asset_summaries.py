from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.asset_summary import (
    CharacterAssetSummaryResponse,
    SceneAssetSummaryResponse,
    ShotAssetSummaryResponse,
)
from app.infrastructure.database import get_db_session
from app.repository.asset_summary_repository import AssetSummaryRepository
from app.service.asset_summary_service import AssetSummaryService

router = APIRouter(prefix="/projects/{project_id}", tags=["asset summaries"])


def get_asset_summary_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> AssetSummaryService:
    return AssetSummaryService(AssetSummaryRepository(session))


@router.get(
    "/characters/{character_id}/asset-summary",
    response_model=CharacterAssetSummaryResponse,
)
def get_character_asset_summary(
    project_id: UUID,
    character_id: UUID,
    service: Annotated[AssetSummaryService, Depends(get_asset_summary_service)],
) -> CharacterAssetSummaryResponse:
    return service.get_character_summary(project_id, character_id)


@router.get(
    "/scenes/{scene_id}/asset-summary",
    response_model=SceneAssetSummaryResponse,
)
def get_scene_asset_summary(
    project_id: UUID,
    scene_id: UUID,
    service: Annotated[AssetSummaryService, Depends(get_asset_summary_service)],
) -> SceneAssetSummaryResponse:
    return service.get_scene_summary(project_id, scene_id)


@router.get(
    "/shots/{shot_id}/asset-summary",
    response_model=ShotAssetSummaryResponse,
)
def get_shot_asset_summary(
    project_id: UUID,
    shot_id: UUID,
    service: Annotated[AssetSummaryService, Depends(get_asset_summary_service)],
) -> ShotAssetSummaryResponse:
    return service.get_shot_summary(project_id, shot_id)
