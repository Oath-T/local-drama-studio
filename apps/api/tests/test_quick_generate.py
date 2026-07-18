from fastapi.testclient import TestClient
from sqlalchemy import select

from app.infrastructure.database import get_session_factory
from app.infrastructure.models.keyframe_generation import (
    KeyframeGenerationOutputRecord,
    KeyframeGenerationRunRecord,
)
from app.infrastructure.models.project_canvas import (
    ProjectCanvasEdgeRecord,
    ProjectCanvasNodeRecord,
)
from app.infrastructure.models.quick_generate import QuickGenerateRequestRecord
from app.infrastructure.models.video_generation import VideoGenerationRunRecord
from tests.test_keyframe_generation import enable_generation
from tests.test_keyframe_tasks import (
    bind_shot_character,
    create_character,
    create_look,
    create_project,
    create_ready_shot_fixture,
    create_shot,
)
from tests.test_video_generation import StubVideoProvider, enable_video_generation


def test_preview_is_read_only(migrated_client: TestClient, monkeypatch) -> None:
    enable_generation(monkeypatch)
    enable_video_generation(monkeypatch)
    data = create_ready_shot_fixture(migrated_client)

    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate/preview",
        json={"mode": "first_frame", "prompt": "A dramatic first frame"},
    )

    assert response.status_code == 200
    assert response.json()["route"]["selected_workflow_id"] == "keyframe_basic_v1"
    with get_session_factory()() as session:
        assert session.query(QuickGenerateRequestRecord).count() == 0
        assert session.query(KeyframeGenerationRunRecord).count() == 0
        assert session.query(VideoGenerationRunRecord).count() == 0


def test_video_preview_reports_missing_wan_models(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_generation(monkeypatch)
    enable_video_generation(monkeypatch)
    StubVideoProvider.object_info_override = {
        "CLIPLoader": {"input": {"required": {"clip_name": [[]]}}},
        "CLIPTextEncode": {},
        "CreateVideo": {},
        "KSamplerAdvanced": {},
        "LoadImage": {},
        "SaveVideo": {},
        "UNETLoader": {"input": {"required": {"unet_name": [[]]}}},
        "VAEDecode": {},
        "VAELoader": {"input": {"required": {"vae_name": [[]]}}},
        "VideoCombine": {},
        "WanFirstLastFrameToVideo": {},
    }
    data = create_ready_shot_fixture(migrated_client)

    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate/preview",
        json={"mode": "video", "prompt": "move forward"},
    )

    assert response.status_code == 200
    route = response.json()["route"]
    assert route["executable"] is False
    assert any(item.startswith("model_file_missing:") for item in route["missing_models"])


def test_quick_generate_keyframe_is_idempotent_and_not_auto_adopted(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_generation(monkeypatch)
    enable_video_generation(monkeypatch)
    data = create_ready_shot_fixture(migrated_client)
    url = f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate"
    payload = {"mode": "first_frame", "prompt": "A dramatic first frame", "request_id": "req-1"}

    first = migrated_client.post(url, json=payload)
    second = migrated_client.post(url, json=payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["idempotent_replay"] is True
    assert first.json()["run_id"] == second.json()["run_id"]
    with get_session_factory()() as session:
        assert session.query(KeyframeGenerationRunRecord).count() == 1
        output = session.scalars(select(KeyframeGenerationOutputRecord)).first()
        assert output is not None
        assert output.is_selected is False


def test_quick_generate_keyframe_bypasses_legacy_task_readiness(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_generation(monkeypatch)
    enable_video_generation(monkeypatch)
    project = create_project(migrated_client)
    project_id = str(project["id"])
    character = create_character(migrated_client, project_id)
    look = create_look(migrated_client, project_id, str(character["id"]))
    shot = create_shot(migrated_client, project_id)
    bind_shot_character(
        migrated_client,
        project_id,
        str(shot["id"]),
        str(character["id"]),
        str(look["id"]),
    )

    preview = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/quick-generate/preview",
        json={"mode": "first_frame", "prompt": "A dramatic first frame"},
    )
    response = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/quick-generate",
        json={
            "mode": "first_frame",
            "prompt": "A dramatic first frame",
            "request_id": "req-incomplete-shot",
        },
    )

    assert preview.status_code == 200
    assert preview.json()["route"]["executable"] is True
    assert response.status_code == 202
    assert response.json()["run_type"] == "keyframe"
    with get_session_factory()() as session:
        assert session.query(KeyframeGenerationRunRecord).count() == 1
        output = session.scalars(select(KeyframeGenerationOutputRecord)).first()
        assert output is not None
        assert output.is_selected is False


def test_quick_generate_reuses_active_run(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_generation(monkeypatch)
    enable_video_generation(monkeypatch)
    data = create_ready_shot_fixture(migrated_client)
    url = f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate"

    first = migrated_client.post(
        url,
        json={"mode": "first_frame", "prompt": "A dramatic first frame", "request_id": "req-a"},
    )
    with get_session_factory()() as session:
        run = session.scalars(select(KeyframeGenerationRunRecord)).first()
        assert run is not None
        run.status = "running"
        session.commit()
    second = migrated_client.post(
        url,
        json={"mode": "first_frame", "prompt": "A dramatic first frame", "request_id": "req-b"},
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["reused_active_run"] is True
    assert second.json()["run_id"] == first.json()["run_id"]
    with get_session_factory()() as session:
        assert session.query(KeyframeGenerationRunRecord).count() == 1


def test_output_sync_creates_canvas_node_and_generated_from_edge(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_generation(monkeypatch)
    enable_video_generation(monkeypatch)
    data = create_ready_shot_fixture(migrated_client)
    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate",
        json={"mode": "first_frame", "prompt": "A dramatic first frame", "request_id": "req-sync"},
    )

    assert response.status_code == 202
    with get_session_factory()() as session:
        nodes = list(session.scalars(select(ProjectCanvasNodeRecord)).all())
        edges = list(session.scalars(select(ProjectCanvasEdgeRecord)).all())
    assert any(node.node_type == "image" for node in nodes)
    assert any(edge.semantic_type == "generated_from" for edge in edges)


def test_sync_endpoint_is_idempotent(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_generation(monkeypatch)
    enable_video_generation(monkeypatch)
    data = create_ready_shot_fixture(migrated_client)
    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate",
        json={
            "mode": "first_frame",
            "prompt": "A dramatic first frame",
            "request_id": "req-sync-2",
        },
    )
    run_id = response.json()["run_id"]

    first_sync = None
    for _ in range(2):
        sync = migrated_client.post(
            f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate/sync-output",
            json={"run_type": "keyframe", "run_id": run_id},
        )
        assert sync.status_code == 200
        assert sync.json()["synced"] is True
        assert sync.json()["node_id"] is not None
        assert sync.json()["edge_id"] is not None
        if first_sync is None:
            first_sync = sync.json()
        else:
            assert sync.json()["node_id"] == first_sync["node_id"]
            assert sync.json()["edge_id"] == first_sync["edge_id"]
    with get_session_factory()() as session:
        assert session.query(ProjectCanvasEdgeRecord).count() == 1
