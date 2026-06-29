from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.api.schemas.vision_analysis import (
    AnalysisConfirmRequest,
    AnalysisConfirmResponse,
    AnalysisRejectResponse,
    LatestVisionAnalysisTaskResponse,
    VisionAnalysisTaskResponse,
)
from app.infrastructure.database import get_db_session
from app.repository.vision_analysis_repository import VisionAnalysisRepository
from app.service.vision_analysis_service import VisionAnalysisService
from app.service.vision_analysis_task_runner import VisionAnalysisTaskRunner

router = APIRouter(tags=["vision-analysis"])


def get_vision_analysis_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> VisionAnalysisService:
    return VisionAnalysisService(VisionAnalysisRepository(session))


@router.get(
    "/projects/{project_id}/vision-analysis/tasks/{task_id}",
    response_model=VisionAnalysisTaskResponse,
)
def get_analysis_task(
    project_id: UUID,
    task_id: UUID,
    service: Annotated[VisionAnalysisService, Depends(get_vision_analysis_service)],
) -> VisionAnalysisTaskResponse:
    return service.get_task(project_id, task_id)


@router.post(
    "/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/analysis/tasks",
    response_model=VisionAnalysisTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_character_reference_analysis(
    project_id: UUID,
    character_id: UUID,
    look_id: UUID,
    reference_id: UUID,
    background_tasks: BackgroundTasks,
    service: Annotated[VisionAnalysisService, Depends(get_vision_analysis_service)],
) -> VisionAnalysisTaskResponse:
    task = service.create_character_task(project_id, character_id, look_id, reference_id)
    background_tasks.add_task(VisionAnalysisTaskRunner().run_task, task.id)
    return task


@router.get(
    "/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/analysis/latest-task",
    response_model=LatestVisionAnalysisTaskResponse,
)
def get_latest_character_reference_analysis_task(
    project_id: UUID,
    character_id: UUID,
    look_id: UUID,
    reference_id: UUID,
    service: Annotated[VisionAnalysisService, Depends(get_vision_analysis_service)],
) -> LatestVisionAnalysisTaskResponse:
    return service.get_latest_character_task(project_id, character_id, look_id, reference_id)


@router.post(
    "/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/analysis/confirm",
    response_model=AnalysisConfirmResponse,
)
def confirm_character_reference_analysis(
    project_id: UUID,
    character_id: UUID,
    look_id: UUID,
    reference_id: UUID,
    payload: AnalysisConfirmRequest,
    service: Annotated[VisionAnalysisService, Depends(get_vision_analysis_service)],
) -> AnalysisConfirmResponse:
    review_status = service.confirm_character_suggestions(
        project_id,
        character_id,
        look_id,
        reference_id,
        payload,
    )
    return AnalysisConfirmResponse(suggestion_review_status=review_status.value)


@router.post(
    "/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/analysis/reject",
    response_model=AnalysisRejectResponse,
)
def reject_character_reference_analysis(
    project_id: UUID,
    character_id: UUID,
    look_id: UUID,
    reference_id: UUID,
    service: Annotated[VisionAnalysisService, Depends(get_vision_analysis_service)],
) -> AnalysisRejectResponse:
    review_status = service.reject_character_suggestions(
        project_id,
        character_id,
        look_id,
        reference_id,
    )
    return AnalysisRejectResponse(suggestion_review_status=review_status.value)


@router.post(
    "/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/analysis/tasks",
    response_model=VisionAnalysisTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_scene_reference_analysis(
    project_id: UUID,
    scene_id: UUID,
    state_id: UUID,
    reference_id: UUID,
    background_tasks: BackgroundTasks,
    service: Annotated[VisionAnalysisService, Depends(get_vision_analysis_service)],
) -> VisionAnalysisTaskResponse:
    task = service.create_scene_task(project_id, scene_id, state_id, reference_id)
    background_tasks.add_task(VisionAnalysisTaskRunner().run_task, task.id)
    return task


@router.get(
    "/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/analysis/latest-task",
    response_model=LatestVisionAnalysisTaskResponse,
)
def get_latest_scene_reference_analysis_task(
    project_id: UUID,
    scene_id: UUID,
    state_id: UUID,
    reference_id: UUID,
    service: Annotated[VisionAnalysisService, Depends(get_vision_analysis_service)],
) -> LatestVisionAnalysisTaskResponse:
    return service.get_latest_scene_task(project_id, scene_id, state_id, reference_id)


@router.post(
    "/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/analysis/confirm",
    response_model=AnalysisConfirmResponse,
)
def confirm_scene_reference_analysis(
    project_id: UUID,
    scene_id: UUID,
    state_id: UUID,
    reference_id: UUID,
    payload: AnalysisConfirmRequest,
    service: Annotated[VisionAnalysisService, Depends(get_vision_analysis_service)],
) -> AnalysisConfirmResponse:
    review_status = service.confirm_scene_suggestions(
        project_id,
        scene_id,
        state_id,
        reference_id,
        payload,
    )
    return AnalysisConfirmResponse(suggestion_review_status=review_status.value)


@router.post(
    "/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/analysis/reject",
    response_model=AnalysisRejectResponse,
)
def reject_scene_reference_analysis(
    project_id: UUID,
    scene_id: UUID,
    state_id: UUID,
    reference_id: UUID,
    service: Annotated[VisionAnalysisService, Depends(get_vision_analysis_service)],
) -> AnalysisRejectResponse:
    review_status = service.reject_scene_suggestions(project_id, scene_id, state_id, reference_id)
    return AnalysisRejectResponse(suggestion_review_status=review_status.value)
