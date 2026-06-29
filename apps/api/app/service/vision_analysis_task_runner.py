import asyncio
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.session import sessionmaker as SessionMaker

from app.api.schemas.vision_analysis import (
    CharacterVisionAnalysisSuggestion,
    SceneVisionAnalysisSuggestion,
)
from app.core.config import Settings, get_settings
from app.domain.character import AnalysisStatus as CharacterAnalysisStatus
from app.domain.media_asset import ALLOWED_IMAGE_MIME_TYPES, MediaType
from app.domain.scene import AnalysisStatus as SceneAnalysisStatus
from app.domain.vision_analysis import (
    VISION_ERROR_MESSAGES,
    VisionAnalysisErrorCode,
    VisionAnalysisTargetType,
    VisionAnalysisTaskStatus,
    VisionProviderRuntimeError,
    can_transition,
)
from app.infrastructure.database import get_session_factory
from app.infrastructure.models.character import (
    CharacterLookRecord,
    CharacterReferenceRecord,
    MediaAssetRecord,
)
from app.infrastructure.models.scene import SceneReferenceRecord, SceneStateRecord
from app.infrastructure.models.vision_analysis import VisionAnalysisTaskRecord
from app.infrastructure.vision.base import (
    CharacterAnalysisContext,
    SceneAnalysisContext,
    VisionImageInput,
)
from app.infrastructure.vision.factory import create_vision_analysis_provider
from app.service.media_storage_service import MediaStorageService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadedTaskInput:
    task_id: str
    target_type: VisionAnalysisTargetType
    image: VisionImageInput
    character_context: CharacterAnalysisContext | None = None
    scene_context: SceneAnalysisContext | None = None


