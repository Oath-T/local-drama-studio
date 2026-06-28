from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.schemas.scene import (
    SceneCreateRequest,
    SceneListResponse,
    SceneReferenceListResponse,
    SceneReferenceResponse,
    SceneReferenceUpdateRequest,
    SceneResponse,
    SceneStateCreateRequest,
    SceneStateListResponse,
    SceneStateResponse,
    SceneStateUpdateRequest,
    SceneUpdateRequest,
)
from app.domain.scene import CameraPosition, CompositionType, ShotScale, ViewDirection
from app.infrastructure.database import get_db_session
from app.repository.scene_repository import SceneRepository
from app.service.scene_service import SceneService

router = APIRouter(prefix="/projects/{project_id}/scenes", tags=["scenes"])


def get_scene_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> SceneService:
    return SceneService(SceneRepository(session))


@router.get("", response_model=SceneListResponse)
def list_scenes(
    project_id: UUID,
    service: Annotated[SceneService, Depends(get_scene_service)],
) -> SceneListResponse:
    return service.list_scenes(project_id)


@router.post("", response_model=SceneResponse, status_code=status.HTTP_201_CREATED)
def create_scene(
    project_id: UUID,
    payload: SceneCreateRequest,
    service: Annotated[SceneService, Depends(get_scene_service)],
) -> SceneResponse:
    return service.create_scene(project_id, payload)


@router.get("/{scene_id}", response_model=SceneResponse)
def get_scene(
    project_id: UUID,
    scene_id: UUID,
    service: Annotated[SceneService, Depends(get_scene_service)],
) -> SceneResponse:
    return service.get_scene(project_id, scene_id)


@router.patch("/{scene_id}", response_model=SceneResponse)
def update_scene(
    project_id: UUID,
    scene_id: UUID,
    payload: SceneUpdateRequest,
    service: Annotated[SceneService, Depends(get_scene_service)],
) -> SceneResponse:
    return service.update_scene(project_id, scene_id, payload)


