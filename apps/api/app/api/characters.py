import mimetypes
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.schemas.character import (
    CharacterCreateRequest,
    CharacterListResponse,
    CharacterLookCreateRequest,
    CharacterLookListResponse,
    CharacterLookResponse,
    CharacterLookUpdateRequest,
    CharacterReferenceListResponse,
    CharacterReferenceResponse,
    CharacterReferenceUpdateRequest,
    CharacterResponse,
    CharacterUpdateRequest,
)
from app.domain.character import Expression, PoseType, ShotType, ViewAngle
from app.infrastructure.database import get_db_session
from app.repository.character_repository import CharacterRepository
from app.service.character_service import CharacterService
from app.service.media_storage_service import MediaStorageService

router = APIRouter(prefix="/projects/{project_id}/characters", tags=["characters"])
media_router = APIRouter(prefix="/media", tags=["media"])
THUMBNAIL_MIME_TYPES = {
    ".webp": "image/webp",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def get_character_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> CharacterService:
    return CharacterService(CharacterRepository(session))


@router.get("", response_model=CharacterListResponse)
def list_characters(
    project_id: UUID,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterListResponse:
    return service.list_characters(project_id)


@router.post("", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
def create_character(
    project_id: UUID,
    payload: CharacterCreateRequest,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterResponse:
    return service.create_character(project_id, payload)


@router.get("/{character_id}", response_model=CharacterResponse)
def get_character(
    project_id: UUID,
    character_id: UUID,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterResponse:
    return service.get_character(project_id, character_id)


@router.patch("/{character_id}", response_model=CharacterResponse)
def update_character(
    project_id: UUID,
    character_id: UUID,
    payload: CharacterUpdateRequest,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterResponse:
    return service.update_character(project_id, character_id, payload)


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_character(
    project_id: UUID,
    character_id: UUID,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> Response:
    service.delete_character(project_id, character_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{character_id}/looks", response_model=CharacterLookListResponse)
def list_looks(
    project_id: UUID,
    character_id: UUID,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterLookListResponse:
    return service.list_looks(project_id, character_id)


@router.post(
    "/{character_id}/looks",
    response_model=CharacterLookResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_look(
    project_id: UUID,
    character_id: UUID,
    payload: CharacterLookCreateRequest,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterLookResponse:
    return service.create_look(project_id, character_id, payload)


@router.get("/{character_id}/looks/{look_id}", response_model=CharacterLookResponse)
def get_look(
    project_id: UUID,
    character_id: UUID,
    look_id: UUID,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterLookResponse:
    return service.get_look(project_id, character_id, look_id)


@router.patch("/{character_id}/looks/{look_id}", response_model=CharacterLookResponse)
def update_look(
    project_id: UUID,
    character_id: UUID,
    look_id: UUID,
    payload: CharacterLookUpdateRequest,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterLookResponse:
    return service.update_look(project_id, character_id, look_id, payload)


@router.post("/{character_id}/looks/{look_id}/set-default", response_model=CharacterLookResponse)
def set_default_look(
    project_id: UUID,
    character_id: UUID,
    look_id: UUID,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterLookResponse:
    return service.set_default_look(project_id, character_id, look_id)


@router.delete("/{character_id}/looks/{look_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_look(
    project_id: UUID,
    character_id: UUID,
    look_id: UUID,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> Response:
    service.delete_look(project_id, character_id, look_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{character_id}/looks/{look_id}/references",
    response_model=CharacterReferenceListResponse,
)
def list_references(
    project_id: UUID,
    character_id: UUID,
    look_id: UUID,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterReferenceListResponse:
    return service.list_references(project_id, character_id, look_id)


@router.post(
    "/{character_id}/looks/{look_id}/references",
    response_model=CharacterReferenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_reference(
    project_id: UUID,
    character_id: UUID,
    look_id: UUID,
    service: Annotated[CharacterService, Depends(get_character_service)],
    file: Annotated[UploadFile, File()],
    shot_type: Annotated[ShotType, Form()] = ShotType.UNKNOWN,
    view_angle: Annotated[ViewAngle, Form()] = ViewAngle.UNKNOWN,
    expression: Annotated[Expression, Form()] = Expression.UNKNOWN,
    pose_type: Annotated[PoseType, Form()] = PoseType.UNKNOWN,
    custom_expression: Annotated[str | None, Form()] = None,
    custom_pose: Annotated[str | None, Form()] = None,
    tags: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
    is_identity_anchor: Annotated[bool, Form()] = False,
) -> CharacterReferenceResponse:
    payload = CharacterReferenceUpdateRequest(
        shot_type=shot_type,
        view_angle=view_angle,
        expression=expression,
        pose_type=pose_type,
        custom_expression=custom_expression,
        custom_pose=custom_pose,
        tags=[tag.strip() for tag in tags.split(",")] if tags else [],
        description=description,
        notes=notes,
        is_identity_anchor=is_identity_anchor,
    )
    return await service.upload_reference(project_id, character_id, look_id, file, payload)


@router.get(
    "/{character_id}/looks/{look_id}/references/{reference_id}",
    response_model=CharacterReferenceResponse,
)
def get_reference(
    project_id: UUID,
    character_id: UUID,
    look_id: UUID,
    reference_id: UUID,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterReferenceResponse:
    return service.get_reference(project_id, character_id, look_id, reference_id)


@router.patch(
    "/{character_id}/looks/{look_id}/references/{reference_id}",
    response_model=CharacterReferenceResponse,
)
def update_reference(
    project_id: UUID,
    character_id: UUID,
    look_id: UUID,
    reference_id: UUID,
    payload: CharacterReferenceUpdateRequest,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterReferenceResponse:
    return service.update_reference(project_id, character_id, look_id, reference_id, payload)


@router.post(
    "/{character_id}/looks/{look_id}/references/{reference_id}/set-primary",
    response_model=CharacterReferenceResponse,
)
def set_primary_reference(
    project_id: UUID,
    character_id: UUID,
    look_id: UUID,
    reference_id: UUID,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> CharacterReferenceResponse:
    return service.set_primary_reference(project_id, character_id, look_id, reference_id)


@router.delete(
    "/{character_id}/looks/{look_id}/references/{reference_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_reference(
    project_id: UUID,
    character_id: UUID,
    look_id: UUID,
    reference_id: UUID,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> Response:
    service.delete_reference(project_id, character_id, look_id, reference_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@media_router.get("/{media_asset_id}/thumbnail")
def get_thumbnail(
    media_asset_id: UUID,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> FileResponse:
    media_asset, relative_path = service.resolve_media_file(media_asset_id, "thumbnail")
    if relative_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    path = MediaStorageService().resolve_relative_path(relative_path)
    media_type = (
        THUMBNAIL_MIME_TYPES.get(path.suffix.lower())
        or mimetypes.guess_type(path.name)[0]
        or "application/octet-stream"
    )
    return FileResponse(path, media_type=media_type, filename=path.name)


@media_router.get("/{media_asset_id}/content")
def get_content(
    media_asset_id: UUID,
    service: Annotated[CharacterService, Depends(get_character_service)],
) -> FileResponse:
    media_asset, relative_path = service.resolve_media_file(media_asset_id, "content")
    if relative_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    path = MediaStorageService().resolve_relative_path(relative_path)
    return FileResponse(
        path,
        media_type=media_asset.mime_type,
        filename=media_asset.original_filename,
    )
