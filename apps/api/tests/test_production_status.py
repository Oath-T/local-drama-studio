from datetime import UTC, datetime
from uuid import uuid4

from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from alembic import command
from app.infrastructure.database import get_session_factory
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.keyframe_generation import (
    KeyframeGenerationOutputRecord,
    KeyframeGenerationRunRecord,
)
from app.infrastructure.models.video_generation import (
    VideoGenerationOutputRecord,
    VideoGenerationRunRecord,
)
from tests.test_keyframe_tasks import create_keyframe_task, create_ready_shot_fixture
from tests.test_prompt_builder import table_counts


def test_keyframe_task_purpose_migration_backfills_historical_names() -> None:
    command.upgrade(Config("alembic.ini"), "20260704_0500")
    now = datetime(2026, 7, 14, tzinfo=UTC).isoformat()
    project_id = str(uuid4())
    shot_id = str(uuid4())
    with get_session_factory()() as session:
        session.execute(
            text(
                """
                INSERT INTO projects (
                    id, name, aspect_ratio, default_language, default_fps, created_at, updated_at
                )
                VALUES (:project_id, 'Migration Project', '9:16', 'zh-CN', 24, :now, :now)
                """
            ),
            {"project_id": project_id, "now": now},
        )
        session.execute(
            text(
                """
                INSERT INTO shots (
                    id, project_id, name, order_index, shot_scale, camera_height, camera_angle,
                    composition_type, camera_movement, created_at, updated_at
                )
                VALUES (
                    :shot_id, :project_id, 'Shot', 1, 'medium', 'eye_level', 'front',
                    'centered', 'static', :now, :now
                )
                """
            ),
            {"shot_id": shot_id, "project_id": project_id, "now": now},
        )
        for name in ("首帧草稿 - Shot", "尾帧草稿 - Shot", "其他任务"):
            session.execute(
                text(
                    """
                    INSERT INTO keyframe_generation_tasks (
                        id, project_id, shot_id, name, status, shot_snapshot,
                        source_shot_updated_at, prompt_zh, aspect_ratio, width, height,
                        steps, guidance_scale, output_count, created_at, updated_at
                    )
                    VALUES (
                        :id, :project_id, :shot_id, :name, 'draft', :snapshot,
                        :now, 'prompt', '9:16', 768, 1360, 30, 7.0, 1, :now, :now
                    )
                    """
                ),
                {
                    "id": str(uuid4()),
                    "project_id": project_id,
                    "shot_id": shot_id,
                    "name": name,
                    "snapshot": (
                        '{"schema_version":1,"shot_id":"x","order_index":1,'
                        '"title":"x","shot_scale":"medium","camera_angle":"front",'
                        '"camera_height":"eye_level","composition_type":"centered",'
                        '"camera_movement":"static","characters":[]}'
                    ),
                    "now": now,
                },
            )
        session.commit()

    command.upgrade(Config("alembic.ini"), "head")

    with get_session_factory()() as session:
        rows = dict(
            session.execute(text("SELECT name, purpose FROM keyframe_generation_tasks")).all()
        )
    assert rows["首帧草稿 - Shot"] == "first_frame"
    assert rows["尾帧草稿 - Shot"] == "end_frame"
    assert rows["其他任务"] == "concept"

    command.downgrade(Config("alembic.ini"), "20260704_0500")
    with get_session_factory()() as session:
        columns = [
            row[1]
            for row in session.execute(text("PRAGMA table_info(keyframe_generation_tasks)")).all()
        ]
    assert "purpose" not in columns


def test_keyframe_task_purpose_create_update_and_generation_summary(
    migrated_client: TestClient,
) -> None:
    data = create_ready_shot_fixture(migrated_client)
    first = create_keyframe_task(
        migrated_client,
        data["project_id"],
        str(data["shot"]["id"]),
        copy_current_references=False,
    )
    end = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/keyframe-tasks",
        json={"purpose": "end_frame", "copy_current_references": False},
    ).json()
    updated = migrated_client.patch(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{first['id']}",
        json={"purpose": "first_frame"},
    )
    summary = migrated_client.get(f"/api/projects/{data['project_id']}/generation-tasks")

    assert first["purpose"] == "concept"
    assert end["purpose"] == "end_frame"
    assert updated.status_code == 200
    assert updated.json()["purpose"] == "first_frame"
    items = {item["task_id"]: item for item in summary.json()["items"]}
    assert items[first["id"]]["task_purpose"] == "first_frame"
    assert items[end["id"]]["task_purpose"] == "end_frame"


