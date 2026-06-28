from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.schemas.shot import (
    ShotCharacterCreateRequest,
    ShotCharacterListResponse,
    ShotCharacterResponse,
    ShotCharacterUpdateRequest,
    ShotCreateRequest,
    ShotListResponse,
    ShotMoveRequest,
    ShotReferenceCreateRequest,
    ShotReferenceListResponse,
    ShotReferenceMoveRequest,
    ShotReferenceResponse,
    ShotReferenceUpdateRequest,
    ShotResponse,
    ShotUpdateRequest,
)
from app.infrastructure.database import get_db_session
from app.repository.shot_repository import ShotRepository
from app.service.shot_service import ShotService

router = APIRouter(prefix="/projects/{project_id}/shots", tags=["shots"])


def get_shot_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ShotService:
    return ShotService(ShotRepository(session))


@router.get("", response_model=ShotListResponse)
def list_shots(
    project_id: UUID,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> ShotListResponse:
    return service.list_shots(project_id)


@router.post("", response_model=ShotResponse, status_code=status.HTTP_201_CREATED)
def create_shot(
    project_id: UUID,
    payload: ShotCreateRequest,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> ShotResponse:
    return service.create_shot(project_id, payload)


@router.get("/{shot_id}", response_model=ShotResponse)
def get_shot(
    project_id: UUID,
    shot_id: UUID,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> ShotResponse:
    return service.get_shot(project_id, shot_id)


@router.patch("/{shot_id}", response_model=ShotResponse)
def update_shot(
    project_id: UUID,
    shot_id: UUID,
    payload: ShotUpdateRequest,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> ShotResponse:
    return service.update_shot(project_id, shot_id, payload)


@router.delete("/{shot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shot(
    project_id: UUID,
    shot_id: UUID,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> Response:
    service.delete_shot(project_id, shot_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{shot_id}/move", response_model=ShotResponse)
def move_shot(
    project_id: UUID,
    shot_id: UUID,
    payload: ShotMoveRequest,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> ShotResponse:
    return service.move_shot(project_id, shot_id, payload)


@router.post("/{shot_id}/duplicate", response_model=ShotResponse)
def duplicate_shot(
    project_id: UUID,
    shot_id: UUID,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> ShotResponse:
    return service.duplicate_shot(project_id, shot_id)


@router.get("/{shot_id}/characters", response_model=ShotCharacterListResponse)
def list_shot_characters(
    project_id: UUID,
    shot_id: UUID,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> ShotCharacterListResponse:
    return service.list_characters(project_id, shot_id)


@router.post(
    "/{shot_id}/characters",
    response_model=ShotCharacterResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_shot_character(
    project_id: UUID,
    shot_id: UUID,
    payload: ShotCharacterCreateRequest,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> ShotCharacterResponse:
    return service.add_character(project_id, shot_id, payload)


@router.patch("/{shot_id}/characters/{shot_character_id}", response_model=ShotCharacterResponse)
def update_shot_character(
    project_id: UUID,
    shot_id: UUID,
    shot_character_id: UUID,
    payload: ShotCharacterUpdateRequest,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> ShotCharacterResponse:
    return service.update_character(project_id, shot_id, shot_character_id, payload)


@router.delete("/{shot_id}/characters/{shot_character_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shot_character(
    project_id: UUID,
    shot_id: UUID,
    shot_character_id: UUID,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> Response:
    service.delete_character(project_id, shot_id, shot_character_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{shot_id}/characters/{shot_character_id}/move", response_model=ShotCharacterResponse)
def move_shot_character(
    project_id: UUID,
    shot_id: UUID,
    shot_character_id: UUID,
    payload: ShotMoveRequest,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> ShotCharacterResponse:
    return service.move_character(project_id, shot_id, shot_character_id, payload)


@router.get("/{shot_id}/references", response_model=ShotReferenceListResponse)
def list_shot_references(
    project_id: UUID,
    shot_id: UUID,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> ShotReferenceListResponse:
    return service.list_references(project_id, shot_id)


@router.post(
    "/{shot_id}/references",
    response_model=ShotReferenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_shot_reference(
    project_id: UUID,
    shot_id: UUID,
    payload: ShotReferenceCreateRequest,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> ShotReferenceResponse:
    return service.add_reference(project_id, shot_id, payload)


@router.patch("/{shot_id}/references/{shot_reference_id}", response_model=ShotReferenceResponse)
def update_shot_reference(
    project_id: UUID,
    shot_id: UUID,
    shot_reference_id: UUID,
    payload: ShotReferenceUpdateRequest,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> ShotReferenceResponse:
    return service.update_reference(project_id, shot_id, shot_reference_id, payload)


@router.delete("/{shot_id}/references/{shot_reference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shot_reference(
    project_id: UUID,
    shot_id: UUID,
    shot_reference_id: UUID,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> Response:
    service.delete_reference(project_id, shot_id, shot_reference_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{shot_id}/references/{shot_reference_id}/move", response_model=ShotReferenceResponse)
def move_shot_reference(
    project_id: UUID,
    shot_id: UUID,
    shot_reference_id: UUID,
    payload: ShotReferenceMoveRequest,
    service: Annotated[ShotService, Depends(get_shot_service)],
) -> ShotReferenceResponse:
    return service.move_reference(project_id, shot_id, shot_reference_id, payload)
