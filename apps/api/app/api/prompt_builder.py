from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.prompt_builder import PromptDraftRequest, PromptDraftResponse
from app.infrastructure.database import get_db_session
from app.repository.prompt_context_repository import PromptContextRepository
from app.service.prompt_draft_service import PromptDraftService

router = APIRouter(prefix="/projects/{project_id}/shots", tags=["prompt-builder"])


def get_prompt_draft_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> PromptDraftService:
    return PromptDraftService(PromptContextRepository(session))


@router.post("/{shot_id}/prompt-draft", response_model=PromptDraftResponse)
def build_prompt_draft(
    project_id: UUID,
    shot_id: UUID,
    payload: PromptDraftRequest,
    service: Annotated[PromptDraftService, Depends(get_prompt_draft_service)],
) -> PromptDraftResponse:
    return service.build_prompt_draft(project_id, shot_id, payload)
