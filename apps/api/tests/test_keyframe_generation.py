from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.infrastructure.database import get_session_factory
from app.infrastructure.generation.base import (
    GenerationProviderHealth,
    KeyframeProviderRequest,
    ProviderJobStatus,
    ProviderOutputImage,
    ProviderSubmission,
)
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.keyframe_generation import (
    KeyframeGenerationOutputRecord,
    KeyframeGenerationRunRecord,
)
from app.repository.keyframe_generation_repository import KeyframeGenerationRepository
from app.service.keyframe_generation_runner import KeyframeGenerationRunner
from tests.test_keyframe_tasks import create_keyframe_task, create_ready_shot_fixture


class StubGenerationProvider:
    submitted_workflow: dict[str, object] | None = None

    async def check_health(self) -> GenerationProviderHealth:
        return GenerationProviderHealth(available=True, provider="comfyui", status="online")

    async def get_required_node_types(self) -> set[str]:
        return {
            "CheckpointLoaderSimple",
            "CLIPTextEncode",
            "EmptyLatentImage",
            "KSampler",
            "VAEDecode",
            "SaveImage",
        }

    async def submit(self, request: KeyframeProviderRequest) -> ProviderSubmission:
        StubGenerationProvider.submitted_workflow = request.workflow
        return ProviderSubmission(provider_job_id="prompt-1")

    async def get_status(self, provider_job_id: str) -> ProviderJobStatus:
        return ProviderJobStatus(status="completed")

    async def fetch_outputs(self, provider_job_id: str) -> list[ProviderOutputImage]:
        return [
            ProviderOutputImage(
                filename="keyframe.png",
                subfolder="",
                output_type="output",
                mime_type="image/png",
                content=make_png_bytes(),
            )
        ]

    async def cancel(self, provider_job_id: str) -> None:
        return None


class OfflineProvider:
    async def check_health(self) -> GenerationProviderHealth:
        return GenerationProviderHealth(available=False, provider="comfyui", status="offline")


class SequencedStatusProvider(StubGenerationProvider):
    def __init__(self, statuses: list[str]) -> None:
        self.statuses = statuses
        self.seen: list[str] = []

    async def get_status(self, provider_job_id: str) -> ProviderJobStatus:
        status = self.statuses.pop(0) if self.statuses else "completed"
        self.seen.append(status)
        return ProviderJobStatus(status=status)


def make_png_bytes() -> bytes:
    image = Image.new("RGB", (64, 64), (120, 80, 40))
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def enable_generation(monkeypatch) -> None:
    monkeypatch.setenv("LDS_API_COMFYUI_DEFAULT_CHECKPOINT", "test-model.safetensors")
    monkeypatch.setenv("LDS_API_COMFYUI_POLL_INTERVAL_SECONDS", "1")
    monkeypatch.setenv("LDS_API_COMFYUI_JOB_TIMEOUT_SECONDS", "5")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.service.keyframe_generation_service.create_keyframe_generation_provider",
        lambda settings: StubGenerationProvider(),
    )
    monkeypatch.setattr(
        "app.service.keyframe_generation_runner.create_keyframe_generation_provider",
        lambda settings: StubGenerationProvider(),
    )


def ready_task(client: TestClient, monkeypatch) -> tuple[dict[str, object], dict[str, object]]:
    enable_generation(monkeypatch)
    data = create_ready_shot_fixture(client)
    task = create_keyframe_task(client, data["project_id"], str(data["shot"]["id"]))
    ready = client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/mark-ready"
    )
    assert ready.status_code == 200
    return data, ready.json()


