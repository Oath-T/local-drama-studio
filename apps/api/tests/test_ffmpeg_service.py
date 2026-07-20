import json
import subprocess
from pathlib import Path

import pytest

from app.service.export.ffmpeg_service import FfmpegService


def test_ffprobe_parses_video_metadata_and_uses_shell_false(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append({"args": args, **kwargs})
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=json.dumps(
                {
                    "streams": [
                        {
                            "codec_type": "video",
                            "width": 640,
                            "height": 360,
                            "r_frame_rate": "30000/1001",
                            "avg_frame_rate": "30000/1001",
                            "nb_frames": "75",
                            "codec_name": "h264",
                            "pix_fmt": "yuv420p",
                        }
                    ],
                    "format": {
                        "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                        "duration": "2.5",
                        "size": "12345",
                    },
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    probe = FfmpegService().probe(tmp_path / "source.mp4")

    assert probe.width == 640
    assert probe.height == 360
    assert probe.fps == 30
    assert probe.duration_seconds == 2.5
    assert probe.codec == "h264"
    assert probe.pixel_format == "yuv420p"
    assert probe.format_name == "mov,mp4,m4a,3gp,3g2,mj2"
    assert probe.size_bytes == 12345
    assert probe.codec_type == "video"
    assert probe.average_frame_rate == "30000/1001"
    assert probe.frame_count == 75
    assert probe.audio_stream_count == 0
    assert calls[0]["shell"] is False
    assert isinstance(calls[0]["args"], list)


def test_normalize_clip_uses_scale_pad_and_shell_false(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append({"args": args, **kwargs})
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    FfmpegService().normalize_clip(
        source_path=tmp_path / "source.mp4",
        output_path=tmp_path / "out" / "clip.mp4",
        width=720,
        height=1280,
        fps=24,
        codec="libx264",
    )

    args = calls[0]["args"]
    assert calls[0]["shell"] is False
    assert "-an" in args
    vf = str(args[args.index("-vf") + 1])
    assert "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280" in vf
    assert "fps=24,format=yuv420p" in vf
    assert "libx264" in args


def test_concat_writes_safe_list_and_raises_on_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append({"args": args, **kwargs})
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="failed")

    monkeypatch.setattr(subprocess, "run", fake_run)
    concat_file = tmp_path / "concat.txt"

    with pytest.raises(RuntimeError):
        FfmpegService().concat(
            [tmp_path / "clip one.mp4", tmp_path / "clip'two.mp4"],
            concat_file,
            tmp_path / "final.mp4",
        )

    assert calls[0]["shell"] is False
    assert "file '" in concat_file.read_text(encoding="utf-8")
    assert "clip one.mp4" in concat_file.read_text(encoding="utf-8")
