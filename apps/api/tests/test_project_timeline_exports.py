import json
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.core.config import get_settings
from app.domain.project_export import ProjectExportStatus
from app.infrastructure.database import get_session_factory
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.project_export import ProjectExportRecord
from app.infrastructure.models.video_generation import (
    VideoGenerationOutputRecord,
    VideoGenerationRunRecord,
    VideoGenerationTaskRecord,
)
from app.service.export.export_runner import ProjectExportRunner
from app.service.export.ffmpeg_service import VideoProbe
from app.service.project_export_service import ProjectExportService


@pytest.fixture(autouse=True)
def fake_timeline_ffmpeg(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "app.service.project_timeline_service.FfmpegService",
        lambda: _AvailableFfmpeg(tmp_path),
    )
    monkeypatch.setattr(
        "app.service.project_export_service.FfmpegService",
        lambda: _AvailableFfmpeg(tmp_path),
    )


def test_project_timeline_uses_only_selected_videos_in_shot_order(
    migrated_client: TestClient,
) -> None:
    project = _create_project(migrated_client)
    second = _create_shot(migrated_client, project["id"], "Second")
    first = _create_shot(migrated_client, project["id"], "First")
    _create_selected_video_output(project["id"], second["id"], selected=True)
    _create_selected_video_output(project["id"], first["id"], selected=False)

    response = migrated_client.get(f"/api/projects/{project['id']}/timeline")

    assert response.status_code == 200
    payload = response.json()
    assert [clip["shot_name"] for clip in payload["clips"]] == ["Second", "First"]
    assert payload["clips"][0]["status"] == "ready"
    assert payload["clips"][1]["status"] == "missing"
    assert payload["ready_clip_count"] == 1
    assert any(blocker["code"] == "SHOT_ADOPTED_VIDEO_MISSING" for blocker in payload["blockers"])
    assert "relative_path" not in json.dumps(payload)
    assert str(get_settings().resolved_storage_dir) not in json.dumps(payload)


def test_project_timeline_requires_completed_selected_video_run(
    migrated_client: TestClient,
) -> None:
    project = _create_project(migrated_client)
    shot = _create_shot(migrated_client, project["id"], "Not Completed")
    _create_selected_video_output(project["id"], shot["id"], selected=True, run_status="running")

    response = migrated_client.get(f"/api/projects/{project['id']}/timeline")

    assert response.status_code == 200
    payload = response.json()
    assert payload["clips"][0]["status"] == "missing"
    assert payload["ready_clip_count"] == 0
    assert any(blocker["code"] == "SHOT_ADOPTED_VIDEO_MISSING" for blocker in payload["blockers"])


def test_project_timeline_uses_ffprobe_actual_duration(
    migrated_client: TestClient,
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "app.service.project_timeline_service.FfmpegService",
        lambda: _AvailableFfmpeg(tmp_path, duration=2.125),
    )
    project = _create_project(migrated_client)
    shot = _create_shot(migrated_client, project["id"], "Actual Duration")
    _create_selected_video_output(
        project["id"],
        shot["id"],
        selected=True,
        task_duration=99,
        duration=2.125,
    )

    response = migrated_client.get(f"/api/projects/{project['id']}/timeline")

    assert response.status_code == 200
    payload = response.json()
    assert payload["estimated_duration_seconds"] == 2.125
    assert payload["clips"][0]["duration_seconds"] == 2.125


def test_project_timeline_blocks_missing_adopted_video_file(
    migrated_client: TestClient,
) -> None:
    project = _create_project(migrated_client)
    shot = _create_shot(migrated_client, project["id"], "Missing File")
    selected = _create_selected_video_output(project["id"], shot["id"], selected=True)
    media_path = get_settings().resolved_storage_dir / selected["relative_path"]
    media_path.unlink()

    response = migrated_client.get(f"/api/projects/{project['id']}/timeline")

    assert response.status_code == 200
    payload = response.json()
    assert payload["clips"][0]["status"] == "blocked"
    assert payload["exportable"] is False
    assert any(blocker["code"] == "ADOPTED_VIDEO_FILE_MISSING" for blocker in payload["blockers"])


