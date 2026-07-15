import json
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.api.schemas.character import MediaAssetResponse
from app.api.schemas.project_export import (
    ProjectExportCreateRequest,
    ProjectExportListResponse,
    ProjectExportResponse,
    ProjectExportStartResponse,
)
from app.core.errors import AppError
from app.domain.project_export import (
    ExportSettings,
    ProjectExportErrorCode,
    ProjectExportStatus,
    normalize_export_name,
    utc_now,
    validate_export_settings,
)
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.project_export import ProjectExportRecord
from app.repository.project_export_repository import ProjectExportRepository
from app.service.export.ffmpeg_service import FfmpegService
from app.service.media_storage_service import MediaStorageService
from app.service.project_timeline_service import ProjectTimelineService

ERROR_MESSAGES = {
    ProjectExportErrorCode.PROJECT_NOT_FOUND: "项目不存在或已被删除。",
    ProjectExportErrorCode.EXPORT_NOT_FOUND: "导出任务不存在或已被删除。",
    ProjectExportErrorCode.NAME_REQUIRED: "请输入导出名称。",
    ProjectExportErrorCode.INVALID_DIMENSIONS: "导出宽高必须为 256 到 3840 之间的偶数。",
    ProjectExportErrorCode.INVALID_FPS: "导出帧率必须在 1 到 60 之间。",
    ProjectExportErrorCode.INVALID_CODEC: "当前仅支持 libx264 编码。",
    ProjectExportErrorCode.NO_CLIPS: "没有可导出的已采用视频。",
    ProjectExportErrorCode.TIMELINE_BLOCKED: "时间线仍有阻断项，无法标记可导出。",
    ProjectExportErrorCode.FFMPEG_UNAVAILABLE: "未检测到 FFmpeg，无法开始成片导出。",
    ProjectExportErrorCode.FFPROBE_UNAVAILABLE: "未检测到 FFprobe，无法开始成片导出。",
    ProjectExportErrorCode.MEDIA_FILE_MISSING: "导出源视频文件不存在或无法读取。",
    ProjectExportErrorCode.INVALID_STATUS: "当前导出任务状态不允许执行此操作。",
    ProjectExportErrorCode.RUN_FAILED: "最终导出失败，请检查源视频和 FFmpeg 环境。",
}


