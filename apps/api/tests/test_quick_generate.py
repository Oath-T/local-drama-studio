import json

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.infrastructure.database import get_session_factory
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.keyframe_generation import (
    KeyframeGenerationOutputRecord,
    KeyframeGenerationRunRecord,
)
from app.infrastructure.models.project_canvas import (
    ProjectCanvasEdgeRecord,
    ProjectCanvasNodeRecord,
)
from app.infrastructure.models.quick_generate import QuickGenerateRequestRecord
from app.infrastructure.models.video_generation import (
    VideoGenerationRunRecord,
    VideoGenerationTaskInputRecord,
    VideoGenerationTaskRecord,
)
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


def adopt_output_for_run(run_id: str) -> str:
    with get_session_factory()() as session:
        output = session.scalars(
            select(KeyframeGenerationOutputRecord).where(
                KeyframeGenerationOutputRecord.run_id == run_id
            )
        ).first()
        assert output is not None
        output.is_selected = True
        session.commit()
        return output.id


def prepare_adopted_video_inputs(
    client: TestClient,
    project_id: str,
    shot_id: str,
    suffix: str,
) -> tuple[str, str]:
    url = f"/api/projects/{project_id}/shots/{shot_id}/quick-generate"
    first = client.post(
        url,
        json={
            "mode": "first_frame",
            "prompt": "A dramatic first frame",
            "request_id": f"first-{suffix}",
        },
    )
    end = client.post(
        url,
        json={
            "mode": "end_frame",
            "prompt": "A dramatic end frame",
            "request_id": f"end-{suffix}",
        },
    )
    return adopt_output_for_run(first.json()["run_id"]), adopt_output_for_run(end.json()["run_id"])


def test_preview_is_read_only(migrated_client: TestClient, monkeypatch) -> None:
    enable_generation(monkeypatch)
    enable_video_generation(monkeypatch)
    data = create_ready_shot_fixture(migrated_client)
    prompt = '中文 Prompt：人物自然呼吸，"稳定镜头"，路径符号 \\ 不应损坏。🙂'
    negative_prompt = "切镜，水印，文字，面部变化。"

    response = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate/preview",
        json={
            "mode": "first_frame",
            "prompt": prompt,
            "negative_prompt": negative_prompt,
        },
    )

    assert response.status_code == 200
    assert response.json()["route"]["selected_workflow_id"] == "keyframe_basic_v1"
    assert response.json()["submitted_prompt"] == prompt
    assert response.json()["submitted_negative_prompt"] == negative_prompt
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
    video_capability = next(
        item
        for item in response.json()["capabilities"]
        if item["workflow_id"] == "video_wan22_14b_flf2v_v1"
    )
    assert route["executable"] is False
    assert video_capability["available"] is False
    assert video_capability["checked_at"] is not None
    assert video_capability["blockers"] == video_capability["missing_requirements"]
    assert any(item.startswith("model_file_missing:") for item in route["missing_models"])


def test_video_quick_generate_uses_adopted_first_and_end_frame_outputs(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_generation(monkeypatch)
    enable_video_generation(monkeypatch)
    data = create_ready_shot_fixture(migrated_client)
    url = f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate"
    first = migrated_client.post(
        url,
        json={"mode": "first_frame", "prompt": "A dramatic first frame", "request_id": "first-1"},
    )
    end = migrated_client.post(
        url,
        json={"mode": "end_frame", "prompt": "A dramatic end frame", "request_id": "end-1"},
    )
    first_output_id = adopt_output_for_run(first.json()["run_id"])
    end_output_id = adopt_output_for_run(end.json()["run_id"])

    preview = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate/preview",
        json={"mode": "video", "prompt": "create the video"},
    )
    response = migrated_client.post(
        url,
        json={"mode": "video", "prompt": "create the video", "request_id": "video-1"},
    )

    assert preview.status_code == 200
    route = preview.json()["route"]
    assert route["executable"] is True
    assert route["missing_inputs"] == []
    assert route["missing_models"] == []
    assert preview.json()["can_execute"] is True
    assert preview.json()["blockers"] == []
    assert preview.json()["capability"]["available"] is True
    assert preview.json()["capability"]["blockers"] == []
    assert preview.json()["capability"]["checked_at"] is not None
    assert preview.json()["workflow_id"] == "video_wan22_14b_flf2v_v1"
    assert preview.json()["resolved_inputs"]["start_frame_media_asset_id"] is not None
    assert preview.json()["resolved_inputs"]["end_frame_media_asset_id"] is not None
    assert preview.json()["resolved_inputs"]["start_frame_available"] is True
    assert preview.json()["resolved_inputs"]["end_frame_available"] is True
    assert preview.json()["resolved_parameters"] == {
        "width": 320,
        "height": 576,
        "frame_count": 17,
        "fps": 8,
        "seed": None,
        "expected_duration": 2.125,
    }
    assert preview.json()["estimated_output"]["media_type"] == "video"
    assert "low_resolution_preset" in preview.json()["warnings"]
    assert "no_negative_prompt" in preview.json()["warnings"]
    assert response.status_code == 202
    assert response.json()["run_type"] == "video"
    with get_session_factory()() as session:
        run = session.get(VideoGenerationRunRecord, response.json()["run_id"])
        assert run is not None
        snapshot = json.loads(run.submitted_payload_snapshot)
        assert snapshot["project_id"] == data["project_id"]
        assert snapshot["shot_id"] == str(data["shot"]["id"])
        assert snapshot["request_id"] == "video-1"
        assert snapshot["prompt"] == "create the video"
        assert snapshot["width"] == 320
        assert snapshot["height"] == 576
        assert snapshot["fps"] == 8
        assert snapshot["frame_count"] == 17
        assert snapshot["start_frame_media_asset_id"] is not None
        assert snapshot["end_frame_media_asset_id"] is not None
        run.status = "running"
        session.commit()
    active_preview = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate/preview",
        json={"mode": "video", "prompt": "create the video"},
    )
    assert active_preview.status_code == 200
    assert active_preview.json()["can_execute"] is False
    assert "active_run_exists" in active_preview.json()["blockers"]
    assert active_preview.json()["active_run"]["run_id"] == response.json()["run_id"]
    with get_session_factory()() as session:
        inputs = list(session.scalars(select(VideoGenerationTaskInputRecord)).all())
    source_by_role = {record.role: record.source_keyframe_output_id for record in inputs}
    assert source_by_role["start_frame"] == first_output_id
    assert source_by_role["end_frame"] == end_output_id
    with get_session_factory()() as session:
        task = session.get(VideoGenerationTaskRecord, response.json()["task_id"])
        assert task is not None
        assert task.width == 320
        assert task.height == 576
        assert task.fps == 8
        assert task.duration_seconds == 2.0