class VisionAnalysisTaskRunner:
    def __init__(
        self,
        session_factory: SessionMaker[Session] | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session_factory = session_factory or get_session_factory()
        self.settings = settings or get_settings()
        self.storage_service = MediaStorageService()
        self._semaphore = asyncio.Semaphore(max(1, self.settings.vision_analysis_max_concurrency))

    async def run_task(self, task_id: str) -> None:
        try:
            loaded = self._load_and_mark_running(task_id)
            try:
                provider = create_vision_analysis_provider(self.settings)
            except VisionProviderRuntimeError as exc:
                self._mark_failed(task_id, exc.code, exc.message)
                return

            final_error: VisionProviderRuntimeError | None = None
            max_attempts = max(1, self.settings.vision_analysis_max_retries + 1)
            for attempt in range(1, max_attempts + 1):
                self._set_attempt(task_id, attempt)
                try:
                    async with self._semaphore:
                        if loaded.target_type == VisionAnalysisTargetType.CHARACTER_REFERENCE:
                            if loaded.character_context is None:
                                raise RuntimeError("missing character context")
                            suggestion = await provider.analyze_character_reference(
                                loaded.image,
                                loaded.character_context,
                            )
                        else:
                            if loaded.scene_context is None:
                                raise RuntimeError("missing scene context")
                            suggestion = await provider.analyze_scene_reference(
                                loaded.image,
                                loaded.scene_context,
                            )
                    self._mark_completed(task_id, loaded.target_type, suggestion)
                    return
                except VisionProviderRuntimeError as exc:
                    final_error = exc
                    if not exc.retryable or attempt >= max_attempts:
                        break
                    await asyncio.sleep(0.2)
            if final_error is None:
                final_error = VisionProviderRuntimeError(
                    VisionAnalysisErrorCode.ANALYSIS_FAILED,
                    "Vision analysis failed.",
                    retryable=False,
                )
            self._mark_failed(task_id, final_error.code, final_error.message)
        except VisionProviderRuntimeError as exc:
            self._mark_failed(task_id, exc.code, exc.message)
        except Exception:
            logger.exception(
                "Vision analysis task failed unexpectedly.",
                extra={"task_id": task_id},
            )
            self._mark_failed(
                task_id,
                VisionAnalysisErrorCode.ANALYSIS_FAILED,
                VISION_ERROR_MESSAGES[VisionAnalysisErrorCode.ANALYSIS_FAILED.value],
            )

    def _load_and_mark_running(self, task_id: str) -> LoadedTaskInput:
        with self.session_factory() as session:
            task = session.get(VisionAnalysisTaskRecord, task_id)
            if task is None:
                raise VisionProviderRuntimeError(
                    VisionAnalysisErrorCode.ANALYSIS_TASK_NOT_FOUND,
                    "Task not found.",
                )
            current = VisionAnalysisTaskStatus(task.status)
            if not can_transition(current, VisionAnalysisTaskStatus.RUNNING):
                raise VisionProviderRuntimeError(
                    VisionAnalysisErrorCode.ANALYSIS_FAILED,
                    "Invalid task transition.",
                )
            task.status = VisionAnalysisTaskStatus.RUNNING.value
            task.error_code = None
            task.error_message_safe = None
            task.started_at = utc_now()
            task.updated_at = task.started_at
            session.commit()

        loaded = self._load_task_input(task_id)
        return loaded

    def _load_task_input(self, task_id: str) -> LoadedTaskInput:
        with self.session_factory() as session:
            task = session.get(VisionAnalysisTaskRecord, task_id)
            if task is None:
                raise VisionProviderRuntimeError(
                    VisionAnalysisErrorCode.ANALYSIS_TASK_NOT_FOUND,
                    "Task not found.",
                )
            if task.target_type == VisionAnalysisTargetType.CHARACTER_REFERENCE.value:
                reference = self._load_character_reference(session, task.character_reference_id)
                image = self._read_image(reference.media_asset)
                context = CharacterAnalysisContext(
                    character_name=reference.look.character.name,
                    look_name=reference.look.name,
                    existing_description=reference.description,
                )
                return LoadedTaskInput(
                    task_id=task_id,
                    target_type=VisionAnalysisTargetType.CHARACTER_REFERENCE,
                    image=image,
                    character_context=context,
                )

            reference = self._load_scene_reference(session, task.scene_reference_id)
            image = self._read_image(reference.media_asset)
            context = SceneAnalysisContext(
                scene_name=reference.state.scene.name,
                state_name=reference.state.name,
                existing_description=reference.description,
            )
            return LoadedTaskInput(
                task_id=task_id,
                target_type=VisionAnalysisTargetType.SCENE_REFERENCE,
                image=image,
                scene_context=context,
            )

    def _set_attempt(self, task_id: str, attempt: int) -> None:
        with self.session_factory() as session:
            task = session.get(VisionAnalysisTaskRecord, task_id)
            if task is None:
                return
            task.attempt_count = attempt
            task.updated_at = utc_now()
            session.commit()

    def _mark_completed(
        self,
        task_id: str,
        target_type: VisionAnalysisTargetType,
        suggestion: CharacterVisionAnalysisSuggestion | SceneVisionAnalysisSuggestion,
    ) -> None:
        with self.session_factory() as session:
            task = session.get(VisionAnalysisTaskRecord, task_id)
            if task is None:
                return
            now = utc_now()
            task.status = VisionAnalysisTaskStatus.COMPLETED.value
            task.error_code = None
            task.error_message_safe = None
            task.completed_at = now
            task.updated_at = now
            if target_type == VisionAnalysisTargetType.CHARACTER_REFERENCE:
                reference = session.get(CharacterReferenceRecord, task.character_reference_id)
                if reference is not None:
                    reference.analysis_status = CharacterAnalysisStatus.COMPLETED.value
                    reference.analysis_suggestions = suggestion.model_dump_json()
                    reference.suggestion_review_status = "not_reviewed"
                    reference.updated_at = now
            else:
                reference = session.get(SceneReferenceRecord, task.scene_reference_id)
                if reference is not None:
                    reference.analysis_status = SceneAnalysisStatus.COMPLETED.value
                    reference.analysis_suggestions = suggestion.model_dump_json()
                    reference.suggestion_review_status = "not_reviewed"
                    reference.updated_at = now
            session.commit()

    def _mark_failed(
        self,
        task_id: str,
        code: VisionAnalysisErrorCode,
        message: str,
    ) -> None:
        with self.session_factory() as session:
            task = session.get(VisionAnalysisTaskRecord, task_id)
            if task is None:
                return
            now = utc_now()
            task.status = VisionAnalysisTaskStatus.FAILED.value
            task.error_code = code.value
            task.error_message_safe = VISION_ERROR_MESSAGES.get(code.value, message)
            task.completed_at = now
            task.updated_at = now
            if task.target_type == VisionAnalysisTargetType.CHARACTER_REFERENCE.value:
                reference = session.get(CharacterReferenceRecord, task.character_reference_id)
                if reference is not None:
                    reference.analysis_status = (
                        CharacterAnalysisStatus.COMPLETED.value
                        if reference.analysis_suggestions
                        else CharacterAnalysisStatus.FAILED.value
                    )
                    reference.updated_at = now
            else:
                reference = session.get(SceneReferenceRecord, task.scene_reference_id)
                if reference is not None:
                    reference.analysis_status = (
                        SceneAnalysisStatus.COMPLETED.value
                        if reference.analysis_suggestions
                        else SceneAnalysisStatus.FAILED.value
                    )
                    reference.updated_at = now
            session.commit()

    def _read_image(self, media_asset: MediaAssetRecord) -> VisionImageInput:
        if media_asset.media_type != MediaType.IMAGE.value:
            raise VisionProviderRuntimeError(
                VisionAnalysisErrorCode.MEDIA_READ_FAILED,
                "Media asset is not an image.",
            )
        if media_asset.mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise VisionProviderRuntimeError(
                VisionAnalysisErrorCode.MEDIA_READ_FAILED,
                "Image MIME type is not supported for analysis.",
            )
        max_mb = self.settings.vision_analysis_max_image_mb or self.settings.max_image_upload_mb
        if media_asset.size_bytes > max_mb * 1024 * 1024:
            raise VisionProviderRuntimeError(
                VisionAnalysisErrorCode.MEDIA_READ_FAILED,
                "Image is too large for analysis.",
            )
        try:
            path = self.storage_service.resolve_relative_path(media_asset.relative_path)
            content = path.read_bytes()
        except Exception as exc:
            raise VisionProviderRuntimeError(
                VisionAnalysisErrorCode.MEDIA_READ_FAILED,
                "Image file could not be read.",
            ) from exc
        return VisionImageInput(
            media_asset_id=media_asset.id,
            original_filename=media_asset.original_filename,
            mime_type=media_asset.mime_type,
            content=content,
        )

    @staticmethod
    def _load_character_reference(
        session: Session,
        reference_id: str | None,
    ) -> CharacterReferenceRecord:
        statement = (
            select(CharacterReferenceRecord)
            .where(CharacterReferenceRecord.id == reference_id)
            .options(
                joinedload(CharacterReferenceRecord.media_asset),
                joinedload(CharacterReferenceRecord.look).joinedload(CharacterLookRecord.character),
            )
        )
        reference = session.scalars(statement).first()
        if reference is None or reference.media_asset is None:
            raise VisionProviderRuntimeError(
                VisionAnalysisErrorCode.MEDIA_NOT_FOUND,
                "Reference or media asset not found.",
            )
        return reference

    @staticmethod
    def _load_scene_reference(
        session: Session,
        reference_id: str | None,
    ) -> SceneReferenceRecord:
        statement = (
            select(SceneReferenceRecord)
            .where(SceneReferenceRecord.id == reference_id)
            .options(
                joinedload(SceneReferenceRecord.media_asset),
                joinedload(SceneReferenceRecord.state).joinedload(SceneStateRecord.scene),
            )
        )
        reference = session.scalars(statement).first()
        if reference is None or reference.media_asset is None:
            raise VisionProviderRuntimeError(
                VisionAnalysisErrorCode.MEDIA_NOT_FOUND,
                "Reference or media asset not found.",
            )
        return reference


def mark_interrupted_vision_tasks() -> None:
    session_factory = get_session_factory()
    with session_factory() as session:
        try:
            tasks = list(
                session.scalars(
                    select(VisionAnalysisTaskRecord).where(
                        VisionAnalysisTaskRecord.status.in_(
                            [
                                VisionAnalysisTaskStatus.PENDING.value,
                                VisionAnalysisTaskStatus.RUNNING.value,
                            ]
                        )
                    )
                ).all()
            )
        except OperationalError:
            session.rollback()
            return
        now = utc_now()
        for task in tasks:
            task.status = VisionAnalysisTaskStatus.FAILED.value
            task.error_code = VisionAnalysisErrorCode.ANALYSIS_INTERRUPTED.value
            task.error_message_safe = VISION_ERROR_MESSAGES[
                VisionAnalysisErrorCode.ANALYSIS_INTERRUPTED.value
            ]
            task.completed_at = now
            task.updated_at = now
            if task.target_type == VisionAnalysisTargetType.CHARACTER_REFERENCE.value:
                reference = session.get(CharacterReferenceRecord, task.character_reference_id)
                if reference is not None:
                    reference.analysis_status = (
                        CharacterAnalysisStatus.COMPLETED.value
                        if reference.analysis_suggestions
                        else CharacterAnalysisStatus.FAILED.value
                    )
                    reference.updated_at = now
            else:
                reference = session.get(SceneReferenceRecord, task.scene_reference_id)
                if reference is not None:
                    reference.analysis_status = (
                        SceneAnalysisStatus.COMPLETED.value
                        if reference.analysis_suggestions
                        else SceneAnalysisStatus.FAILED.value
                    )
                    reference.updated_at = now
        if tasks:
            session.commit()


def utc_now():
    from datetime import UTC, datetime

    return datetime.now(UTC)