class ProjectExportService:
    def __init__(
        self,
        session: Session,
        storage_service: MediaStorageService | None = None,
        ffmpeg_service: FfmpegService | None = None,
    ) -> None:
        self.session = session
        self.repository = ProjectExportRepository(session)
        self.storage_service = storage_service or MediaStorageService()
        self.ffmpeg_service = ffmpeg_service or FfmpegService()

    def list_exports(self, project_id: UUID) -> ProjectExportListResponse:
        if not self.repository.project_exists(str(project_id)):
            raise_export_error(ProjectExportErrorCode.PROJECT_NOT_FOUND, 404)
        items, total = self.repository.list_exports(str(project_id))
        media_assets = self.repository.media_assets_by_ids(
            [item.output_media_asset_id for item in items if item.output_media_asset_id]
        )
        return ProjectExportListResponse(
            items=[
                self._response(item, media_assets.get(item.output_media_asset_id or ""))
                for item in items
            ],
            total=total,
        )

    def create_export(
        self,
        project_id: UUID,
        payload: ProjectExportCreateRequest,
    ) -> ProjectExportResponse:
        settings = validate_export_settings_or_raise(
            payload.target_width,
            payload.target_height,
            payload.target_fps,
            payload.video_codec,
        )
        timeline = ProjectTimelineService(
            self.session,
            self.storage_service,
        ).get_timeline(project_id)
        clips = [
            {
                "shot_id": clip.shot_id,
                "shot_order": clip.shot_order,
                "shot_name": clip.shot_name,
                "media_asset_id": clip.media_asset_id,
                "source_video_output_id": clip.adopted_video_output_id,
                "duration_seconds": clip.duration_seconds,
            }
            for clip in timeline.clips
            if clip.status == "ready" and clip.media_asset_id and clip.adopted_video_output_id
        ]
        snapshot = {
            "schema_version": 1,
            "clips": clips,
            "timeline_blockers": [
                blocker.model_dump()
                for blocker in timeline.blockers
                if blocker.code not in {"FFMPEG_UNAVAILABLE", "FFPROBE_UNAVAILABLE"}
            ],
            "export_settings": {
                "width": settings.width,
                "height": settings.height,
                "fps": settings.fps,
                "codec": settings.codec,
                "pixel_format": settings.pixel_format,
                "output_format": settings.output_format,
            },
        }
        now = utc_now()
        record = ProjectExportRecord(
            id=str(uuid4()),
            project_id=str(project_id),
            name=normalize_export_name_or_raise(payload.name),
            status=ProjectExportStatus.DRAFT.value,
            progress_percent=0,
            current_stage="准备中",
            clip_count=len(clips),
            duration_seconds=round(
                sum(float(clip.get("duration_seconds") or 0) for clip in clips),
                3,
            ),
            target_width=settings.width,
            target_height=settings.height,
            target_fps=settings.fps,
            video_codec=settings.codec,
            output_format=settings.output_format,
            snapshot=json.dumps(snapshot, ensure_ascii=False),
            error_message=None,
            output_media_asset_id=None,
            created_at=now,
            updated_at=now,
            started_at=None,
            completed_at=None,
        )
        return self._response(self.repository.create_export(record), None)

    def get_export(self, project_id: UUID, export_id: UUID) -> ProjectExportResponse:
        record = self._get_record(project_id, export_id)
        media_asset = (
            self.repository.media_assets_by_ids([record.output_media_asset_id]).get(
                record.output_media_asset_id
            )
            if record.output_media_asset_id
            else None
        )
        return self._response(record, media_asset)

    def mark_ready(self, project_id: UUID, export_id: UUID) -> ProjectExportResponse:
        record = self._get_record(project_id, export_id)
        if record.status not in {ProjectExportStatus.DRAFT.value, ProjectExportStatus.FAILED.value}:
            raise_export_error(ProjectExportErrorCode.INVALID_STATUS, 409)
        self._validate_ready(record)
        now = utc_now()
        self.repository.update_export(
            record,
            {
                "status": ProjectExportStatus.READY.value,
                "progress_percent": 0,
                "current_stage": "检查通过，等待开始导出",
                "error_message": None,
                "updated_at": now,
            },
        )
        return self._response(record, None)

    def start(self, project_id: UUID, export_id: UUID) -> ProjectExportStartResponse:
        record = self._get_record(project_id, export_id)
        if record.status != ProjectExportStatus.READY.value:
            raise_export_error(ProjectExportErrorCode.INVALID_STATUS, 409)
        now = utc_now()
        self.repository.update_export(
            record,
            {
                "status": ProjectExportStatus.QUEUED.value,
                "progress_percent": 0,
                "current_stage": "排队中",
                "updated_at": now,
            },
        )
        return ProjectExportStartResponse(
            id=record.id,
            status=record.status,
            progress_percent=record.progress_percent,
            current_stage=record.current_stage,
        )

    def _validate_ready(self, record: ProjectExportRecord) -> None:
        if not self.ffmpeg_service.ffmpeg_available():
            raise_export_error(ProjectExportErrorCode.FFMPEG_UNAVAILABLE, 422)
        if not self.ffmpeg_service.ffprobe_available():
            raise_export_error(ProjectExportErrorCode.FFPROBE_UNAVAILABLE, 422)
        snapshot = json.loads(record.snapshot)
        blockers = snapshot.get("timeline_blockers") or []
        if blockers:
            raise_export_error(ProjectExportErrorCode.TIMELINE_BLOCKED, 422)
        clips = snapshot.get("clips") or []
        if not clips:
            raise_export_error(ProjectExportErrorCode.NO_CLIPS, 422)
        validate_export_settings_or_raise(
            record.target_width,
            record.target_height,
            record.target_fps,
            record.video_codec,
        )
        media_assets = self.repository.media_assets_by_ids(
            [clip["media_asset_id"] for clip in clips if clip.get("media_asset_id")]
        )
        for clip in clips:
            media_asset = media_assets.get(clip.get("media_asset_id"))
            if media_asset is None or media_asset.media_type != "video":
                raise_export_error(ProjectExportErrorCode.MEDIA_FILE_MISSING, 422)
            self.storage_service.resolve_relative_path(media_asset.relative_path)
        output_path = self.storage_service.project_export_path(
            record.project_id,
            record.id,
            "final.mp4",
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_record(self, project_id: UUID, export_id: UUID) -> ProjectExportRecord:
        record = self.repository.get_export(str(project_id), str(export_id))
        if record is None:
            raise_export_error(ProjectExportErrorCode.EXPORT_NOT_FOUND, 404)
        return record

    def _response(
        self,
        record: ProjectExportRecord,
        output_media_asset: MediaAssetRecord | None,
    ) -> ProjectExportResponse:
        media_response = None
        if output_media_asset is not None:
            media_response = MediaAssetResponse(
                id=output_media_asset.id,
                project_id=output_media_asset.project_id,
                media_type=output_media_asset.media_type,
                original_filename=output_media_asset.original_filename,
                mime_type=output_media_asset.mime_type,
                extension=output_media_asset.extension,
                size_bytes=output_media_asset.size_bytes,
                width=output_media_asset.width,
                height=output_media_asset.height,
                sha256=output_media_asset.sha256,
                thumbnail_url=(
                    f"/api/media/{output_media_asset.id}/thumbnail"
                    if output_media_asset.thumbnail_relative_path
                    else None
                ),
                content_url=f"/api/media/{output_media_asset.id}/content",
                created_at=output_media_asset.created_at,
            )
        return ProjectExportResponse(
            id=record.id,
            project_id=record.project_id,
            name=record.name,
            status=record.status,
            progress_percent=record.progress_percent,
            current_stage=record.current_stage,
            clip_count=record.clip_count,
            duration_seconds=record.duration_seconds,
            target_width=record.target_width,
            target_height=record.target_height,
            target_fps=record.target_fps,
            video_codec=record.video_codec,
            output_format=record.output_format,
            error_message=record.error_message,
            output_media_asset_id=record.output_media_asset_id,
            output_media_asset=media_response,
            created_at=record.created_at,
            updated_at=record.updated_at,
            started_at=record.started_at,
            completed_at=record.completed_at,
        )


def raise_export_error(code: ProjectExportErrorCode, status_code: int) -> None:
    raise AppError(
        code=code.value,
        message=ERROR_MESSAGES[code],
        status_code=status_code,
    )


def normalize_export_name_or_raise(value: str | None) -> str:
    try:
        return normalize_export_name(value)
    except ValueError as error:
        code = ProjectExportErrorCode(str(error.args[0]))
        raise_export_error(code, 422)


def validate_export_settings_or_raise(
    width: int,
    height: int,
    fps: int,
    codec: str,
) -> ExportSettings:
    try:
        return validate_export_settings(width, height, fps, codec)
    except ValueError as error:
        code = ProjectExportErrorCode(str(error.args[0]))
        raise_export_error(code, 422)
