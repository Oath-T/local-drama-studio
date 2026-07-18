import asyncio
import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.orm.session import sessionmaker as SessionMaker

from app.core.config import Settings, get_settings
from app.domain.keyframe_generation import (
    KEYFRAME_GENERATION_ERROR_MESSAGES,
    KeyframeGenerationErrorCode,
    KeyframeGenerationRunStatus,
)
from app.infrastructure.database import get_session_factory
from app.infrastructure.generation.base import (
    GenerationProviderRuntimeError,
    KeyframeProviderRequest,
    ProviderOutputImage,
)
from app.infrastructure.generation.factory import create_keyframe_generation_provider
from app.infrastructure.models.keyframe_generation import (
    KeyframeGenerationOutputRecord,
    KeyframeGenerationRunRecord,
)
from app.repository.keyframe_generation_repository import KeyframeGenerationRepository
from app.service.canvas_output_sync_service import CanvasOutputSyncService
from app.service.keyframe_generation_service import (
    KeyframeGenerationService,
    media_record_from_stored_image,
)
from app.service.media_storage_service import MediaStorageService

logger = logging.getLogger(__name__)


class KeyframeGenerationRunner:
    def __init__(
        self,
        session_factory: SessionMaker[Session] | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session_factory = session_factory or get_session_factory()
        self.settings = settings or get_settings()
        self.storage_service = MediaStorageService()
        self._semaphore = asyncio.Semaphore(max(1, self.settings.comfyui_max_concurrency))

    async def run_task(self, run_id: str) -> None:
        try:
            run = self._load_run(run_id)
            if run.provider_job_id:
                await self._poll_provider_job(run.id, run.provider_job_id)
                return
            provider = create_keyframe_generation_provider(self.settings)
            workflow_payload = self._build_workflow_payload(run.id)
            async with self._semaphore:
                submission = await provider.submit(
                    KeyframeProviderRequest(
                        workflow=workflow_payload,
                        client_id=f"local-drama-studio-{run.id}",
                    )
                )
            self._update_run(
                run.id,
                {
                    "provider_job_id": submission.provider_job_id,
                    "updated_at": utc_now(),
                },
            )
            await self._poll_provider_job(run.id, submission.provider_job_id)
        except GenerationProviderRuntimeError as exc:
            self._mark_failed(run_id, exc.code, exc.message)
        except Exception:
            logger.exception(
                "Keyframe generation run failed unexpectedly.",
                extra={"run_id": run_id},
            )
            self._mark_failed(
                run_id,
                KeyframeGenerationErrorCode.COMFYUI_EXECUTION_FAILED,
                KEYFRAME_GENERATION_ERROR_MESSAGES[
                    KeyframeGenerationErrorCode.COMFYUI_EXECUTION_FAILED.value
                ],
            )

    async def recover_run(self, run_id: str) -> None:
        run = self._load_run(run_id)
        if run.provider_job_id is None:
            self._mark_interrupted(run.id)
            return
        try:
            await self._poll_provider_job(run.id, run.provider_job_id)
        except GenerationProviderRuntimeError as exc:
            self._mark_failed(run.id, exc.code, exc.message)

    async def _poll_provider_job(self, run_id: str, provider_job_id: str) -> None:
        provider = create_keyframe_generation_provider(self.settings)
        deadline = asyncio.get_running_loop().time() + self.settings.comfyui_job_timeout_seconds
        while True:
            status = await provider.get_status(provider_job_id)
            if status.status == KeyframeGenerationRunStatus.COMPLETED.value:
                outputs = await provider.fetch_outputs(provider_job_id)
                self._save_outputs(run_id, outputs)
                self._mark_completed(run_id)
                return
            if status.status == KeyframeGenerationRunStatus.FAILED.value:
                self._mark_failed(
                    run_id,
                    status.error_code or KeyframeGenerationErrorCode.COMFYUI_EXECUTION_FAILED,
                    status.error_message
                    or KEYFRAME_GENERATION_ERROR_MESSAGES[
                        KeyframeGenerationErrorCode.COMFYUI_EXECUTION_FAILED.value
                    ],
                )
                return
            if status.status == KeyframeGenerationRunStatus.RUNNING.value:
                self._mark_running(run_id)
            elif status.status == KeyframeGenerationRunStatus.QUEUED.value:
                self._touch_queued(run_id)
            if asyncio.get_running_loop().time() >= deadline:
                self._mark_failed(
                    run_id,
                    KeyframeGenerationErrorCode.COMFYUI_TIMEOUT,
                    KEYFRAME_GENERATION_ERROR_MESSAGES[
                        KeyframeGenerationErrorCode.COMFYUI_TIMEOUT.value
                    ],
                )
                return
            await asyncio.sleep(max(1, self.settings.comfyui_poll_interval_seconds))

    def _build_workflow_payload(self, run_id: str) -> dict[str, object]:
        with self.session_factory() as session:
            repository = KeyframeGenerationRepository(session)
            run = repository.get_run_by_id(run_id)
            if run is None:
                raise GenerationProviderRuntimeError(
                    KeyframeGenerationErrorCode.GENERATION_RUN_NOT_FOUND,
                    "Generation run was not found.",
                )
            return KeyframeGenerationService(
                repository,
                settings=self.settings,
            ).build_provider_workflow(run)

    def _save_outputs(self, run_id: str, outputs: list[ProviderOutputImage]) -> None:
        if not outputs:
            raise GenerationProviderRuntimeError(
                KeyframeGenerationErrorCode.COMFYUI_OUTPUT_MISSING,
                "ComfyUI output is missing.",
            )
        saved_or_existing = 0
        with self.session_factory() as session:
            repository = KeyframeGenerationRepository(session)
            run = repository.get_run_by_id(run_id)
            if run is None:
                raise GenerationProviderRuntimeError(
                    KeyframeGenerationErrorCode.GENERATION_RUN_NOT_FOUND,
                    "Generation run was not found.",
                )
            seed = _snapshot_seed(run)
            for output_index, output in enumerate(outputs, start=1):
                if repository.output_exists(
                    run.id,
                    output.filename,
                    output.subfolder,
                    output_index,
                ):
                    saved_or_existing += 1
                    continue
                stored = self.storage_service.store_generated_keyframe_image(
                    run.project_id,
                    output.filename,
                    output.content,
                    output.mime_type,
                )
                now = utc_now()
                media_asset = media_record_from_stored_image(run.project_id, stored, now)
                output_record = KeyframeGenerationOutputRecord(
                    id=str(uuid4()),
                    project_id=run.project_id,
                    run_id=run.id,
                    media_asset_id=media_asset.id,
                    output_index=output_index,
                    provider_filename=output.filename,
                    provider_subfolder=output.subfolder,
                    width=stored.width,
                    height=stored.height,
                    seed=seed,
                    is_selected=False,
                    created_at=now,
                )
                try:
                    repository.create_output_with_media(media_asset, output_record)
                    saved_or_existing += 1
                except SQLAlchemyError as exc:
                    self.storage_service.delete_relative_file_safely(stored.relative_path)
                    self.storage_service.delete_relative_file_safely(stored.thumbnail_relative_path)
                    raise GenerationProviderRuntimeError(
                        KeyframeGenerationErrorCode.GENERATED_MEDIA_SAVE_FAILED,
                        "Generated media could not be saved.",
                    ) from exc
        if saved_or_existing == 0:
            raise GenerationProviderRuntimeError(
                KeyframeGenerationErrorCode.COMFYUI_OUTPUT_MISSING,
                "ComfyUI output is missing.",
            )
        with self.session_factory() as session:
            CanvasOutputSyncService(session).sync_keyframe_run_outputs(run_id)

    def _load_run(self, run_id: str) -> KeyframeGenerationRunRecord:
        with self.session_factory() as session:
            run = KeyframeGenerationRepository(session).get_run_by_id(run_id)
            if run is None:
                raise GenerationProviderRuntimeError(
                    KeyframeGenerationErrorCode.GENERATION_RUN_NOT_FOUND,
                    "Generation run was not found.",
                )
            session.expunge(run)
            return run

    def _update_run(self, run_id: str, values: dict[str, object]) -> None:
        with self.session_factory() as session:
            repository = KeyframeGenerationRepository(session)
            run = repository.get_run_by_id(run_id)
            if run is not None:
                repository.update_run(run, values)

    def _touch_queued(self, run_id: str) -> None:
        self._update_run(
            run_id,
            {"status": KeyframeGenerationRunStatus.QUEUED.value, "updated_at": utc_now()},
        )

    def _mark_running(self, run_id: str) -> None:
        with self.session_factory() as session:
            repository = KeyframeGenerationRepository(session)
            run = repository.get_run_by_id(run_id)
            if run is None:
                return
            values: dict[str, object] = {
                "status": KeyframeGenerationRunStatus.RUNNING.value,
                "updated_at": utc_now(),
            }
            if run.started_at is None:
                values["started_at"] = utc_now()
            repository.update_run(run, values)

    def _mark_completed(self, run_id: str) -> None:
        now = utc_now()
        self._update_run(
            run_id,
            {
                "status": KeyframeGenerationRunStatus.COMPLETED.value,
                "error_code": None,
                "error_message_safe": None,
                "completed_at": now,
                "updated_at": now,
            },
        )

    def _mark_failed(
        self,
        run_id: str,
        code: KeyframeGenerationErrorCode,
        message: str,
    ) -> None:
        now = utc_now()
        self._update_run(
            run_id,
            {
                "status": KeyframeGenerationRunStatus.FAILED.value,
                "error_code": code.value,
                "error_message_safe": KEYFRAME_GENERATION_ERROR_MESSAGES.get(code.value, message),
                "completed_at": now,
                "updated_at": now,
            },
        )

    def _mark_interrupted(self, run_id: str) -> None:
        now = utc_now()
        self._update_run(
            run_id,
            {
                "status": KeyframeGenerationRunStatus.INTERRUPTED.value,
                "error_code": KeyframeGenerationErrorCode.GENERATION_INTERRUPTED.value,
                "error_message_safe": KEYFRAME_GENERATION_ERROR_MESSAGES[
                    KeyframeGenerationErrorCode.GENERATION_INTERRUPTED.value
                ],
                "completed_at": now,
                "updated_at": now,
            },
        )


async def recover_active_keyframe_runs() -> None:
    session_factory = get_session_factory()
    with session_factory() as session:
        try:
            runs = KeyframeGenerationRepository(session).list_active_runs()
        except OperationalError:
            session.rollback()
            return
        run_ids = [run.id for run in runs]
    runner = KeyframeGenerationRunner(session_factory=session_factory)
    for run_id in run_ids:
        try:
            await runner.recover_run(run_id)
        except Exception:
            logger.warning("Failed to recover keyframe generation run.", extra={"run_id": run_id})


def _snapshot_seed(run: KeyframeGenerationRunRecord) -> int | None:
    from app.api.schemas.keyframe_generation import KeyframeRunSnapshot

    try:
        return KeyframeRunSnapshot.model_validate_json(run.submitted_payload_snapshot).seed
    except Exception:
        return None


def utc_now() -> datetime:
    return datetime.now(UTC)