def test_shot_production_status_empty_and_asset_blockers(migrated_client: TestClient) -> None:
    project = migrated_client.post("/api/projects", json={"name": "Production"}).json()
    shot = migrated_client.post(
        f"/api/projects/{project['id']}/shots", json={"name": "Empty Shot"}
    ).json()

    response = migrated_client.get(
        f"/api/projects/{project['id']}/shots/{shot['id']}/production-status"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_status"] == "blocked"
    assert payload["steps"]["assets"]["status"] == "missing"
    assert "complete_assets" in payload["next_actions"]
    assert payload["steps"]["director_prompt"]["director_template_available"] is True


def test_production_status_frames_video_adoption_and_continuity(
    migrated_client: TestClient,
) -> None:
    first_shot = create_ready_shot_fixture(migrated_client)
    project_id = first_shot["project_id"]
    second_shot = migrated_client.post(
        f"/api/projects/{project_id}/shots",
        json={
            "name": "Shot 2",
            "scene_id": first_shot["scene"]["id"],
            "scene_state_id": first_shot["state"]["id"],
        },
    ).json()
    first_task = _create_keyframe_task_with_selected_output(
        migrated_client, project_id, str(first_shot["shot"]["id"]), "first_frame", True
    )
    end_task = _create_keyframe_task_with_selected_output(
        migrated_client, project_id, str(first_shot["shot"]["id"]), "end_frame", True
    )
    _create_video_task_with_selected_output(
        migrated_client,
        project_id,
        str(first_shot["shot"]["id"]),
        first_task["output_id"],
        end_task["output_id"],
        True,
    )

    response = migrated_client.get(
        f"/api/projects/{project_id}/shots/{first_shot['shot']['id']}/production-status"
    )
    second_response = migrated_client.get(
        f"/api/projects/{project_id}/shots/{second_shot['id']}/production-status"
    )
    project_response = migrated_client.get(f"/api/projects/{project_id}/production-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_status"] == "completed"
    assert payload["steps"]["first_frame"]["status"] == "adopted"
    assert payload["steps"]["end_frame"]["status"] == "adopted"
    assert payload["steps"]["video"]["status"] == "adopted"
    assert payload["steps"]["video"]["has_start_frame"] is True
    assert payload["steps"]["video"]["has_end_frame"] is True
    assert second_response.json()["continuity_candidate"]["source"] == "adopted_video"
    assert project_response.json()["summary"]["completed"] == 1
    assert len(project_response.json()["shots"]) == 2


def test_production_status_uses_only_selected_outputs_and_is_read_only(
    migrated_client: TestClient,
) -> None:
    data = create_ready_shot_fixture(migrated_client)
    project_id = data["project_id"]
    before = table_counts()
    _create_keyframe_task_with_selected_output(
        migrated_client, project_id, str(data["shot"]["id"]), "first_frame", False
    )

    response = migrated_client.get(
        f"/api/projects/{project_id}/shots/{data['shot']['id']}/production-status"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["steps"]["first_frame"]["status"] == "completed"
    assert payload["steps"]["first_frame"]["adopted_output_id"] is None
    assert "select_first_frame_output" in payload["next_actions"]
    assert table_counts()["keyframe_tasks"] == before["keyframe_tasks"] + 1
    assert table_counts()["keyframe_outputs"] == before["keyframe_outputs"] + 1


def test_production_status_cross_project_access_fails(migrated_client: TestClient) -> None:
    first = create_ready_shot_fixture(migrated_client)
    second = migrated_client.post("/api/projects", json={"name": "Other"}).json()

    response = migrated_client.get(
        f"/api/projects/{second['id']}/shots/{first['shot']['id']}/production-status"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SHOT_NOT_FOUND"


def _create_keyframe_task_with_selected_output(
    client: TestClient,
    project_id: str,
    shot_id: str,
    purpose: str,
    selected: bool,
) -> dict[str, str]:
    task = client.post(
        f"/api/projects/{project_id}/shots/{shot_id}/keyframe-tasks",
        json={"purpose": purpose, "copy_current_references": False},
    ).json()
    media_id = _create_media_asset(project_id, "image")
    now = datetime.now(UTC)
    run_id = str(uuid4())
    output_id = str(uuid4())
    with get_session_factory()() as session:
        session.add(
            KeyframeGenerationRunRecord(
                id=run_id,
                project_id=project_id,
                keyframe_task_id=task["id"],
                run_number=1,
                provider="comfyui",
                workflow_id="keyframe_basic_v1",
                workflow_version="1",
                status="completed",
                submitted_payload_snapshot="{}",
                completed_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            KeyframeGenerationOutputRecord(
                id=output_id,
                project_id=project_id,
                run_id=run_id,
                media_asset_id=media_id,
                output_index=1,
                provider_filename="output.png",
                provider_subfolder="",
                width=768,
                height=1360,
                seed=1,
                is_selected=selected,
                created_at=now,
            )
        )
        session.commit()
    return {"task_id": task["id"], "output_id": output_id, "media_asset_id": media_id}


def _create_video_task_with_selected_output(
    client: TestClient,
    project_id: str,
    shot_id: str,
    start_output_id: str,
    end_output_id: str,
    selected: bool,
) -> dict[str, str]:
    start_media = _media_id_for_keyframe_output(start_output_id)
    end_media = _media_id_for_keyframe_output(end_output_id)
    task = client.post(
        f"/api/projects/{project_id}/shots/{shot_id}/video-tasks",
        json={
            "inputs": [
                {
                    "role": "start_frame",
                    "media_asset_id": start_media,
                    "source_keyframe_output_id": start_output_id,
                },
                {
                    "role": "end_frame",
                    "media_asset_id": end_media,
                    "source_keyframe_output_id": end_output_id,
                },
            ]
        },
    ).json()
    media_id = _create_media_asset(project_id, "video")
    now = datetime.now(UTC)
    run_id = str(uuid4())
    output_id = str(uuid4())
    with get_session_factory()() as session:
        session.add(
            VideoGenerationRunRecord(
                id=run_id,
                project_id=project_id,
                video_task_id=task["id"],
                run_number=1,
                provider="comfyui",
                workflow_id="video_wan22_14b_flf2v_v1",
                workflow_version="1",
                status="completed",
                submitted_payload_snapshot="{}",
                completed_at=now,
                created_at=now,
                updated_at=now,
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
                duration_seconds=2,
                fps=16,
                seed=1,
                is_selected=selected,
                created_at=now,
            )
        )
        session.commit()
    return {"task_id": task["id"], "output_id": output_id, "media_asset_id": media_id}


def _create_media_asset(project_id: str, media_type: str) -> str:
    now = datetime.now(UTC)
    media_id = str(uuid4())
    extension = ".mp4" if media_type == "video" else ".png"
    mime_type = "video/mp4" if media_type == "video" else "image/png"
    with get_session_factory()() as session:
        session.add(
            MediaAssetRecord(
                id=media_id,
                project_id=project_id,
                media_type=media_type,
                original_filename=f"generated{extension}",
                stored_filename=f"{media_id}{extension}",
                relative_path=f"projects/{project_id}/generated/{media_id}{extension}",
                mime_type=mime_type,
                extension=extension,
                size_bytes=128,
                width=640,
                height=640,
                sha256=media_id.replace("-", ""),
                created_at=now,
            )
        )
        session.commit()
    return media_id


def _media_id_for_keyframe_output(output_id: str) -> str:
    with get_session_factory()() as session:
        output = session.get(KeyframeGenerationOutputRecord, output_id)
        assert output is not None
        return output.media_asset_id