def test_video_quick_generate_accepts_standard_preset_fps_and_seed(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_generation(monkeypatch)
    enable_video_generation(monkeypatch)
    data = create_ready_shot_fixture(migrated_client)
    url = f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate"
    first = migrated_client.post(
        url,
        json={"mode": "first_frame", "prompt": "A dramatic first frame", "request_id": "first-p"},
    )
    end = migrated_client.post(
        url,
        json={"mode": "end_frame", "prompt": "A dramatic end frame", "request_id": "end-p"},
    )
    adopt_output_for_run(first.json()["run_id"])
    adopt_output_for_run(end.json()["run_id"])

    response = migrated_client.post(
        url,
        json={
            "mode": "video",
            "prompt": "create the video",
            "request_id": "video-preset",
            "duration_preset": "standard_short",
            "fps": 12,
            "seed": 7002,
        },
    )

    assert response.status_code == 202
    with get_session_factory()() as session:
        task = session.get(VideoGenerationTaskRecord, response.json()["task_id"])
        assert task is not None
        assert task.width == 320
        assert task.height == 576
        assert task.fps == 12
        assert task.duration_seconds == 4.0
        assert task.seed == 7002


def test_video_quick_generate_request_id_is_idempotent(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_generation(monkeypatch)
    enable_video_generation(monkeypatch)
    data = create_ready_shot_fixture(migrated_client)
    project_id = data["project_id"]
    shot_id = str(data["shot"]["id"])
    prepare_adopted_video_inputs(migrated_client, project_id, shot_id, "idem")
    url = f"/api/projects/{project_id}/shots/{shot_id}/quick-generate"
    payload = {"mode": "video", "prompt": "create the video", "request_id": "video-idem"}

    first = migrated_client.post(url, json=payload)
    second = migrated_client.post(url, json=payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["idempotent_replay"] is True
    assert second.json()["run_id"] == first.json()["run_id"]
    with get_session_factory()() as session:
        assert session.query(VideoGenerationRunRecord).count() == 1


def test_video_quick_generate_reuses_active_run_for_different_request_id(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_generation(monkeypatch)
    enable_video_generation(monkeypatch)
    data = create_ready_shot_fixture(migrated_client)
    project_id = data["project_id"]
    shot_id = str(data["shot"]["id"])
    prepare_adopted_video_inputs(migrated_client, project_id, shot_id, "active")
    url = f"/api/projects/{project_id}/shots/{shot_id}/quick-generate"
    first = migrated_client.post(
        url,
        json={"mode": "video", "prompt": "create the video", "request_id": "video-active-a"},
    )
    with get_session_factory()() as session:
        run = session.get(VideoGenerationRunRecord, first.json()["run_id"])
        assert run is not None
        run.status = "running"
        session.commit()

    second = migrated_client.post(
        url,
        json={"mode": "video", "prompt": "create the video", "request_id": "video-active-b"},
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["reused_active_run"] is True
    assert second.json()["run_id"] == first.json()["run_id"]
    with get_session_factory()() as session:
        assert session.query(VideoGenerationRunRecord).count() == 1


def test_video_quick_generate_allows_new_run_after_terminal_run(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_generation(monkeypatch)
    enable_video_generation(monkeypatch)
    data = create_ready_shot_fixture(migrated_client)
    project_id = data["project_id"]
    shot_id = str(data["shot"]["id"])
    prepare_adopted_video_inputs(migrated_client, project_id, shot_id, "terminal")
    url = f"/api/projects/{project_id}/shots/{shot_id}/quick-generate"
    first = migrated_client.post(
        url,
        json={"mode": "video", "prompt": "create the video", "request_id": "video-terminal-a"},
    )
    with get_session_factory()() as session:
        run = session.get(VideoGenerationRunRecord, first.json()["run_id"])
        assert run is not None
        run.status = "failed"
        session.commit()
    second = migrated_client.post(
        url,
        json={"mode": "video", "prompt": "create the video", "request_id": "video-terminal-b"},
    )
    with get_session_factory()() as session:
        second_run = session.get(VideoGenerationRunRecord, second.json()["run_id"])
        assert second_run is not None
        second_run.status = "completed"
        session.commit()
    third = migrated_client.post(
        url,
        json={"mode": "video", "prompt": "create the video", "request_id": "video-terminal-c"},
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert third.status_code == 202
    assert len({first.json()["run_id"], second.json()["run_id"], third.json()["run_id"]}) == 3
    with get_session_factory()() as session:
        assert session.query(VideoGenerationRunRecord).count() == 3


def test_video_preview_rejects_duplicate_adopted_keyframe_outputs(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_generation(monkeypatch)
    enable_video_generation(monkeypatch)
    data = create_ready_shot_fixture(migrated_client)
    url = f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate"
    first_a = migrated_client.post(
        url,
        json={"mode": "first_frame", "prompt": "A dramatic first frame", "request_id": "first-a"},
    )
    first_b = migrated_client.post(
        url,
        json={"mode": "first_frame", "prompt": "Another first frame", "request_id": "first-b"},
    )
    end = migrated_client.post(
        url,
        json={"mode": "end_frame", "prompt": "A dramatic end frame", "request_id": "end-a"},
    )
    adopt_output_for_run(first_a.json()["run_id"])
    adopt_output_for_run(first_b.json()["run_id"])
    adopt_output_for_run(end.json()["run_id"])

    preview = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate/preview",
        json={"mode": "video", "prompt": "create the video"},
    )

    assert preview.status_code == 200
    route = preview.json()["route"]
    assert route["executable"] is False
    assert "multiple_adopted_first_frame" in route["missing_inputs"]
    assert "ambiguous_adopted_start_frame" in preview.json()["blockers"]


def test_video_preview_rejects_adopted_keyframe_with_missing_file(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_generation(monkeypatch)
    enable_video_generation(monkeypatch)
    data = create_ready_shot_fixture(migrated_client)
    url = f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate"
    first = migrated_client.post(
        url,
        json={"mode": "first_frame", "prompt": "A dramatic first frame", "request_id": "first-x"},
    )
    end = migrated_client.post(
        url,
        json={"mode": "end_frame", "prompt": "A dramatic end frame", "request_id": "end-x"},
    )
    first_output_id = adopt_output_for_run(first.json()["run_id"])
    adopt_output_for_run(end.json()["run_id"])
    with get_session_factory()() as session:
        output = session.get(KeyframeGenerationOutputRecord, first_output_id)
        assert output is not None
        media_asset = session.get(MediaAssetRecord, output.media_asset_id)
        assert media_asset is not None
        media_asset.relative_path = "generated-keyframes/missing-file.png"
        session.commit()

    preview = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate/preview",
        json={"mode": "video", "prompt": "create the video"},
    )

    assert preview.status_code == 200
    route = preview.json()["route"]
    assert route["executable"] is False
    assert "adopted_first_frame_file_missing" in route["missing_inputs"]
    assert "start_frame_file_missing" in preview.json()["blockers"]


def test_video_preview_warns_for_stale_media_metadata_without_blocking(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_generation(monkeypatch)
    enable_video_generation(monkeypatch)
    data = create_ready_shot_fixture(migrated_client)
    url = f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate"
    first = migrated_client.post(
        url,
        json={"mode": "first_frame", "prompt": "A dramatic first frame", "request_id": "first-s"},
    )
    end = migrated_client.post(
        url,
        json={"mode": "end_frame", "prompt": "A dramatic end frame", "request_id": "end-s"},
    )
    first_output_id = adopt_output_for_run(first.json()["run_id"])
    adopt_output_for_run(end.json()["run_id"])
    with get_session_factory()() as session:
        output = session.get(KeyframeGenerationOutputRecord, first_output_id)
        assert output is not None
        media_asset = session.get(MediaAssetRecord, output.media_asset_id)
        assert media_asset is not None
        media_asset.sha256 = "0" * 64
        media_asset.size_bytes = media_asset.size_bytes + 10
        session.commit()

    preview = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/quick-generate/preview",
        json={"mode": "video", "prompt": "create the video"},
    )

    assert preview.status_code == 200
    route = preview.json()["route"]
    assert route["executable"] is True
    assert route["missing_inputs"] == []
    assert "media_metadata_stale" in route["warnings"]


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