def test_workflow_unavailable_when_checkpoint_missing(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    data = create_ready_shot_fixture(migrated_client)
    monkeypatch.setattr(
        "app.service.keyframe_generation_service.create_keyframe_generation_provider",
        lambda settings: StubGenerationProvider(),
    )

    response = migrated_client.get(f"/api/projects/{data['project_id']}/keyframe-workflows")

    assert response.status_code == 200
    workflow = response.json()["items"][0]
    assert workflow["workflow_id"] == "keyframe_basic_v1"
    assert workflow["available"] is False
    assert "default_checkpoint_not_configured" in workflow["missing_requirements"]


def test_start_run_completes_and_saves_output(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    data, task = ready_task(migrated_client, monkeypatch)

    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/runs",
        json={"workflow_id": "keyframe_basic_v1"},
    )
    runs = migrated_client.get(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/runs"
    ).json()

    assert response.status_code == 202
    assert runs["total"] == 1
    run = runs["items"][0]
    assert run["status"] == "completed"
    assert run["provider_job_id"] == "prompt-1"
    assert run["submitted_payload_snapshot"]["reference_inputs_used"] is False
    assert len(run["submitted_payload_snapshot"]["task_reference_ids"]) == 2
    assert run["submitted_payload_snapshot"]["effective_prompt_language"] == "zh"
    assert isinstance(run["submitted_payload_snapshot"]["seed"], int)
    assert len(run["outputs"]) == 1
    assert run["outputs"][0]["media_asset"]["content_url"].startswith("/api/media/")
    assert "relative_path" not in str(run)
    assert "127.0.0.1" not in str(run)
    assert "CheckpointLoaderSimple" not in str(run)
    assert "test-model.safetensors" not in str(run)


def test_output_count_greater_than_one_is_rejected_without_run(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    data, task = ready_task(migrated_client, monkeypatch)
    patch = migrated_client.patch(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}",
        json={"output_count": 2},
    )
    assert patch.status_code == 200
    ready = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/mark-ready"
    )
    assert ready.status_code == 200

    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/runs",
        json={"workflow_id": "keyframe_basic_v1"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "workflow_output_count_unsupported"
    with get_session_factory()() as session:
        count = session.query(KeyframeGenerationRunRecord).count()
    assert count == 0


def test_seed_zero_and_prompt_en_are_submitted(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    data, task = ready_task(migrated_client, monkeypatch)
    update = migrated_client.patch(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}",
        json={"seed": 0, "prompt_en": "english prompt"},
    )
    assert update.status_code == 200
    ready = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/mark-ready"
    )
    assert ready.status_code == 200

    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/runs",
        json={"workflow_id": "keyframe_basic_v1"},
    )

    assert response.status_code == 202
    workflow = StubGenerationProvider.submitted_workflow
    assert workflow is not None
    assert workflow["3"]["inputs"]["seed"] == 0
    assert workflow["6"]["inputs"]["text"] == "english prompt"


def test_unknown_sampler_is_rejected(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    data, task = ready_task(migrated_client, monkeypatch)
    update = migrated_client.patch(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}",
        json={"sampler_name": "unknown_sampler"},
    )
    assert update.status_code == 200
    ready = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/mark-ready"
    )
    assert ready.status_code == 200

    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/runs",
        json={"workflow_id": "keyframe_basic_v1"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "workflow_sampler_unsupported"


def test_unknown_scheduler_is_rejected(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    data, task = ready_task(migrated_client, monkeypatch)
    update = migrated_client.patch(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}",
        json={"scheduler_name": "unknown_scheduler"},
    )
    assert update.status_code == 200
    ready = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/mark-ready"
    )
    assert ready.status_code == 200

    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/runs",
        json={"workflow_id": "keyframe_basic_v1"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "workflow_scheduler_unsupported"


def test_provider_offline_does_not_create_half_run(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    data = create_ready_shot_fixture(migrated_client)
    task = create_keyframe_task(migrated_client, data["project_id"], str(data["shot"]["id"]))
    ready = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/mark-ready"
    )
    assert ready.status_code == 200
    monkeypatch.setenv("LDS_API_COMFYUI_DEFAULT_CHECKPOINT", "test-model.safetensors")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.service.keyframe_generation_service.create_keyframe_generation_provider",
        lambda settings: OfflineProvider(),
    )

    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/runs",
        json={"workflow_id": "keyframe_basic_v1"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "comfyui_unavailable"
    with get_session_factory()() as session:
        count = session.query(KeyframeGenerationRunRecord).count()
    assert count == 0


def test_capabilities_online_can_coexist_with_workflow_model_missing(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    data = create_ready_shot_fixture(migrated_client)
    monkeypatch.delenv("LDS_API_COMFYUI_DEFAULT_CHECKPOINT", raising=False)
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.api.system.create_keyframe_generation_provider",
        lambda settings: StubGenerationProvider(),
    )
    monkeypatch.setattr(
        "app.service.keyframe_generation_service.create_keyframe_generation_provider",
        lambda settings: StubGenerationProvider(),
    )

    capabilities = migrated_client.get("/api/system/capabilities")
    workflows = migrated_client.get(f"/api/projects/{data['project_id']}/keyframe-workflows")

    assert capabilities.status_code == 200
    assert capabilities.json()["keyframe_generation"] == {
        "available": True,
        "provider": "comfyui",
        "status": "online",
    }
    workflow = workflows.json()["items"][0]
    assert workflow["available"] is False
    assert "default_checkpoint_not_configured" in workflow["missing_requirements"]


def test_select_output_is_unique_per_task(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    data, task = ready_task(migrated_client, monkeypatch)
    first = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/runs",
        json={"workflow_id": "keyframe_basic_v1"},
    ).json()
    second = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/runs",
        json={"workflow_id": "keyframe_basic_v1"},
    ).json()
    first_run = migrated_client.get(
        f"/api/projects/{data['project_id']}/keyframe-runs/{first['run_id']}"
    ).json()
    second_run = migrated_client.get(
        f"/api/projects/{data['project_id']}/keyframe-runs/{second['run_id']}"
    ).json()
    first_output = first_run["outputs"][0]["id"]
    second_output = second_run["outputs"][0]["id"]

    migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-outputs/{first_output}/select"
    )
    selected = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-outputs/{second_output}/select"
    )
    refreshed_first = migrated_client.get(
        f"/api/projects/{data['project_id']}/keyframe-runs/{first['run_id']}"
    ).json()
    refreshed_second = migrated_client.get(
        f"/api/projects/{data['project_id']}/keyframe-runs/{second['run_id']}"
    ).json()

    assert selected.status_code == 200
    assert refreshed_first["outputs"][0]["is_selected"] is False
    assert refreshed_second["outputs"][0]["is_selected"] is True


