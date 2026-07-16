import asyncio
import json
import shutil
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

from app.core.config import get_settings
from app.domain.video_generation import VideoGenerationErrorCode, VideoInputRole
from app.infrastructure.database import get_session_factory
from app.infrastructure.generation.base import (
    GenerationProviderHealth,
    GenerationProviderRuntimeError,
    ProviderJobStatus,
    ProviderOutputFile,
    ProviderSubmission,
    ProviderUploadedImage,
    VideoProviderRequest,
)
from app.infrastructure.generation.comfyui_video_provider import ComfyUIVideoGenerationProvider
from app.infrastructure.generation.video_workflow import (
    VideoWorkflowMappingValues,
    VideoWorkflowRegistry,
)
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.video_generation import (
    VideoGenerationOutputRecord,
    VideoGenerationRunRecord,
)
from app.service.video_generation_runner import VideoGenerationRunner
from tests.test_keyframe_tasks import create_ready_shot_fixture

REPO_ROOT = Path(__file__).resolve().parents[3]
WAN_WORKFLOW_ID = "video_wan22_14b_flf2v_v1"
WAN_WORKFLOW_JSON = REPO_ROOT / "workflows" / f"{WAN_WORKFLOW_ID}.json"
WAN_WORKFLOW_MANIFEST = REPO_ROOT / "workflows" / f"{WAN_WORKFLOW_ID}.manifest.json"
OLD_WAN_WORKFLOW_JSON = REPO_ROOT / "workflows" / "video_wan2_2_14B_flf2v.json"


class StubVideoProvider:
    submitted_workflow: dict[str, object] | None = None
    uploaded_filenames: list[str] = []
    fail_upload_role: str | None = None
    output_node_ids: list[str] = []
    object_info_override: dict[str, object] | None = None

    async def check_health(self) -> GenerationProviderHealth:
        return GenerationProviderHealth(available=True, provider="comfyui", status="online")

    async def get_object_info(self) -> dict[str, object]:
        if self.object_info_override is not None:
            return self.object_info_override
        return {
            "CLIPLoader": {
                "input": {
                    "required": {
                        "clip_name": [["umt5_xxl_fp8_e4m3fn_scaled.safetensors"]],
                    }
                }
            },
            "CLIPTextEncode": {},
            "CreateVideo": {},
            "KSamplerAdvanced": {},
            "LoadImage": {},
            "SaveVideo": {},
            "UNETLoader": {
                "input": {
                    "required": {
                        "unet_name": [
                            [
                                "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
                                "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
                            ]
                        ],
                    }
                }
            },
            "VAEDecode": {},
            "VAELoader": {
                "input": {
                    "required": {
                        "vae_name": [["wan_2.1_vae.safetensors", "sdxl_vae.safetensors"]],
                    }
                }
            },
            "VideoCombine": {},
            "WanFirstLastFrameToVideo": {},
        }

    async def get_required_node_types(self) -> set[str]:
        return set(await self.get_object_info())

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
        if self.fail_upload_role and self.fail_upload_role in filename:
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.REFERENCE_UPLOAD_FAILED,
                "upload failed",
            )
        self.uploaded_filenames.append(filename)
        return ProviderUploadedImage(filename=filename, subfolder="", input_type="input")

    async def submit(self, request: VideoProviderRequest) -> ProviderSubmission:
        StubVideoProvider.submitted_workflow = request.workflow
        return ProviderSubmission(provider_job_id="video-prompt-1")

    async def get_status(self, provider_job_id: str) -> ProviderJobStatus:
        return ProviderJobStatus(status="completed")

    async def fetch_video_outputs(
        self,
        provider_job_id: str,
        *,
        output_node_ids: list[str],
        output_file_keys: list[str],
        allowed_extensions: list[str],
    ) -> list[ProviderOutputFile]:
        StubVideoProvider.output_node_ids = output_node_ids
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
    StubVideoProvider.submitted_workflow = None
    StubVideoProvider.uploaded_filenames = []
    StubVideoProvider.fail_upload_role = None
    StubVideoProvider.output_node_ids = []
    StubVideoProvider.object_info_override = None
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


