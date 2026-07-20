import json
import logging
import shutil
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy.orm.session import sessionmaker as SessionMaker

from app.domain.project_export import ProjectExportStatus, utc_now
from app.infrastructure.database import get_session_factory
from app.infrastructure.models.character import MediaAssetRecord
from app.repository.project_export_repository import ProjectExportRepository
from app.service.export.ffmpeg_service import FfmpegService, VideoProbe
from app.service.media_storage_service import MediaStorageService

logger = logging.getLogger(__name__)


class ProjectExportRunner:
    def __init__(
        self,
        session_factory: SessionMaker[Session] | None = None,
        storage_service: MediaStorageService | None = None,
        ffmpeg_service: FfmpegService | None = None,
    ) -> None:
        self.session_factory = session_factory or get_session_factory()
        self.storage_service = storage_service or MediaStorageService()
        self.ffmpeg_service = ffmpeg_service or FfmpegService()

    def run_export(self, export_id: str) -> None:
        with self.session_factory() as session:
            repository = ProjectExportRepository(session)
            record = repository.get_export_by_id(export_id)
            if record is None:
                return
            try:
                now = utc_now()
                repository.update_export(
                    record,
                    {
                        "status": ProjectExportStatus.RUNNING.value,
                        "progress_percent": 5,
                        "current_stage": "检查视频",
                        "started_at": now,
                        "updated_at": now,
                    },
                )
                snapshot = json.loads(record.snapshot)
                clips = snapshot.get("clips") or []
                settings = snapshot.get("export_settings") or {}
                media_assets = repository.media_assets_by_ids(
                    [clip["media_asset_id"] for clip in clips if clip.get("media_asset_id")]
                )
                segment_dir = self.storage_service.project_export_segments_dir(
                    record.project_id,
                    record.id,
                )
                final_path = self.storage_service.project_export_path(
                    record.project_id,
                    record.id,
                    "final.mp4",
                )
                segment_dir.mkdir(parents=True, exist_ok=True)
                final_path.parent.mkdir(parents=True, exist_ok=True)

                segment_paths = []
                total = max(len(clips), 1)
                for index, clip in enumerate(clips, start=1):
                    media_asset = media_assets.get(clip.get("media_asset_id"))
                    if media_asset is None:
                        raise RuntimeError("导出源视频文件不存在或无法读取。")
                    source_path = self.storage_service.resolve_relative_path(
                        media_asset.relative_path
                    )
                    source_probe = self.ffmpeg_service.probe(source_path)
                    self._validate_source_probe(source_probe)
                    segment_path = segment_dir / f"{index:04d}.mp4"
                    repository.update_export(
                        record,
                        {
                            "progress_percent": 10 + int((index - 1) / total * 70),
                            "current_stage": f"标准化镜头 {index}/{len(clips)}",
                            "updated_at": utc_now(),
                        },
                    )
                    self.ffmpeg_service.normalize_clip(
                        source_path=source_path,
                        output_path=segment_path,
                        width=int(settings["width"]),
                        height=int(settings["height"]),
                        fps=int(settings["fps"]),
                        codec=str(settings["codec"]),
                    )
                    segment_paths.append(segment_path)

                repository.update_export(
                    record,
                    {
                        "progress_percent": 85,
                        "current_stage": "拼接中",
                        "updated_at": utc_now(),
                    },
                )
                concat_file = segment_dir / "concat.txt"
                self.ffmpeg_service.concat(segment_paths, concat_file, final_path)
                final_probe = self.ffmpeg_service.probe(final_path)
                self._validate_final_probe(
                    final_probe,
                    width=int(settings["width"]),
                    height=int(settings["height"]),
                    fps=int(settings["fps"]),
                )

                repository.update_export(
                    record,
                    {
                        "progress_percent": 95,
                        "current_stage": "写入媒体库",
                        "updated_at": utc_now(),
                    },
                )
                stored = self.storage_service.register_project_export_video(
                    record.project_id,
                    record.id,
                    final_path,
                )
                media_asset = MediaAssetRecord(
                    id=str(uuid4()),
                    project_id=record.project_id,
                    media_type="video",
                    original_filename=stored.original_filename,
                    stored_filename=stored.stored_filename,
                    relative_path=stored.relative_path,
                    thumbnail_relative_path=None,
                    mime_type=stored.mime_type,
                    extension=stored.extension,
                    size_bytes=stored.size_bytes,
                    width=final_probe.width,
                    height=final_probe.height,
                    sha256=stored.sha256,
                    created_at=utc_now(),
                )
                completed_at = utc_now()
                repository.complete_with_media(
                    record,
                    media_asset,
                    {
                        "status": ProjectExportStatus.COMPLETED.value,
                        "progress_percent": 100,
                        "current_stage": "已完成",
                        "error_message": None,
                        "output_media_asset_id": media_asset.id,
                        "completed_at": completed_at,
                        "updated_at": completed_at,
                    },
                )
                shutil.rmtree(segment_dir, ignore_errors=True)
            except Exception:
                logger.exception("Project export failed.")
                failed_at = utc_now()
                repository.update_export(
                    record,
                    {
                        "status": ProjectExportStatus.FAILED.value,
                        "progress_percent": record.progress_percent,
                        "current_stage": "失败",
                        "error_message": "最终导出失败，请检查源视频和 FFmpeg 环境。",
                        "completed_at": failed_at,
                        "updated_at": failed_at,
                    },
                )

    def _validate_source_probe(self, probe: VideoProbe) -> None:
        if probe.codec_type not in {None, "video"}:
            raise ValueError("invalid video stream")
        if probe.width <= 0 or probe.height <= 0:
            raise ValueError("invalid video dimensions")
        if probe.fps <= 0:
            raise ValueError("invalid video fps")
        if probe.duration_seconds <= 0:
            raise ValueError("invalid video duration")

    def _validate_final_probe(self, probe: VideoProbe, width: int, height: int, fps: int) -> None:
        self._validate_source_probe(probe)
        if probe.width != width or probe.height != height:
            raise ValueError("final video dimensions do not match export settings")
        if probe.fps != fps:
            raise ValueError("final video fps does not match export settings")
        if probe.codec != "h264":
            raise ValueError("final video is not H.264")
        if probe.pixel_format != "yuv420p":
            raise ValueError("final video pixel format is not yuv420p")
        if probe.audio_stream_count != 0:
            raise ValueError("final video must not contain audio in v1")


def run_project_export(export_id: str) -> None:
    ProjectExportRunner().run_export(export_id)
