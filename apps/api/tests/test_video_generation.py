import asyncio
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

from app.core.config import get_settings
from app.infrastructure.database import get_session_factory
from app.infrastructure.generation.base import (
    GenerationProviderHealth,
    ProviderJobStatus,
    ProviderOutputFile,
    ProviderSubmission,
    ProviderUploadedImage,
    VideoProviderRequest,
)
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.video_generation import (
    VideoGenerationOutputRecord,
    VideoGenerationRunRecord,
)
from app.service.video_generation_runner import VideoGenerationRunner
from tests.test_keyframe_tasks import create_ready_shot_fixture


class StubVideoProvider:
    submitted_workflow: dict[str, object] | None = None

    async def check_health(self) -> GenerationProviderHealth:
        return GenerationProviderHealth(available=True, provider="comfyui", status="online")

    async def get_required_node_types(self) -> set[str]:
        return {"LoadImage", "VideoCombine"}

    async def upload_input_image(
        self,
        *,
        filename: str,
        content: bytes,
        mime_type: str | None,
    ) -> ProviderUploadedImage:
        assert filename.startswith("lds_video_")
        assert content
        assert mime_type == "image/png"
        return ProviderUploadedImage(filename="uploaded.png", subfolder="", input_type="input")

    async def submit(self, request: VideoProviderRequest) -> ProviderSubmission:
        StubVideoProvider.submitted_workflow = request.workflow
        return ProviderSubmission(provider_job_id="video-prompt-1")

    async def get_status(self, provider_job_id: str) -> ProviderJobStatus:
        return ProviderJobStatus(status="completed")

    async def fetch_video_outputs(
        self,
        provider_job_id: str,
        *,
        output_file_keys: list[str],
        allowed_extensions: list[str],
    ) -> list[ProviderOutputFile]:
        assert output_file_keys == ["videos"]
        assert "mp4" in allowed_extensions
        return [
            ProviderOutputFile(
                filename="result.mp4",
                subfolder="",
                output_type="output",
                mime_type="video/mp4",
                content=b"fake mp4 bytes",
            )
        ]


def make_png_bytes() -> bytes:
    image = Image.new("RGB", (64, 64), (20, 80, 120))
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def upload_video_input(client: TestClient, project_id: str) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/video-inputs/images",
        files={"file": ("input.png", make_png_bytes(), "image/png")},
    )
    assert response.status_code == 201
    return response.json()["media_asset"]


def enable_video_generation(monkeypatch, workflow_dir: Path | None = None) -> None:
    if workflow_dir:
        monkeypatch.setenv("LDS_API_COMFYUI_WORKFLOW_DIR", str(workflow_dir))
    monkeypatch.setenv("LDS_API_COMFYUI_POLL_INTERVAL_SECONDS", "1")
    monkeypatch.setenv("LDS_API_COMFYUI_JOB_TIMEOUT_SECONDS", "5")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.service.video_generation_service.create_video_generation_provider",
        lambda settings: StubVideoProvider(),
    )
    monkeypatch.setattr(
        "app.service.video_generation_runner.create_video_generation_provider",
        lambda settings: StubVideoProvider(),
    )
    monkeypatch.setattr(
        "app.api.system.create_video_generation_provider",
        lambda settings: StubVideoProvider(),
    )


def write_video_workflow_files(workflow_dir: Path) -> None:
    workflow_dir.mkdir(parents=True, exist_ok=True)
    (workflow_dir / "video_i2v_14b_v1.manifest.json").write_text(
        """
        {
          "schema_version": 1,
          "workflow_id": "video_i2v_14b_v1",
          "display_name": "Video Test Workflow",
          "version": "test",
          "workflow_file": "video_i2v_14b_v1.json",
          "provider": "comfyui",
          "required_node_types": ["LoadImage", "VideoCombine"],
          "input_image_binding": {"node_id": "1", "input_name": "image"},
          "parameter_bindings": {
            "positive_prompt": {"node_id": "2", "input_name": "text"},
            "width": {"node_id": "3", "input_name": "width"},
            "height": {"node_id": "3", "input_name": "height"},
            "duration_seconds": {"node_id": "3", "input_name": "duration_seconds"},
            "fps": {"node_id": "3", "input_name": "fps"},
            "seed": {"node_id": "3", "input_name": "seed"}
          },
          "output_node_ids": ["4"],
          "output_file_keys": ["videos"],
          "allowed_output_extensions": ["mp4"]
        }
        """,
        encoding="utf-8",
    )
    (workflow_dir / "video_i2v_14b_v1.json").write_text(
        """
        {
          "1": {"class_type": "LoadImage", "inputs": {"image": ""}},
          "2": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
          "3": {
            "class_type": "VideoSettings",
            "inputs": {"width": 768, "height": 1360, "duration_seconds": 5, "fps": 16, "seed": 1}
          },
          "4": {"class_type": "VideoCombine", "inputs": {}}
        }
        """,
        encoding="utf-8",
    )