def test_history_waiting_state_is_not_immediate_failure(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    data, task = ready_task(migrated_client, monkeypatch)
    provider = SequencedStatusProvider(["waiting", "running", "completed"])
    monkeypatch.setattr(
        "app.service.keyframe_generation_runner.create_keyframe_generation_provider",
        lambda settings: provider,
    )

    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/runs",
        json={"workflow_id": "keyframe_basic_v1"},
    )
    run = migrated_client.get(
        f"/api/projects/{data['project_id']}/keyframe-runs/{response.json()['run_id']}"
    ).json()

    assert response.status_code == 202
    assert provider.seen == ["waiting", "running", "completed"]
    assert run["status"] == "completed"
    assert run["started_at"] is not None


def test_repeated_runner_sync_does_not_duplicate_outputs(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    data, task = ready_task(migrated_client, monkeypatch)
    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/runs",
        json={"workflow_id": "keyframe_basic_v1"},
    )
    run_id = response.json()["run_id"]

    import asyncio

    asyncio.run(KeyframeGenerationRunner().run_task(run_id))

    with get_session_factory()() as session:
        outputs = list(session.scalars(select(KeyframeGenerationOutputRecord)).all())
        media_assets = list(session.scalars(select(MediaAssetRecord)).all())

    assert len(outputs) == 1
    generated_assets = [
        asset for asset in media_assets if "generated-keyframes" in asset.relative_path
    ]
    assert len(generated_assets) == 1


def test_output_save_database_failure_cleans_new_files(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    data, task = ready_task(migrated_client, monkeypatch)

    def fail_create_output_with_media(self, media_asset, output) -> None:
        raise SQLAlchemyError("simulated save failure")

    monkeypatch.setattr(
        KeyframeGenerationRepository,
        "create_output_with_media",
        fail_create_output_with_media,
    )

    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/runs",
        json={"workflow_id": "keyframe_basic_v1"},
    )
    run = migrated_client.get(
        f"/api/projects/{data['project_id']}/keyframe-runs/{response.json()['run_id']}"
    ).json()
    generated_dir = (
        get_settings().resolved_storage_dir
        / "projects"
        / data["project_id"]
        / "media"
        / "generated-keyframes"
    )

    assert response.status_code == 202
    assert run["status"] == "failed"
    assert run["error_code"] == "generated_media_save_failed"
    if generated_dir.exists():
        assert not any(path.is_file() for path in generated_dir.rglob("*"))


def test_deleting_keyframe_task_keeps_generated_media_asset_and_file(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    data, task = ready_task(migrated_client, monkeypatch)
    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/runs",
        json={"workflow_id": "keyframe_basic_v1"},
    )
    run_id = response.json()["run_id"]
    run = migrated_client.get(f"/api/projects/{data['project_id']}/keyframe-runs/{run_id}").json()
    output = run["outputs"][0]
    media_asset_id = output["media_asset_id"]
    output_id = output["id"]

    delete_response = migrated_client.delete(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}"
    )

    with get_session_factory()() as session:
        deleted_run = session.get(KeyframeGenerationRunRecord, run_id)
        deleted_output = session.get(KeyframeGenerationOutputRecord, output_id)
        media_asset = session.get(MediaAssetRecord, media_asset_id)
        assert media_asset is not None
        media_path = get_settings().resolved_storage_dir / media_asset.relative_path

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert deleted_run is None
    assert deleted_output is None
    assert media_path.exists()


def test_basic_workflow_file_is_auditable() -> None:
    workflow_path = Path(__file__).resolve().parents[3] / "workflows" / "keyframe_basic_v1.json"
    workflow = workflow_path.read_text(encoding="utf-8")
    assert "__LDS_DEFAULT_CHECKPOINT__" in workflow
    assert "C:/" not in workflow
    assert "C:\\" not in workflow
    assert "base64" not in workflow.lower()
    assert "nodes" not in workflow
    allowed_node_types = {
        "CheckpointLoaderSimple",
        "CLIPTextEncode",
        "EmptyLatentImage",
        "KSampler",
        "VAEDecode",
        "SaveImage",
    }
    for node_type in allowed_node_types:
        assert node_type in workflow