@router.delete("/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scene(
    project_id: UUID,
    scene_id: UUID,
    service: Annotated[SceneService, Depends(get_scene_service)],
) -> Response:
    service.delete_scene(project_id, scene_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{scene_id}/states", response_model=SceneStateListResponse)
def list_states(
    project_id: UUID,
    scene_id: UUID,
    service: Annotated[SceneService, Depends(get_scene_service)],
) -> SceneStateListResponse:
    return service.list_states(project_id, scene_id)


@router.post(
    "/{scene_id}/states",
    response_model=SceneStateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_state(
    project_id: UUID,
    scene_id: UUID,
    payload: SceneStateCreateRequest,
    service: Annotated[SceneService, Depends(get_scene_service)],
) -> SceneStateResponse:
    return service.create_state(project_id, scene_id, payload)


@router.get("/{scene_id}/states/{state_id}", response_model=SceneStateResponse)
def get_state(
    project_id: UUID,
    scene_id: UUID,
    state_id: UUID,
    service: Annotated[SceneService, Depends(get_scene_service)],
) -> SceneStateResponse:
    return service.get_state(project_id, scene_id, state_id)


@router.patch("/{scene_id}/states/{state_id}", response_model=SceneStateResponse)
def update_state(
    project_id: UUID,
    scene_id: UUID,
    state_id: UUID,
    payload: SceneStateUpdateRequest,
    service: Annotated[SceneService, Depends(get_scene_service)],
) -> SceneStateResponse:
    return service.update_state(project_id, scene_id, state_id, payload)


@router.post("/{scene_id}/states/{state_id}/set-default", response_model=SceneStateResponse)
def set_default_state(
    project_id: UUID,
    scene_id: UUID,
    state_id: UUID,
    service: Annotated[SceneService, Depends(get_scene_service)],
) -> SceneStateResponse:
    return service.set_default_state(project_id, scene_id, state_id)


@router.delete("/{scene_id}/states/{state_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_state(
    project_id: UUID,
    scene_id: UUID,
    state_id: UUID,
    service: Annotated[SceneService, Depends(get_scene_service)],
) -> Response:
    service.delete_state(project_id, scene_id, state_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{scene_id}/states/{state_id}/references",
    response_model=SceneReferenceListResponse,
)
def list_references(
    project_id: UUID,
    scene_id: UUID,
    state_id: UUID,
    service: Annotated[SceneService, Depends(get_scene_service)],
) -> SceneReferenceListResponse:
    return service.list_references(project_id, scene_id, state_id)


@router.post(
    "/{scene_id}/states/{state_id}/references",
    response_model=SceneReferenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_reference(
    project_id: UUID,
    scene_id: UUID,
    state_id: UUID,
    service: Annotated[SceneService, Depends(get_scene_service)],
    file: Annotated[UploadFile, File()],
    shot_scale: Annotated[ShotScale, Form()] = ShotScale.UNKNOWN,
    camera_position: Annotated[CameraPosition, Form()] = CameraPosition.UNKNOWN,
    custom_camera_position: Annotated[str | None, Form()] = None,
    view_direction: Annotated[ViewDirection, Form()] = ViewDirection.UNKNOWN,
    custom_view_direction: Annotated[str | None, Form()] = None,
    composition_type: Annotated[CompositionType, Form()] = CompositionType.UNKNOWN,
    custom_composition: Annotated[str | None, Form()] = None,
    is_empty_plate: Annotated[bool, Form()] = False,
    is_spatial_anchor: Annotated[bool, Form()] = False,
    tags: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
) -> SceneReferenceResponse:
    payload = SceneReferenceUpdateRequest(
        shot_scale=shot_scale,
        camera_position=camera_position,
        custom_camera_position=custom_camera_position,
        view_direction=view_direction,
        custom_view_direction=custom_view_direction,
        composition_type=composition_type,
        custom_composition=custom_composition,
        is_empty_plate=is_empty_plate,
        is_spatial_anchor=is_spatial_anchor,
        tags=[tag.strip() for tag in tags.split(",")] if tags else [],
        description=description,
        notes=notes,
    )
    return await service.upload_reference(project_id, scene_id, state_id, file, payload)


@router.get(
    "/{scene_id}/states/{state_id}/references/{reference_id}",
    response_model=SceneReferenceResponse,
)
def get_reference(
    project_id: UUID,
    scene_id: UUID,
    state_id: UUID,
    reference_id: UUID,
    service: Annotated[SceneService, Depends(get_scene_service)],
) -> SceneReferenceResponse:
    return service.get_reference(project_id, scene_id, state_id, reference_id)


@router.patch(
    "/{scene_id}/states/{state_id}/references/{reference_id}",
    response_model=SceneReferenceResponse,
)
def update_reference(
    project_id: UUID,
    scene_id: UUID,
    state_id: UUID,
    reference_id: UUID,
    payload: SceneReferenceUpdateRequest,
    service: Annotated[SceneService, Depends(get_scene_service)],
) -> SceneReferenceResponse:
    return service.update_reference(project_id, scene_id, state_id, reference_id, payload)


@router.post(
    "/{scene_id}/states/{state_id}/references/{reference_id}/set-primary",
    response_model=SceneReferenceResponse,
)
def set_primary_reference(
    project_id: UUID,
    scene_id: UUID,
    state_id: UUID,
    reference_id: UUID,
    service: Annotated[SceneService, Depends(get_scene_service)],
) -> SceneReferenceResponse:
    return service.set_primary_reference(project_id, scene_id, state_id, reference_id)


@router.delete(
    "/{scene_id}/states/{state_id}/references/{reference_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_reference(
    project_id: UUID,
    scene_id: UUID,
    state_id: UUID,
    reference_id: UUID,
    service: Annotated[SceneService, Depends(get_scene_service)],
) -> Response:
    service.delete_reference(project_id, scene_id, state_id, reference_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