def create_ready_video_task(
    client: TestClient,
    monkeypatch,
    tmp_path: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    workflow_dir = tmp_path / "workflows"
    write_video_workflow_files(workflow_dir)
    enable_video_generation(monkeypatch, workflow_dir)
    data = create_ready_shot_fixture(client)
    media_asset = upload_video_input(client, data["project_id"])
    task = client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/video-tasks",
        json={"input_media_asset_id": media_asset["id"]},
    ).json()
    patch = client.patch(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}",
        json={"prompt": "rainy night street push in", "seed": 0, "workflow_id": "video_i2v_14b_v1"},
    )
    assert patch.status_code == 200
    ready = client.post(f"/api/projects/{data['project_id']}/video-tasks/{task['id']}/mark-ready")
    assert ready.status_code == 200
    return data, ready.json()


def create_completed_video_run(
    client: TestClient,
    project_id: str,
    task_id: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/video-tasks/{task_id}/runs",
        json={"workflow_id": "video_i2v_14b_v1"},
    )
    assert response.status_code == 202
    run_id = response.json()["run_id"]
    asyncio.run(VideoGenerationRunner().run_task(run_id))
    run = client.get(f"/api/projects/{project_id}/video-runs/{run_id}")
    assert run.status_code == 200
    assert run.json()["status"] == "completed"
    return run.json()


def test_video_workflow_missing_file_is_unavailable(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    data = create_ready_shot_fixture(migrated_client)
    enable_video_generation(monkeypatch)

    response = migrated_client.get(f"/api/projects/{data['project_id']}/video-workflows")

    assert response.status_code == 200
    workflow = response.json()["items"][0]
    assert workflow["workflow_id"] == "video_i2v_14b_v1"
    assert workflow["available"] is False
    assert "workflow_file_missing" in workflow["missing_requirements"]


def test_video_task_upload_and_readiness_reject_missing_workflow(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    data = create_ready_shot_fixture(migrated_client)
    enable_video_generation(monkeypatch)
    media_asset = upload_video_input(migrated_client, data["project_id"])
    task = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/video-tasks",
        json={"input_media_asset_id": media_asset["id"]},
    ).json()

    updated = migrated_client.patch(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}",
        json={"prompt": "镜头缓慢推进", "duration_seconds": 4, "fps": 16},
    )
    ready = migrated_client.post(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}/mark-ready"
    )

    assert updated.status_code == 200
    assert updated.json()["input_media_asset"]["content_url"].startswith("/api/media/")
    assert "relative_path" not in str(updated.json())
    assert ready.status_code == 422
    assert "workflow_unavailable" in ready.json()["error"]["details"]["blocking_issues"]


