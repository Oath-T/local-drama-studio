import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from shutil import which

from app.core.config import get_settings


@dataclass(frozen=True)
class VideoProbe:
    width: int
    height: int
    fps: int
    duration_seconds: float
    codec: str | None
    pixel_format: str | None
    format_name: str | None = None
    size_bytes: int = 0
    codec_type: str | None = None
    average_frame_rate: str | None = None
    frame_count: int = 0
    audio_stream_count: int = 0


class FfmpegService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def ffmpeg_available(self) -> bool:
        return which(self.settings.ffmpeg_bin) is not None

    def ffprobe_available(self) -> bool:
        return which(self.settings.ffprobe_bin) is not None

    def probe(self, source_path: Path) -> VideoProbe:
        result = subprocess.run(
            [
                self.settings.ffprobe_bin,
                "-v",
                "error",
                "-show_entries",
                (
                    "stream=codec_type,width,height,codec_name,pix_fmt,"
                    "r_frame_rate,avg_frame_rate,nb_frames:format=format_name,duration,size"
                ),
                "-of",
                "json",
                str(source_path),
            ],
            capture_output=True,
            text=True,
            timeout=min(self.settings.export_timeout_seconds, 120),
            shell=False,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("FFprobe 无法读取视频文件。")
        payload = json.loads(result.stdout or "{}")
        streams = payload.get("streams") or []
        video_streams = [
            stream
            for stream in streams
            if isinstance(stream, dict) and stream.get("codec_type") == "video"
        ]
        if not video_streams:
            raise RuntimeError("FFprobe 未发现视频流。")
        stream = video_streams[0]
        format_info = payload.get("format") or {}
        duration = float(format_info.get("duration") or 0)
        return VideoProbe(
            width=int(stream.get("width") or 0),
            height=int(stream.get("height") or 0),
            fps=_parse_fps(str(stream.get("r_frame_rate") or "0/1")),
            duration_seconds=duration,
            codec=stream.get("codec_name"),
            pixel_format=stream.get("pix_fmt"),
            format_name=format_info.get("format_name"),
            size_bytes=int(format_info.get("size") or 0),
            codec_type=stream.get("codec_type"),
            average_frame_rate=stream.get("avg_frame_rate"),
            frame_count=int(stream.get("nb_frames") or 0),
            audio_stream_count=sum(
                1
                for item in streams
                if isinstance(item, dict) and item.get("codec_type") == "audio"
            ),
        )

    def normalize_clip(
        self,
        source_path: Path,
        output_path: Path,
        width: int,
        height: int,
        fps: int,
        codec: str,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
            f"fps={fps},format=yuv420p"
        )
        result = subprocess.run(
            [
                self.settings.ffmpeg_bin,
                "-y",
                "-i",
                str(source_path),
                "-an",
                "-vf",
                vf,
                "-c:v",
                codec,
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=self.settings.export_timeout_seconds,
            shell=False,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("FFmpeg 标准化镜头片段失败。")

    def extract_poster(self, source_path: Path, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                self.settings.ffmpeg_bin,
                "-y",
                "-ss",
                "0.2",
                "-i",
                str(source_path),
                "-frames:v",
                "1",
                "-f",
                "image2",
                "-vcodec",
                "png",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=min(self.settings.export_timeout_seconds, 120),
            shell=False,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("FFmpeg 提取视频封面失败。")

    def concat(self, segment_paths: list[Path], concat_file: Path, output_path: Path) -> None:
        concat_file.parent.mkdir(parents=True, exist_ok=True)
        concat_file.write_text(
            "".join(f"file '{_concat_path(path)}'\n" for path in segment_paths),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                self.settings.ffmpeg_bin,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=self.settings.export_timeout_seconds,
            shell=False,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("FFmpeg 拼接最终视频失败。")


def _parse_fps(value: str) -> int:
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        denominator_number = float(denominator or 1)
        if denominator_number == 0:
            return 0
        return round(float(numerator or 0) / denominator_number)
    return round(float(value or 0))


def _concat_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "'\\''")