def write_first_last_video_workflow_files(workflow_dir: Path) -> None:
    workflow_dir.mkdir(parents=True, exist_ok=True)
    (workflow_dir / "video_flf2v_test.manifest.json").write_text(
        """
        {
          "schema_version": 1,
          "workflow_id": "video_flf2v_test",
          "display_name": "Video First Last Test Workflow",
          "version": "test",
          "workflow_file": "video_flf2v_test.json",
          "provider": "comfyui",
          "mode": "first_last_frame_to_video",
          "required_input_roles": ["start_frame", "end_frame"],
          "required_node_types": ["LoadImage", "VideoCombine"],
          "image_input_bindings": {
            "start_frame": {"node_id": "1", "input": "image"},
            "end_frame": {"node_id": "5", "input_name": "image"}
          },
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
    (workflow_dir / "video_flf2v_test.json").write_text(
        """
        {
          "1": {"class_type": "LoadImage", "inputs": {"image": ""}},
          "5": {"class_type": "LoadImage", "inputs": {"image": ""}},
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


def write_wan_workflow_files(workflow_dir: Path) -> None:
    workflow_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WAN_WORKFLOW_MANIFEST, workflow_dir / WAN_WORKFLOW_MANIFEST.name)
    shutil.copy2(WAN_WORKFLOW_JSON, workflow_dir / WAN_WORKFLOW_JSON.name)


def workflow_mapping_values(
    *,
    duration_seconds: int = 2,
    fps: int = 16,
    negative_prompt: str | None = None,
    seed: int = 123,
) -> VideoWorkflowMappingValues:
    return VideoWorkflowMappingValues(
        positive_prompt="rainy street",
        negative_prompt=negative_prompt,
        width=640,
        height=640,
        duration_seconds=duration_seconds,
        fps=fps,
        seed=seed,
        motion_strength=None,
        camera_motion=None,
        input_images={
            VideoInputRole.START_FRAME: ProviderUploadedImage("start.png"),
            VideoInputRole.END_FRAME: ProviderUploadedImage("end.png"),
        },
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


def test_wan_workflow_file_is_normalized_and_placeholders_are_clean() -> None:
    assert WAN_WORKFLOW_JSON.exists()
    assert WAN_WORKFLOW_MANIFEST.exists()
    assert not OLD_WAN_WORKFLOW_JSON.exists()

    workflow = json.loads(WAN_WORKFLOW_JSON.read_text(encoding="utf-8"))
    serialized = json.dumps(workflow, ensure_ascii=False)

    assert workflow["80"]["inputs"]["image"] == "lds_start_frame_placeholder.png"
    assert workflow["89"]["inputs"]["image"] == "lds_end_frame_placeholder.png"
    assert "保安.png" not in serialized
    assert "男主逆袭.png" not in serialized


def test_wan_workflow_builds_real_mapping_and_computed_length(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    write_wan_workflow_files(workflow_dir)
    monkeypatch.setenv("LDS_API_COMFYUI_WORKFLOW_DIR", str(workflow_dir))
    get_settings.cache_clear()
    registry = VideoWorkflowRegistry(get_settings())
    workflow = registry.get_workflow(WAN_WORKFLOW_ID)

    assert workflow.available_locally is True
    for duration, expected_length in [(2, 33), (3, 49), (5, 81)]:
        payload = registry.build_workflow(
            workflow,
            workflow_mapping_values(
                duration_seconds=duration,
                fps=16,
                negative_prompt="low quality",
                seed=789,
            ),
        )
        assert payload["80"]["inputs"]["image"] == "start.png"
        assert payload["89"]["inputs"]["image"] == "end.png"
        assert payload["90"]["inputs"]["text"] == "rainy street"
        assert payload["78"]["inputs"]["text"] == "low quality"
        assert payload["81"]["inputs"]["width"] == 640
        assert payload["81"]["inputs"]["height"] == 640
        assert payload["81"]["inputs"]["length"] == expected_length
        assert payload["86"]["inputs"]["fps"] == 16
        assert payload["84"]["inputs"]["noise_seed"] == 789
        assert payload["87"]["inputs"]["noise_seed"] == 0
        assert payload["87"]["inputs"]["add_noise"] == "disable"


def test_wan_workflow_negative_prompt_keeps_default_when_empty(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    write_wan_workflow_files(workflow_dir)
    monkeypatch.setenv("LDS_API_COMFYUI_WORKFLOW_DIR", str(workflow_dir))
    get_settings.cache_clear()
    registry = VideoWorkflowRegistry(get_settings())
    workflow = registry.get_workflow(WAN_WORKFLOW_ID)
    assert workflow.workflow is not None
    default_negative = workflow.workflow["78"]["inputs"]["text"]

    payload = registry.build_workflow(workflow, workflow_mapping_values(negative_prompt=None))
    overridden = registry.build_workflow(
        workflow,
        workflow_mapping_values(negative_prompt="blur, watermark"),
    )

    assert payload["78"]["inputs"]["text"] == default_negative
    assert overridden["78"]["inputs"]["text"] == "blur, watermark"


def test_wan_workflow_safety_accepts_model_names_and_rejects_absolute_paths(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    write_wan_workflow_files(workflow_dir)
    monkeypatch.setenv("LDS_API_COMFYUI_WORKFLOW_DIR", str(workflow_dir))
    get_settings.cache_clear()
    registry = VideoWorkflowRegistry(get_settings())
    workflow = registry.get_workflow(WAN_WORKFLOW_ID)
    serialized = json.dumps(workflow.workflow, ensure_ascii=False)

    assert workflow.available_locally is True
    assert "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors" in serialized

    unsafe = json.loads(WAN_WORKFLOW_JSON.read_text(encoding="utf-8"))
    unsafe["80"]["inputs"]["image"] = "F:\\LocalDramaStudio\\storage\\secret.png"
    (workflow_dir / WAN_WORKFLOW_JSON.name).write_text(
        json.dumps(unsafe, ensure_ascii=False),
        encoding="utf-8",
    )
    get_settings.cache_clear()
    unsafe_workflow = VideoWorkflowRegistry(get_settings()).get_workflow(WAN_WORKFLOW_ID)

    assert unsafe_workflow.available_locally is False
    assert "workflow_unsafe_absolute_path" in unsafe_workflow.missing_requirements


def test_wan_workflow_is_unavailable_when_real_file_is_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WAN_WORKFLOW_MANIFEST, workflow_dir / WAN_WORKFLOW_MANIFEST.name)
    monkeypatch.setenv("LDS_API_COMFYUI_WORKFLOW_DIR", str(workflow_dir))
    get_settings.cache_clear()

    workflow = VideoWorkflowRegistry(get_settings()).get_workflow(WAN_WORKFLOW_ID)

    assert workflow.available_locally is False
    assert workflow.missing_requirements == ["workflow_file_missing"]


def test_wan_workflow_safety_rejects_ui_format_and_missing_required_nodes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    write_wan_workflow_files(workflow_dir)

    ui_workflow = {"nodes": [], "links": [], "groups": []}
    (workflow_dir / WAN_WORKFLOW_JSON.name).write_text(json.dumps(ui_workflow), encoding="utf-8")
    monkeypatch.setenv("LDS_API_COMFYUI_WORKFLOW_DIR", str(workflow_dir))
    get_settings.cache_clear()
    workflow = VideoWorkflowRegistry(get_settings()).get_workflow(WAN_WORKFLOW_ID)

    assert workflow.available_locally is False
    assert "workflow_ui_format" in workflow.missing_requirements

    write_wan_workflow_files(workflow_dir)
    missing_node = json.loads(WAN_WORKFLOW_JSON.read_text(encoding="utf-8"))
    missing_node.pop("80")
    (workflow_dir / WAN_WORKFLOW_JSON.name).write_text(
        json.dumps(missing_node, ensure_ascii=False),
        encoding="utf-8",
    )
    get_settings.cache_clear()
    workflow = VideoWorkflowRegistry(get_settings()).get_workflow(WAN_WORKFLOW_ID)

    assert workflow.available_locally is False
    assert "workflow_node_missing:80" in workflow.missing_requirements

    write_wan_workflow_files(workflow_dir)
    wrong_output = json.loads(WAN_WORKFLOW_JSON.read_text(encoding="utf-8"))
    wrong_output["83"]["class_type"] = "PreviewImage"
    (workflow_dir / WAN_WORKFLOW_JSON.name).write_text(
        json.dumps(wrong_output, ensure_ascii=False),
        encoding="utf-8",
    )
    get_settings.cache_clear()
    workflow = VideoWorkflowRegistry(get_settings()).get_workflow(WAN_WORKFLOW_ID)

    assert workflow.available_locally is False
    assert "workflow_output_node_type_invalid:83" in workflow.missing_requirements


def test_comfyui_video_output_refs_use_manifest_output_node_and_video_extensions() -> None:
    history_item = {
        "outputs": {
            "82": {"images": [{"filename": "preview.png", "subfolder": "", "type": "output"}]},
            "83": {
                "videos": [{"filename": "final.mp4", "subfolder": "run", "type": "output"}],
                "images": [{"filename": "poster.png", "subfolder": "run", "type": "output"}],
            },
            "99": {"videos": [{"filename": "other.mp4", "subfolder": "", "type": "output"}]},
        }
    }

    refs = ComfyUIVideoGenerationProvider._output_file_refs(
        history_item,
        ["83"],
        ["videos", "files", "gifs", "images"],
        ["mp4", "webm", "mov", "gif"],
    )

    assert refs == [{"filename": "final.mp4", "subfolder": "run", "type": "output"}]


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


def test_video_workflow_missing_loader_model_is_unavailable(
    migrated_client: TestClient,
    monkeypatch,
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "video_missing_model.manifest.json").write_text(
        """
        {
          "schema_version": 1,
          "workflow_id": "video_missing_model",
          "display_name": "Missing Model Workflow",
          "version": "test",
          "workflow_file": "video_missing_model.json",
          "provider": "comfyui",
          "required_node_types": ["LoadImage", "UNETLoader", "SaveVideo"],
          "input_image_binding": {"node_id": "1", "input_name": "image"},
          "output_node_ids": ["3"],
          "output_file_keys": ["videos"],
          "allowed_output_extensions": ["mp4"]
        }
        """,
        encoding="utf-8",
    )
    (workflow_dir / "video_missing_model.json").write_text(
        """
        {
          "1": {"class_type": "LoadImage", "inputs": {"image": ""}},
          "2": {"class_type": "UNETLoader", "inputs": {"unet_name": "missing_wan.safetensors"}},
          "3": {"class_type": "SaveVideo", "inputs": {}}
        }
        """,
        encoding="utf-8",
    )
    enable_video_generation(monkeypatch, workflow_dir)
    StubVideoProvider.object_info_override = {
        "LoadImage": {},
        "SaveVideo": {},
        "UNETLoader": {"input": {"required": {"unet_name": [["available_wan.safetensors"]]}}},
    }
    data = create_ready_shot_fixture(migrated_client)

    response = migrated_client.get(f"/api/projects/{data['project_id']}/video-workflows")

    assert response.status_code == 200
    workflow = response.json()["items"][0]
    assert workflow["workflow_id"] == "video_missing_model"
    assert workflow["available"] is False
    assert (
        "model_file_missing:UNETLoader.unet_name:missing_wan.safetensors"
        in workflow["missing_requirements"]
    )


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
    assert updated.json()["inputs"][0]["role"] == "start_frame"
    assert updated.json()["inputs"][0]["media_asset"]["content_url"].startswith("/api/media/")
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
    assert "_start_frame." in StubVideoProvider.submitted_workflow["1"]["inputs"]["image"]
    assert StubVideoProvider.output_node_ids == ["4"]
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


def test_first_last_frame_task_requires_end_frame_and_snapshots_inputs(
    migrated_client: TestClient,
    monkeypatch,
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    write_first_last_video_workflow_files(workflow_dir)
    enable_video_generation(monkeypatch, workflow_dir)
    data = create_ready_shot_fixture(migrated_client)
    start_frame = upload_video_input(migrated_client, data["project_id"])
    end_frame = upload_video_input(migrated_client, data["project_id"])
    task = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/video-tasks",
        json={
            "inputs": [{"role": "start_frame", "media_asset_id": start_frame["id"]}],
        },
    ).json()
    patched = migrated_client.patch(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}",
        json={
            "prompt": "rainy street from first frame to final frame",
            "seed": 0,
            "workflow_id": "video_flf2v_test",
        },
    )
    assert patched.status_code == 200

    missing_end = migrated_client.post(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}/mark-ready"
    )
    assert missing_end.status_code == 422
    assert "missing_end_frame" in missing_end.json()["error"]["details"]["blocking_issues"]

    same_frame = migrated_client.patch(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}",
        json={
            "inputs": [
                {"role": "start_frame", "media_asset_id": start_frame["id"]},
                {"role": "end_frame", "media_asset_id": start_frame["id"]},
            ]
        },
    )
    assert same_frame.status_code == 200
    assert "same_start_and_end_frame" in same_frame.json()["readiness"]["warnings"]

    with_end = migrated_client.patch(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}",
        json={
            "inputs": [
                {"role": "start_frame", "media_asset_id": start_frame["id"]},
                {"role": "end_frame", "media_asset_id": end_frame["id"]},
            ]
        },
    )
    assert with_end.status_code == 200
    ready = migrated_client.post(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}/mark-ready"
    )
    assert ready.status_code == 200

    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}/runs",
        json={"workflow_id": "video_flf2v_test"},
    )
    run_id = response.json()["run_id"]
    run = migrated_client.get(f"/api/projects/{data['project_id']}/video-runs/{run_id}").json()
    snapshot = run["submitted_payload_snapshot"]

    assert response.status_code == 202
    assert snapshot["schema_version"] == 2
    assert snapshot["workflow_mode"] == "first_last_frame_to_video"
    assert snapshot["inputs"] == [
        {"role": "start_frame", "media_asset_id": start_frame["id"]},
        {"role": "end_frame", "media_asset_id": end_frame["id"]},
    ]
    assert len(StubVideoProvider.uploaded_filenames) == 2
    assert any("_start_frame." in filename for filename in StubVideoProvider.uploaded_filenames)
    assert any("_end_frame." in filename for filename in StubVideoProvider.uploaded_filenames)
    assert StubVideoProvider.submitted_workflow is not None
    assert "_start_frame." in StubVideoProvider.submitted_workflow["1"]["inputs"]["image"]
    assert "_end_frame." in StubVideoProvider.submitted_workflow["5"]["inputs"]["image"]


