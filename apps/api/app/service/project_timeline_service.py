from shutil import which
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.schemas.project_timeline import (
    ProjectTimelineResponse,
    TimelineBlocker,
    TimelineClipResponse,
    TimelineFfmpegStatus,
    TimelineProjectSpec,
)
from app.core.config import get_settings
from app.core.errors import AppError
from app.domain.project_export import ProjectExportErrorCode
from app.repository.project_timeline_repository import ProjectTimelineRepository
from app.service.media_storage_service import MediaStorageService

ERROR_MESSAGES = {
    ProjectExportErrorCode.PROJECT_NOT_FOUND: "项目不存在或已被删除。",
}


class ProjectTimelineService:
    def __init__(
        self,
        session: Session,
        storage_service: MediaStorageService | None = None,
    ) -> None:
        self.repository = ProjectTimelineRepository(session)
        self.storage_service = storage_service or MediaStorageService()
        self.settings = get_settings()

    def get_timeline(self, project_id: UUID) -> ProjectTimelineResponse:
        data = self.repository.load_project_timeline(str(project_id))
        if data is None:
            raise AppError(
                code=ProjectExportErrorCode.PROJECT_NOT_FOUND.value,
                message=ERROR_MESSAGES[ProjectExportErrorCode.PROJECT_NOT_FOUND],
                status_code=404,
            )

        clips: list[TimelineClipResponse] = []
        blockers: list[TimelineBlocker] = []
        estimated_duration = 0.0
        ready_count = 0

        for shot in data.shots:
            selected = data.selected_outputs_by_shot_id.get(shot.id)
            if selected is None or selected.media_asset is None:
                blockers.append(
                    TimelineBlocker(
                        code="SHOT_ADOPTED_VIDEO_MISSING",
                        shot_id=shot.id,
                        message=f"镜头 {shot.order_index:02d} 尚未采用视频输出。",
                    )
                )
                clips.append(
                    TimelineClipResponse(
                        shot_id=shot.id,
                        shot_order=shot.order_index,
                        shot_name=shot.name,
                        status="missing",
                        adopted_video_output_id=None,
                        media_asset_id=None,
                        content_url=None,
                        duration_seconds=None,
                        width=None,
                        height=None,
                        fps=None,
                        warnings=[],
                    )
                )
                continue

            output = selected.output
            media_asset = selected.media_asset
            warnings: list[str] = []
            status = "ready"
            if media_asset.media_type != "video":
                status = "blocked"
                warnings.append("采用的媒体不是视频。")
                blockers.append(
                    TimelineBlocker(
                        code="ADOPTED_MEDIA_NOT_VIDEO",
                        shot_id=shot.id,
                        message=f"镜头 {shot.order_index:02d} 采用的媒体不是视频。",
                    )
                )
            else:
                try:
                    self.storage_service.resolve_relative_path(media_asset.relative_path)
                except AppError:
                    status = "blocked"
                    warnings.append("视频文件不存在或无法读取。")
                    blockers.append(
                        TimelineBlocker(
                            code="ADOPTED_VIDEO_FILE_MISSING",
                            shot_id=shot.id,
                            message=f"镜头 {shot.order_index:02d} 的采用视频文件不存在。",
                        )
                    )

            duration = output.duration_seconds
            if duration is not None:
                estimated_duration += float(duration)
            if status == "ready":
                ready_count += 1

            clips.append(
                TimelineClipResponse(
                    shot_id=shot.id,
                    shot_order=shot.order_index,
                    shot_name=shot.name,
                    status=status,
                    adopted_video_output_id=output.id,
                    media_asset_id=media_asset.id,
                    content_url=f"/api/media/{media_asset.id}/content",
                    duration_seconds=duration,
                    width=output.width or media_asset.width,
                    height=output.height or media_asset.height,
                    fps=output.fps,
                    warnings=warnings,
                )
            )

        ffmpeg_status = self.ffmpeg_status()
        if not ffmpeg_status.available:
            blockers.append(
                TimelineBlocker(
                    code="FFMPEG_UNAVAILABLE",
                    shot_id=None,
                    message="未检测到 FFmpeg，无法开始成片导出。",
                )
            )
        if not ffmpeg_status.ffprobe_available:
            blockers.append(
                TimelineBlocker(
                    code="FFPROBE_UNAVAILABLE",
                    shot_id=None,
                    message="未检测到 FFprobe，无法开始成片导出。",
                )
            )

        return ProjectTimelineResponse(
            project_id=data.project.id,
            exportable=(
                len(data.shots) > 0 and ready_count == len(data.shots) and len(blockers) == 0
            ),
            total_shots=len(data.shots),
            ready_clip_count=ready_count,
            missing_clip_count=max(len(data.shots) - ready_count, 0),
            estimated_duration_seconds=round(estimated_duration, 3),
            project_spec=TimelineProjectSpec(
                aspect_ratio=data.project.aspect_ratio,
                default_fps=data.project.default_fps,
            ),
            ffmpeg=ffmpeg_status,
            clips=clips,
            blockers=blockers,
        )

    def ffmpeg_status(self) -> TimelineFfmpegStatus:
        ffmpeg_available = which(self.settings.ffmpeg_bin) is not None
        ffprobe_available = which(self.settings.ffprobe_bin) is not None
        message = None
        if not ffmpeg_available or not ffprobe_available:
            message = "未检测到 FFmpeg / FFprobe，时间线可查看，但无法开始最终导出。"
        return TimelineFfmpegStatus(
            available=ffmpeg_available,
            ffprobe_available=ffprobe_available,
            message=message,
        )