def test_video_run_completes_saves_video_and_is_idempotent(
    migrated_client: TestClient,
    monkeypatch,
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    write_video_workflow_files(workflow_dir)
    enable_video_generation(monkeypatch, workflow_dir)
    data = create_ready_shot_fixture(migrated_client)
    media_asset = upload_video_input(migrated_client, data["project_id"])
    task = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/video-tasks",
        json={"input_media_asset_id": media_asset["id"]},
    ).json()
    patch = migrated_client.patch(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}",
        json={"prompt": "雨夜街道逐渐推进", "seed": 0, "workflow_id": "video_i2v_14b_v1"},
    )
    assert patch.status_code == 200
    ready = migrated_client.post(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}/mark-ready"
    )
    assert ready.status_code == 200

    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}/runs",
        json={"workflow_id": "video_i2v_14b_v1"},
    )
    run_id = response.json()["run_id"]
    run = migrated_client.get(f"/api/projects/{data['project_id']}/video-runs/{run_id}").json()
    asyncio.run(VideoGenerationRunner().run_task(run_id))

    refreshed = migrated_client.get(
        f"/api/projects/{data['project_id']}/video-runs/{run_id}"
    ).json()
    with get_session_factory()() as session:
        outputs = list(session.scalars(select(VideoGenerationOutputRecord)).all())
        video_assets = [
            asset
            for asset in session.scalars(select(MediaAssetRecord)).all()
            if asset.media_type == "video"
        ]

    assert response.status_code == 202
    assert run["status"] == "completed", (run["error_code"], run["error_message_safe"])
    assert refreshed["status"] == "completed", (
        refreshed["error_code"],
        refreshed["error_message_safe"],
    )
    assert len(outputs) == 1
    assert len(video_assets) == 1
    output = refreshed["outputs"][0]
    assert output["media_asset"]["media_type"] == "video"
    assert output["media_asset"]["thumbnail_url"] is None
    assert output["media_asset"]["content_url"].startswith("/api/media/")
    assert "relative_path" not in str(refreshed)
    assert StubVideoProvider.submitted_workflow is not None
    assert StubVideoProvider.submitted_workflow["1"]["inputs"]["image"] == "uploaded.png"
    assert StubVideoProvider.submitted_workflow["2"]["inputs"]["text"] == "雨夜街道逐渐推进"


def test_video_output_selection_is_exclusive_and_can_be_unselected(
    migrated_client: TestClient,
    monkeypatch,
    tmp_path: Path,
) -> None:
    data, task = create_ready_video_task(migrated_client, monkeypatch, tmp_path)
    first_run = create_completed_video_run(migrated_client, data["project_id"], task["id"])
    second_run = create_completed_video_run(migrated_client, data["project_id"], task["id"])
    first_output = first_run["outputs"][0]
    second_output = second_run["outputs"][0]

    selected_first = migrated_client.post(
        f"/api/projects/{data['project_id']}/video-outputs/{first_output['id']}/select"
    )
    selected_second = migrated_client.post(
        f"/api/projects/{data['project_id']}/video-outputs/{second_output['id']}/select"
    )
    refreshed_runs = migrated_client.get(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}/runs"
    ).json()
    selected_outputs = [
        output
        for run in refreshed_runs["items"]
        for output in run["outputs"]
        if output["is_selected"]
    ]

    assert selected_first.status_code == 200
    assert selected_first.json()["is_selected"] is True
    assert selected_second.status_code == 200
    assert selected_second.json()["is_selected"] is True
    assert [output["id"] for output in selected_outputs] == [second_output["id"]]

    unselected = migrated_client.delete(
        f"/api/projects/{data['project_id']}/video-outputs/{second_output['id']}/select"
    )
    refreshed_runs = migrated_client.get(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}/runs"
    ).json()
    refreshed_tasks = migrated_client.get(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/video-tasks"
    ).json()

    assert unselected.status_code == 200
    assert unselected.json()["is_selected"] is False
    assert all(
        not output["is_selected"] for run in refreshed_runs["items"] for output in run["outputs"]
    )
    assert refreshed_tasks["items"][0]["selected_output"] is None


def test_failed_video_run_does_not_lock_task_and_retry_creates_new_run(
    migrated_client: TestClient,
    monkeypatch,
    tmp_path: Path,
) -> None:
    data, task = create_ready_video_task(migrated_client, monkeypatch, tmp_path)
    first_run = create_completed_video_run(migrated_client, data["project_id"], task["id"])

    with get_session_factory()() as session:
        run_record = session.get(VideoGenerationRunRecord, first_run["id"])
        assert run_record is not None
        run_record.status = "failed"
        run_record.error_code = "video_generation_failed"
        run_record.error_message_safe = "Video generation failed"
        session.commit()

    retry = migrated_client.post(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}/runs",
        json={"workflow_id": "video_i2v_14b_v1"},
    )
    assert retry.status_code == 202
    assert retry.json()["run_id"] != first_run["id"]

    runs = migrated_client.get(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}/runs"
    ).json()
    run_numbers = {run["id"]: run["run_number"] for run in runs["items"]}
    statuses = {run["id"]: run["status"] for run in runs["items"]}

    assert runs["total"] == 2
    assert run_numbers[first_run["id"]] == 1
    assert run_numbers[retry.json()["run_id"]] == 2
    assert statuses[first_run["id"]] == "failed"