def test_project_timeline_cross_project_access_fails(migrated_client: TestClient) -> None:
    _create_project(migrated_client)
    other = _create_project(migrated_client)

    response = migrated_client.get(f"/api/projects/{uuid4()}/timeline")
    other_response = migrated_client.get(f"/api/projects/{other['id']}/timeline")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"
    assert other_response.status_code == 200


def test_project_export_create_snapshot_and_missing_ffmpeg_blocker(
    migrated_client: TestClient,
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "app.service.project_export_service.FfmpegService",
        lambda: _UnavailableFfmpeg(tmp_path),
    )

    project = _create_project(migrated_client)
    shot = _create_shot(migrated_client, project["id"], "Ready Shot")
    _create_selected_video_output(project["id"], shot["id"], selected=True, duration=2)

    create_response = migrated_client.post(
        f"/api/projects/{project['id']}/exports",
        json={"name": "Final Export", "target_width": 720, "target_height": 1280, "target_fps": 24},
    )
    mark_response = migrated_client.post(
        f"/api/projects/{project['id']}/exports/{create_response.json()['id']}/mark-ready"
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["status"] == "draft"
    assert payload["clip_count"] == 1
    assert payload["duration_seconds"] == 2
    assert mark_response.status_code == 422
    assert mark_response.json()["error"]["code"] == "PROJECT_EXPORT_FFMPEG_UNAVAILABLE"


def test_project_export_snapshot_is_stable_after_adopted_video_changes(
    migrated_client: TestClient,
) -> None:
    project = _create_project(migrated_client)
    shot = _create_shot(migrated_client, project["id"], "Stable Shot")
    original = _create_selected_video_output(project["id"], shot["id"], selected=True, duration=2)

    response = migrated_client.post(
        f"/api/projects/{project['id']}/exports",
        json={"name": "Snapshot", "target_width": 720, "target_height": 1280, "target_fps": 24},
    )
    replacement = _create_selected_video_output(
        project["id"],
        shot["id"],
        selected=True,
        duration=4,
        created_at=datetime.now(UTC) + timedelta(seconds=5),
    )

    with get_session_factory()() as session:
        record = session.get(ProjectExportRecord, response.json()["id"])
        assert record is not None
        snapshot = json.loads(record.snapshot)

    assert snapshot["clips"][0]["media_asset_id"] == original["media_asset_id"]
    assert snapshot["clips"][0]["media_asset_id"] != replacement["media_asset_id"]
    assert response.json()["duration_seconds"] == 2


def test_project_export_rejects_invalid_settings(migrated_client: TestClient) -> None:
    project = _create_project(migrated_client)

    width_response = migrated_client.post(
        f"/api/projects/{project['id']}/exports",
        json={"target_width": 721, "target_height": 1280, "target_fps": 24},
    )
    fps_response = migrated_client.post(
        f"/api/projects/{project['id']}/exports",
        json={"target_width": 720, "target_height": 1280, "target_fps": 0},
    )

    assert width_response.status_code == 422
    assert width_response.json()["error"]["code"] == "PROJECT_EXPORT_INVALID_DIMENSIONS"
    assert fps_response.status_code == 422
    assert fps_response.json()["error"]["code"] == "PROJECT_EXPORT_INVALID_FPS"


def test_project_export_runner_success_creates_final_media_and_does_not_mutate_sources(
    migrated_client: TestClient,
    tmp_path: Path,
) -> None:
    project = _create_project(migrated_client)
    shot = _create_shot(migrated_client, project["id"], "Export Shot")
    selected = _create_selected_video_output(project["id"], shot["id"], selected=True)
    with get_session_factory()() as session:
        service = ProjectExportService(session, ffmpeg_service=_AvailableFfmpeg(tmp_path))
        export = service.create_export(
            uuid4_from_string(project["id"]),
            _payload("Final"),
        )
        service.mark_ready(uuid4_from_string(project["id"]), uuid4_from_string(export.id))
        record = session.get(ProjectExportRecord, export.id)
        assert record is not None
        record.status = ProjectExportStatus.QUEUED.value
        session.commit()

    runner = ProjectExportRunner(ffmpeg_service=_AvailableFfmpeg(tmp_path))
    runner.run_export(export.id)

    with get_session_factory()() as session:
        record = session.get(ProjectExportRecord, export.id)
        output = session.get(VideoGenerationOutputRecord, selected["output_id"])
        assert record is not None
        assert output is not None
        assert record.status == ProjectExportStatus.COMPLETED.value
        assert record.output_media_asset_id is not None
        media = session.get(MediaAssetRecord, record.output_media_asset_id)
        assert media is not None
        assert media.media_type == "video"
        assert media.relative_path.startswith(f"projects/{project['id']}/exports/{export.id}/")
        assert media.width == 720
        assert media.height == 1280
        assert output.is_selected is True


def test_project_export_runner_rejects_non_browser_compatible_final_video(
    migrated_client: TestClient,
    tmp_path: Path,
) -> None:
    project = _create_project(migrated_client)
    shot = _create_shot(migrated_client, project["id"], "Bad Final")
    _create_selected_video_output(project["id"], shot["id"], selected=True)
    with get_session_factory()() as session:
        service = ProjectExportService(session, ffmpeg_service=_AvailableFfmpeg(tmp_path))
        export = service.create_export(uuid4_from_string(project["id"]), _payload("Bad Final"))
        service.mark_ready(uuid4_from_string(project["id"]), uuid4_from_string(export.id))
        record = session.get(ProjectExportRecord, export.id)
        assert record is not None
        record.status = ProjectExportStatus.QUEUED.value
        session.commit()

    runner = ProjectExportRunner(ffmpeg_service=_BadFinalFfmpeg(tmp_path))
    runner.run_export(export.id)

    with get_session_factory()() as session:
        record = session.get(ProjectExportRecord, export.id)
        assert record is not None
        assert record.status == ProjectExportStatus.FAILED.value
        assert record.output_media_asset_id is None
        assert record.error_message == "最终导出失败，请检查源视频和 FFmpeg 环境。"


def test_project_export_runner_failure_sets_safe_failed_status(
    migrated_client: TestClient,
    tmp_path: Path,
) -> None:
    project = _create_project(migrated_client)
    shot = _create_shot(migrated_client, project["id"], "Fail Shot")
    _create_selected_video_output(project["id"], shot["id"], selected=True)
    with get_session_factory()() as session:
        service = ProjectExportService(session, ffmpeg_service=_AvailableFfmpeg(tmp_path))
        export = service.create_export(uuid4_from_string(project["id"]), _payload("Failure"))
        service.mark_ready(uuid4_from_string(project["id"]), uuid4_from_string(export.id))
        record = session.get(ProjectExportRecord, export.id)
        assert record is not None
        record.status = ProjectExportStatus.QUEUED.value
        session.commit()

    runner = ProjectExportRunner(ffmpeg_service=_FailingFfmpeg(tmp_path))
    runner.run_export(export.id)

    with get_session_factory()() as session:
        record = session.get(ProjectExportRecord, export.id)
        assert record is not None
        assert record.status == ProjectExportStatus.FAILED.value
        assert record.error_message == "最终导出失败，请检查源视频和 FFmpeg 环境。"
        assert str(get_settings().resolved_storage_dir) not in (record.error_message or "")


def _create_project(client: TestClient) -> dict[str, str]:
    return client.post("/api/projects", json={"name": f"Project {uuid4()}"}).json()


def _create_shot(client: TestClient, project_id: str, name: str) -> dict[str, str]:
    return client.post(f"/api/projects/{project_id}/shots", json={"name": name}).json()


def _create_selected_video_output(
    project_id: str,
    shot_id: str,
    selected: bool,
    duration: float = 2.0,
    task_duration: float | None = None,
    created_at: datetime | None = None,
    run_status: str = "completed",
) -> dict[str, str]:
    now = created_at or datetime.now(UTC)
    task_id = str(uuid4())
    run_id = str(uuid4())
    output_id = str(uuid4())
    media_id = str(uuid4())
    relative_path = f"projects/{project_id}/media/generated-videos/{media_id}.mp4"
    media_path = get_settings().resolved_storage_dir / relative_path
    media_path.parent.mkdir(parents=True, exist_ok=True)
    media_path.write_bytes(b"fake mp4")
    with get_session_factory()() as session:
        session.add(
            VideoGenerationTaskRecord(
                id=task_id,
                project_id=project_id,
                shot_id=shot_id,
                name="Video Task",
                status="ready",
                prompt="Prompt",
                duration_seconds=task_duration if task_duration is not None else duration,
                fps=16,
                width=640,
                height=640,
                workflow_id="video_wan22_14b_flf2v_v1",
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            VideoGenerationRunRecord(
                id=run_id,
                project_id=project_id,
                video_task_id=task_id,
                run_number=1,
                provider="comfyui",
                workflow_id="video_wan22_14b_flf2v_v1",
                workflow_version="1",
                status=run_status,
                submitted_payload_snapshot="{}",
                completed_at=now if run_status == "completed" else None,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            MediaAssetRecord(
                id=media_id,
                project_id=project_id,
                media_type="video",
                original_filename="output.mp4",
                stored_filename=f"{media_id}.mp4",
                relative_path=relative_path,
                mime_type="video/mp4",
                extension="mp4",
                size_bytes=media_path.stat().st_size,
                width=640,
                height=640,
                sha256=media_id.replace("-", ""),
                created_at=now,
            )
        )
        session.add(
            VideoGenerationOutputRecord(
                id=output_id,
                project_id=project_id,
                run_id=run_id,
                media_asset_id=media_id,
                output_index=1,
                provider_filename="output.mp4",
                provider_subfolder="",
                provider_type="output",
                width=640,
                height=640,
                duration_seconds=duration,
                fps=16,
                seed=1,
                is_selected=selected,
                created_at=now,
            )
        )
        session.commit()
    return {
        "task_id": task_id,
        "run_id": run_id,
        "output_id": output_id,
        "media_asset_id": media_id,
        "relative_path": relative_path,
    }


def _payload(name: str):
    from app.api.schemas.project_export import ProjectExportCreateRequest

    return ProjectExportCreateRequest(
        name=name,
        target_width=720,
        target_height=1280,
        target_fps=24,
        video_codec="libx264",
    )


def uuid4_from_string(value: str):
    from uuid import UUID

    return UUID(value)


class _AvailableFfmpeg:
    def __init__(self, tmp_path: Path, duration: float = 2.0) -> None:
        self.tmp_path = tmp_path
        self.duration = duration

    def ffmpeg_available(self) -> bool:
        return True

    def ffprobe_available(self) -> bool:
        return True

    def probe(self, source_path: Path) -> VideoProbe:
        assert source_path.exists()
        if source_path.name == "final.mp4":
            return VideoProbe(
                width=720,
                height=1280,
                fps=24,
                duration_seconds=self.duration,
                codec="h264",
                pixel_format="yuv420p",
                codec_type="video",
                audio_stream_count=0,
                frame_count=48,
            )
        return VideoProbe(
            width=640,
            height=640,
            fps=16,
            duration_seconds=self.duration,
            codec="h264",
            pixel_format="yuv420p",
            codec_type="video",
            audio_stream_count=0,
            frame_count=32,
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
        assert source_path.exists()
        assert width == 720
        assert height == 1280
        assert fps == 24
        assert codec == "libx264"
        output_path.write_bytes(b"segment")

    def concat(self, segment_paths: Iterable[Path], concat_file: Path, output_path: Path) -> None:
        assert list(segment_paths)
        concat_file.write_text("concat", encoding="utf-8")
        output_path.write_bytes(b"final video")


class _FailingFfmpeg(_AvailableFfmpeg):
    def concat(self, segment_paths: Iterable[Path], concat_file: Path, output_path: Path) -> None:
        raise RuntimeError("F:\\LocalDramaStudio\\private\\ffmpeg failed")


class _UnavailableFfmpeg(_AvailableFfmpeg):
    def ffmpeg_available(self) -> bool:
        return False

    def ffprobe_available(self) -> bool:
        return False


class _BadFinalFfmpeg(_AvailableFfmpeg):
    def probe(self, source_path: Path) -> VideoProbe:
        probe = super().probe(source_path)
        if source_path.name == "final.mp4":
            return VideoProbe(
                width=probe.width,
                height=probe.height,
                fps=probe.fps,
                duration_seconds=probe.duration_seconds,
                codec="hevc",
                pixel_format="yuv444p",
                codec_type="video",
                audio_stream_count=1,
                frame_count=probe.frame_count,
            )
        return probe
