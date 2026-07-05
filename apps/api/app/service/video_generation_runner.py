import asyncio
import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.orm.session import sessionmaker as SessionMaker

from app.api.schemas.video_generation import VideoRunSnapshot
from app.core.config import Settings, get_settings
from app.domain.media_asset import MediaType
from app.domain.video_generation import (
    VIDEO_GENERATION_ERROR_MESSAGES,
    VideoGenerationErrorCode,
    VideoGenerationRunStatus,
    VideoInputRole,
)
from app.infrastructure.database import get_session_factory
from app.infrastructure.generation.base import (
    GenerationProviderRuntimeError,
    ProviderOutputFile,
    VideoProviderRequest,
)
from app.infrastructure.generation.factory import create_video_generation_provider
from app.infrastructure.models.video_generation import (
    VideoGenerationOutputRecord,
    VideoGenerationRunRecord,
)
from app.repository.video_generation_repository import VideoGenerationRepository
from app.service.media_storage_service import MediaStorageService
from app.service.video_generation_service import (
    VideoGenerationService,
    media_record_from_stored_video,
)

logger = logging.getLogger(__name__)


class VideoGenerationRunner:
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
            provider = create_video_generation_provider(self.settings)
            uploaded_inputs = await self._upload_inputs(provider, run)
            workflow_payload = self._build_workflow_payload(run.id, uploaded_inputs)
            async with self._semaphore:
                submission = await provider.submit(
                    VideoProviderRequest(
                        workflow=workflow_payload,
                        client_id=f"local-drama-studio-video-{run.id}",
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
            self._mark_failed(run_id, _video_code(exc.code), exc.message)
        except Exception:
            logger.exception("Video generation run failed unexpectedly.", extra={"run_id": run_id})
            self._mark_failed(
                run_id,
                VideoGenerationErrorCode.COMFYUI_EXECUTION_FAILED,
                VIDEO_GENERATION_ERROR_MESSAGES[
                    VideoGenerationErrorCode.COMFYUI_EXECUTION_FAILED.value
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
            self._mark_failed(run.id, _video_code(exc.code), exc.message)

    async def _poll_provider_job(self, run_id: str, provider_job_id: str) -> None:
        provider = create_video_generation_provider(self.settings)
        deadline = asyncio.get_running_loop().time() + self.settings.comfyui_job_timeout_seconds
        while True:
            status = await provider.get_status(provider_job_id)
            if status.status == VideoGenerationRunStatus.COMPLETED.value:
                workflow = self._load_workflow_manifest(run_id)
                outputs = await provider.fetch_video_outputs(
                    provider_job_id,
                    output_file_keys=workflow.manifest.output_file_keys,
                    allowed_extensions=workflow.manifest.allowed_output_extensions,
                )
                self._save_outputs(run_id, outputs)
                self._mark_completed(run_id)
                return
            if status.status == VideoGenerationRunStatus.FAILED.value:
                self._mark_failed(
                    run_id,
                    _video_code(status.error_code)
                    if status.error_code
                    else VideoGenerationErrorCode.COMFYUI_EXECUTION_FAILED,
                    status.error_message
                    or VIDEO_GENERATION_ERROR_MESSAGES[
                        VideoGenerationErrorCode.COMFYUI_EXECUTION_FAILED.value
                    ],
                )
                return
            if status.status == VideoGenerationRunStatus.RUNNING.value:
                self._mark_running(run_id)
            elif status.status == VideoGenerationRunStatus.QUEUED.value:
                self._touch_queued(run_id)
            if asyncio.get_running_loop().time() >= deadline:
                self._mark_failed(
                    run_id,
                    VideoGenerationErrorCode.COMFYUI_TIMEOUT,
                    VIDEO_GENERATION_ERROR_MESSAGES[VideoGenerationErrorCode.COMFYUI_TIMEOUT.value],
                )
                return
            await asyncio.sleep(max(1, self.settings.comfyui_poll_interval_seconds))

    def _build_workflow_payload(
        self,
        run_id: str,
        uploaded_inputs: dict[VideoInputRole, object],
    ) -> dict[str, object]:
        with self.session_factory() as session:
            repository = VideoGenerationRepository(session)
            run = repository.get_run_by_id(run_id)
            if run is None:
                raise GenerationProviderRuntimeError(
                    VideoGenerationErrorCode.VIDEO_RUN_NOT_FOUND,
                    "Video generation run was not found.",
                )
            return VideoGenerationService(
                repository,
                settings=self.settings,
            ).build_provider_workflow(run, uploaded_inputs)

    def _load_workflow_manifest(self, run_id: str):
        with self.session_factory() as session:
            repository = VideoGenerationRepository(session)
            run = repository.get_run_by_id(run_id)
            if run is None:
                raise GenerationProviderRuntimeError(
                    VideoGenerationErrorCode.VIDEO_RUN_NOT_FOUND,
                    "Video generation run was not found.",
                )
            service = VideoGenerationService(repository, settings=self.settings)
            return service.workflow_registry.get_workflow(run.workflow_id)

    async def _upload_inputs(
        self,
        provider,
        run: VideoGenerationRunRecord,
    ) -> dict[VideoInputRole, object]:
        snapshot = VideoRunSnapshot.model_validate_json(run.submitted_payload_snapshot)
        workflow = self._load_workflow_manifest(run.id)
        uploaded: dict[VideoInputRole, object] = {}
        inputs = _snapshot_inputs(snapshot)
        for role in workflow.manifest.required_input_roles:
            media_asset_id = inputs.get(role)
            if not media_asset_id:
                raise GenerationProviderRuntimeError(
                    VideoGenerationErrorCode.VIDEO_INPUT_IMAGE_UNAVAILABLE,
                    "Input image is unavailable.",
                )
            content, mime_type, extension = self._read_input_image(run, role, media_asset_id)
            uploaded[role] = await provider.upload_input_image(
                filename=self._safe_input_filename(run, role, extension),
                content=content,
                mime_type=mime_type,
            )
        return uploaded

    def _read_input_image(
        self,
        run: VideoGenerationRunRecord,
        role: VideoInputRole,
        media_asset_id: str,
    ) -> tuple[bytes, str | None, str]:
        with self.session_factory() as session:
            media_asset = VideoGenerationRepository(session).get_media_asset(
                run.project_id,
                media_asset_id,
            )
            if media_asset is None or media_asset.media_type != MediaType.IMAGE.value:
                raise GenerationProviderRuntimeError(
                    VideoGenerationErrorCode.VIDEO_INPUT_IMAGE_UNAVAILABLE,
                    f"{role.value} image is unavailable.",
                )
            try:
                path = self.storage_service.resolve_relative_path(
                    media_asset.relative_path,
                    must_exist=True,
                )
                content = path.read_bytes()
            except Exception as exc:
                raise GenerationProviderRuntimeError(
                    VideoGenerationErrorCode.REFERENCE_UPLOAD_FAILED,
                    f"{role.value} image could not be prepared.",
                ) from exc
            return content, media_asset.mime_type, media_asset.extension

    def _safe_input_filename(
        self,
        run: VideoGenerationRunRecord,
        role: VideoInputRole,
        extension: str | None,
    ) -> str:
        suffix = f".{extension.lower().lstrip('.')}" if extension else ".png"
        return f"lds_video_{run.id}_{role.value}{suffix}"

    def _save_outputs(self, run_id: str, outputs: list[ProviderOutputFile]) -> None:
        if not outputs:
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.OUTPUT_MISSING,
                "ComfyUI output is missing.",
            )
        saved_or_existing = 0
        with self.session_factory() as session:
            repository = VideoGenerationRepository(session)
            run = repository.get_run_by_id(run_id)
            if run is None:
                raise GenerationProviderRuntimeError(
                    VideoGenerationErrorCode.VIDEO_RUN_NOT_FOUND,
                    "Video generation run was not found.",
                )
            snapshot = VideoRunSnapshot.model_validate_json(run.submitted_payload_snapshot)
            for output_index, output in enumerate(outputs, start=1):
                if repository.output_exists(
                    run.id,
                    output.filename,
                    output.subfolder,
                    output.output_type,
                    output_index,
                ):
                    saved_or_existing += 1
                    continue
                stored = self.storage_service.store_generated_video(
                    run.project_id,
                    output.filename,
                    output.content,
                    output.mime_type,
                )
                now = utc_now()
                media_asset = media_record_from_stored_video(
                    run.project_id,
                    stored,
                    now,
                    width=snapshot.width,
                    height=snapshot.height,
                )
                output_record = VideoGenerationOutputRecord(
                    id=str(uuid4()),
                    project_id=run.project_id,
                    run_id=run.id,
                    media_asset_id=media_asset.id,
                    output_index=output_index,
                    provider_filename=output.filename,
                    provider_subfolder=output.subfolder,
                    provider_type=output.output_type,
                    width=snapshot.width,
                    height=snapshot.height,
                    duration_seconds=snapshot.duration_seconds,
                    fps=snapshot.fps,
                    seed=snapshot.seed,
                    is_selected=False,
                    created_at=now,
                )
                try:
                    repository.create_output_with_media(media_asset, output_record)
                    saved_or_existing += 1
                except SQLAlchemyError as exc:
                    self.storage_service.delete_relative_file_safely(stored.relative_path)
                    raise GenerationProviderRuntimeError(
                        VideoGenerationErrorCode.OUTPUT_SAVE_FAILED,
                        "Generated video could not be saved.",
                    ) from exc
        if saved_or_existing == 0:
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.OUTPUT_MISSING,
                "ComfyUI output is missing.",
            )

    def _load_run(self, run_id: str) -> VideoGenerationRunRecord:
        with self.session_factory() as session:
            run = VideoGenerationRepository(session).get_run_by_id(run_id)
            if run is None:
                raise GenerationProviderRuntimeError(
                    VideoGenerationErrorCode.VIDEO_RUN_NOT_FOUND,
                    "Video generation run was not found.",
                )
            session.expunge(run)
            return run

    def _update_run(self, run_id: str, values: dict[str, object]) -> None:
        with self.session_factory() as session:
            repository = VideoGenerationRepository(session)
            run = repository.get_run_by_id(run_id)
            if run is not None:
                repository.update_run(run, values)

    def _touch_queued(self, run_id: str) -> None:
        self._update_run(
            run_id,
            {"status": VideoGenerationRunStatus.QUEUED.value, "updated_at": utc_now()},
        )

    def _mark_running(self, run_id: str) -> None:
        with self.session_factory() as session:
            repository = VideoGenerationRepository(session)
            run = repository.get_run_by_id(run_id)
            if run is None:
                return
            now = utc_now()
            values: dict[str, object] = {
                "status": VideoGenerationRunStatus.RUNNING.value,
                "updated_at": now,
            }
            if run.started_at is None:
                values["started_at"] = now
            repository.update_run(run, values)

    def _mark_completed(self, run_id: str) -> None:
        now = utc_now()
        self._update_run(
            run_id,
            {
                "status": VideoGenerationRunStatus.COMPLETED.value,
                "error_code": None,
                "error_message_safe": None,
                "completed_at": now,
                "updated_at": now,
            },
        )

    def _mark_failed(
        self,
        run_id: str,
        code: VideoGenerationErrorCode,
        message: str,
    ) -> None:
        now = utc_now()
        self._update_run(
            run_id,
            {
                "status": VideoGenerationRunStatus.FAILED.value,
                "error_code": code.value,
                "error_message_safe": VIDEO_GENERATION_ERROR_MESSAGES.get(code.value, message),
                "completed_at": now,
                "updated_at": now,
            },
        )

    def _mark_interrupted(self, run_id: str) -> None:
        now = utc_now()
        self._update_run(
            run_id,
            {
                "status": VideoGenerationRunStatus.INTERRUPTED.value,
                "error_code": VideoGenerationErrorCode.VIDEO_GENERATION_INTERRUPTED.value,
                "error_message_safe": VIDEO_GENERATION_ERROR_MESSAGES[
                    VideoGenerationErrorCode.VIDEO_GENERATION_INTERRUPTED.value
                ],
                "completed_at": now,
                "updated_at": now,
            },
        )


async def recover_active_video_runs() -> None:
    session_factory = get_session_factory()
    with session_factory() as session:
        try:
            runs = VideoGenerationRepository(session).list_active_runs()
        except OperationalError:
            session.rollback()
            return
        run_ids = [run.id for run in runs]
    runner = VideoGenerationRunner(session_factory=session_factory)
    for run_id in run_ids:
        try:
            await runner.recover_run(run_id)
        except Exception:
            logger.warning("Failed to recover video generation run.", extra={"run_id": run_id})


def _video_code(value) -> VideoGenerationErrorCode:
    try:
        return VideoGenerationErrorCode(str(value))
    except ValueError:
        return VideoGenerationErrorCode.COMFYUI_EXECUTION_FAILED


def _snapshot_inputs(snapshot: VideoRunSnapshot) -> dict[VideoInputRole, str]:
    if snapshot.inputs:
        return {item.role: item.media_asset_id for item in snapshot.inputs}
    if snapshot.input_media_asset_id:
        return {VideoInputRole.START_FRAME: snapshot.input_media_asset_id}
    return {}


def utc_now() -> datetime:
    return datetime.now(UTC)