def test_wan_first_last_workflow_run_uses_manifest_nodes_and_saves_video(
    migrated_client: TestClient,
    monkeypatch,
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    write_wan_workflow_files(workflow_dir)
    enable_video_generation(monkeypatch, workflow_dir)
    data = create_ready_shot_fixture(migrated_client)
    start_frame = upload_video_input(migrated_client, data["project_id"])
    end_frame = upload_video_input(migrated_client, data["project_id"])
    task = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/video-tasks",
        json={
            "inputs": [
                {"role": "start_frame", "media_asset_id": start_frame["id"]},
                {"role": "end_frame", "media_asset_id": end_frame["id"]},
            ]
        },
    ).json()
    patch = migrated_client.patch(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}",
        json={
            "prompt": "fixed seed first last frame test",
            "negative_prompt": "bad quality",
            "duration_seconds": 2,
            "fps": 16,
            "width": 640,
            "height": 640,
            "seed": 321,
            "workflow_id": WAN_WORKFLOW_ID,
        },
    )
    ready = migrated_client.post(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}/mark-ready"
    )

    assert patch.status_code == 200
    assert ready.status_code == 200
    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}/runs",
        json={"workflow_id": WAN_WORKFLOW_ID},
    )
    run_id = response.json()["run_id"]
    asyncio.run(VideoGenerationRunner().run_task(run_id))
    refreshed = migrated_client.get(
        f"/api/projects/{data['project_id']}/video-runs/{run_id}"
    ).json()

    assert response.status_code == 202
    assert refreshed["status"] == "completed"
    assert refreshed["outputs"][0]["media_asset"]["media_type"] == "video"
    assert StubVideoProvider.output_node_ids == ["83"]
    assert StubVideoProvider.submitted_workflow is not None
    workflow = StubVideoProvider.submitted_workflow
    assert "_start_frame." in workflow["80"]["inputs"]["image"]
    assert "_end_frame." in workflow["89"]["inputs"]["image"]
    assert workflow["90"]["inputs"]["text"] == "fixed seed first last frame test"
    assert workflow["78"]["inputs"]["text"] == "bad quality"
    assert workflow["81"]["inputs"]["width"] == 640
    assert workflow["81"]["inputs"]["height"] == 640
    assert workflow["81"]["inputs"]["length"] == 33
    assert workflow["86"]["inputs"]["fps"] == 16
    assert workflow["84"]["inputs"]["noise_seed"] == 321
    assert workflow["87"]["inputs"]["noise_seed"] == 0
    assert workflow["87"]["inputs"]["add_noise"] == "disable"


