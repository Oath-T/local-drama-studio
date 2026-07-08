from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.asset_picker import PickerOptionListResponse
from app.infrastructure.database import get_db_session
from app.repository.asset_picker_repository import AssetPickerRepository
from app.service.asset_picker_service import AssetPickerService

router = APIRouter(prefix="/projects/{project_id}/assets", tags=["asset picker"])


def get_asset_picker_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> AssetPickerService:
    return AssetPickerService(AssetPickerRepository(session))


@router.get("/picker-options", response_model=PickerOptionListResponse)
def list_picker_options(
    project_id: UUID,
    service: Annotated[AssetPickerService, Depends(get_asset_picker_service)],
    scope: Annotated[Literal["project", "shot"], Query()] = "project",
    asset_type: Annotated[
        Literal[
            "character",
            "scene",
            "frame_image",
            "character_look",
            "scene_state",
            "reference_image",
        ],
        Query(),
    ] = "character",
    shot_id: Annotated[UUID | None, Query()] = None,
    character_id: Annotated[UUID | None, Query()] = None,
    scene_id: Annotated[UUID | None, Query()] = None,
    shot_character_id: Annotated[UUID | None, Query()] = None,
    task_id: Annotated[UUID | None, Query()] = None,
    source: Annotated[Literal["shot_context"] | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int | None, Query(ge=1, le=80)] = None,
) -> PickerOptionListResponse:
    return service.list_options(
        project_id,
        scope=scope,
        asset_type=asset_type,
        shot_id=shot_id,
        character_id=character_id,
        scene_id=scene_id,
        shot_character_id=shot_character_id,
        task_id=task_id,
        source=source,
        q=q,
        limit=limit,
    )