def test_first_last_frame_runner_does_not_submit_when_role_upload_fails(
    migrated_client: TestClient,
    monkeypatch,
    tmp_path: Path,
) -> None:
    workflow_dir = tmp_path / "workflows"
    write_first_last_video_workflow_files(workflow_dir)
    enable_video_generation(monkeypatch, workflow_dir)
    data = create_ready_shot_fixture(migrated_client)
    start_frame = upload_video_input(migrated_client, data["project_id"])
    end_frame = upload_video_input(migrated_client, data["project_id"])
    task = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/video-tasks",
        json={
            "inputs": [
                {"role": "start_frame", "media_asset_id": start_frame["id"]},
                {"role": "end_frame", "media_asset_id": end_frame["id"]},
            ]
        },
    ).json()
    migrated_client.patch(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}",
        json={
            "prompt": "rainy street",
            "seed": 0,
            "workflow_id": "video_flf2v_test",
        },
    )
    ready = migrated_client.post(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}/mark-ready"
    )
    assert ready.status_code == 200
    StubVideoProvider.fail_upload_role = "end_frame"

    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}/runs",
        json={"workflow_id": "video_flf2v_test"},
    )
    run_id = response.json()["run_id"]
    run = migrated_client.get(f"/api/projects/{data['project_id']}/video-runs/{run_id}").json()

    assert response.status_code == 202
    assert run["status"] == "failed"
    assert run["error_code"] == "video_reference_upload_failed"
    assert StubVideoProvider.submitted_workflow is None


def test_video_task_input_validation_is_transactional(
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
        json={"inputs": [{"role": "start_frame", "media_asset_id": media_asset["id"]}]},
    ).json()

    duplicate = migrated_client.patch(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}",
        json={
            "inputs": [
                {"role": "start_frame", "media_asset_id": media_asset["id"]},
                {"role": "start_frame", "media_asset_id": media_asset["id"]},
            ]
        },
    )
    refreshed = migrated_client.get(
        f"/api/projects/{data['project_id']}/video-tasks/{task['id']}"
    ).json()

    assert duplicate.status_code == 422
    assert duplicate.json()["error"]["code"] == "video_input_role_duplicate"
    assert refreshed["inputs"] == task["inputs"]
