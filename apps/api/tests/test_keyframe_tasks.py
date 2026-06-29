from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.infrastructure.database import get_session_factory


def create_project(client: TestClient, name: str = "Sprint 7 Project") -> dict[str, object]:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()


def create_character(client: TestClient, project_id: str, name: str = "Lead") -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/characters",
        json={"name": name, "role_type": "protagonist"},
    )
    assert response.status_code == 201
    return response.json()


def create_look(
    client: TestClient, project_id: str, character_id: str, name: str = "Default Look"
) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/characters/{character_id}/looks",
        json={"name": name},
    )
    assert response.status_code == 201
    return response.json()


def make_image_bytes(color: tuple[int, int, int] = (64, 96, 128)) -> bytes:
    image = Image.new("RGB", (48, 32), color=color)
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def upload_character_reference(
    client: TestClient,
    project_id: str,
    character_id: str,
    look_id: str,
    filename: str = "character.png",
) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references",
        files={"file": (filename, make_image_bytes(), "image/png")},
        data={
            "shot_type": "closeup",
            "view_angle": "front",
            "expression": "neutral",
            "pose_type": "standing",
            "description": "Identity reference",
            "is_identity_anchor": "true",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_scene(client: TestClient, project_id: str, name: str = "Lobby") -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/scenes",
        json={"name": name, "scene_type": "interior"},
    )
    assert response.status_code == 201
    return response.json()


def create_state(
    client: TestClient, project_id: str, scene_id: str, name: str = "Night Rain"
) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/scenes/{scene_id}/states",
        json={
            "name": name,
            "time_of_day": "night",
            "weather": "heavy_rain",
            "lighting": "neon",
            "season": "unknown",
            "crowd_level": "sparse",
        },
    )
    assert response.status_code == 201
    return response.json()


def upload_scene_reference(
    client: TestClient, project_id: str, scene_id: str, state_id: str
) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references",
        files={"file": ("scene.png", make_image_bytes((24, 40, 64)), "image/png")},
        data={
            "shot_scale": "wide",
            "camera_position": "eye_level",
            "view_direction": "front",
            "composition_type": "centered",
            "description": "Environment reference",
            "is_spatial_anchor": "true",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_shot(client: TestClient, project_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Shot 1",
        "story_description": "主角走入大厅。",
        "visual_description": "夜雨中的室内入口。",
        "action_summary": "进入画面",
        "mood_description": "紧张",
    }
    payload.update(overrides)
    response = client.post(f"/api/projects/{project_id}/shots", json=payload)
    assert response.status_code == 201
    return response.json()


def bind_shot_character(
    client: TestClient,
    project_id: str,
    shot_id: str,
    character_id: str,
    look_id: str,
    *,
    is_primary_subject: bool = True,
) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/shots/{shot_id}/characters",
        json={
            "character_id": character_id,
            "look_id": look_id,
            "is_primary_subject": is_primary_subject,
            "action_description": "enters frame",
        },
    )
    assert response.status_code == 201
    return response.json()


def bind_character_reference(
    client: TestClient,
    project_id: str,
    shot_id: str,
    character_reference_id: str,
    shot_character_id: str,
    purpose: str = "identity",
) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/shots/{shot_id}/references",
        json={
            "reference_type": "character",
            "character_reference_id": character_reference_id,
            "shot_character_id": shot_character_id,
            "purpose": purpose,
        },
    )
    assert response.status_code == 201
    return response.json()


def bind_scene_reference(
    client: TestClient,
    project_id: str,
    shot_id: str,
    scene_reference_id: str,
    purpose: str = "environment",
) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/shots/{shot_id}/references",
        json={
            "reference_type": "scene",
            "scene_reference_id": scene_reference_id,
            "purpose": purpose,
        },
    )
    assert response.status_code == 201
    return response.json()


def create_ready_shot_fixture(client: TestClient) -> dict[str, object]:
    project = create_project(client)
    project_id = str(project["id"])
    character = create_character(client, project_id)
    look = create_look(client, project_id, str(character["id"]))
    character_reference = upload_character_reference(
        client, project_id, str(character["id"]), str(look["id"])
    )
    scene = create_scene(client, project_id)
    state = create_state(client, project_id, str(scene["id"]))
    scene_reference = upload_scene_reference(client, project_id, str(scene["id"]), str(state["id"]))
    shot = create_shot(
        client,
        project_id,
        scene_id=scene["id"],
        scene_state_id=state["id"],
    )
    shot_character = bind_shot_character(
        client,
        project_id,
        str(shot["id"]),
        str(character["id"]),
        str(look["id"]),
    )
    shot_character_reference = bind_character_reference(
        client,
        project_id,
        str(shot["id"]),
        str(character_reference["id"]),
        str(shot_character["id"]),
    )
    shot_scene_reference = bind_scene_reference(
        client,
        project_id,
        str(shot["id"]),
        str(scene_reference["id"]),
    )
    return {
        "project": project,
        "project_id": project_id,
        "character": character,
        "look": look,
        "character_reference": character_reference,
        "scene": scene,
        "state": state,
        "scene_reference": scene_reference,
        "shot": shot,
        "shot_character": shot_character,
        "shot_character_reference": shot_character_reference,
        "shot_scene_reference": shot_scene_reference,
    }


def create_keyframe_task(
    client: TestClient,
    project_id: str,
    shot_id: str,
    *,
    copy_current_references: bool = True,
) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/shots/{shot_id}/keyframe-tasks",
        json={"copy_current_references": copy_current_references},
    )
    assert response.status_code == 201
    return response.json()


def test_keyframe_task_create_snapshot_defaults_and_mark_ready(
    migrated_client: TestClient,
) -> None:
    data = create_ready_shot_fixture(migrated_client)

    task = create_keyframe_task(
        migrated_client,
        data["project_id"],
        str(data["shot"]["id"]),
    )
    ready = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/mark-ready"
    )

    assert task["status"] == "draft"
    assert task["shot_snapshot"]["schema_version"] == 1
    assert task["shot_snapshot"]["shot_id"] == data["shot"]["id"]
    assert (
        task["shot_snapshot"]["characters"][0]["shot_character_id"] == data["shot_character"]["id"]
    )
    assert task["reference_count"] == 2
    assert task["readiness"]["readiness_status"] == "ready"
    assert task["width"] == 768
    assert task["height"] == 1360
    assert task["seed"] is None
    assert task["steps"] == 30
    assert task["guidance_scale"] == 7.0
    assert task["output_count"] == 1
    assert "relative_path" not in str(task)
    assert "stored_filename" not in str(task)
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_keyframe_task_noop_update_keeps_ready_and_real_change_downgrades(
    migrated_client: TestClient,
) -> None:
    data = create_ready_shot_fixture(migrated_client)
    task = create_keyframe_task(migrated_client, data["project_id"], str(data["shot"]["id"]))
    ready = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/mark-ready"
    ).json()

    noop = migrated_client.patch(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}",
        json={"prompt_zh": ready["prompt_zh"]},
    )
    changed = migrated_client.patch(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}",
        json={"prompt_zh": "新的画面提示词"},
    )

    assert noop.status_code == 200
    assert noop.json()["status"] == "ready"
    assert changed.status_code == 200
    assert changed.json()["status"] == "draft"


def test_keyframe_task_dimension_rules_and_aspect_mismatch_readiness(
    migrated_client: TestClient,
) -> None:
    data = create_ready_shot_fixture(migrated_client)
    task = create_keyframe_task(migrated_client, data["project_id"], str(data["shot"]["id"]))

    invalid_dimension = migrated_client.patch(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}",
        json={"width": 250},
    )
    seed_zero = migrated_client.patch(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}",
        json={"seed": 0},
    )
    aspect_mismatch = migrated_client.patch(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}",
        json={"aspect_ratio": "16:9", "width": 768, "height": 1360},
    )

    assert invalid_dimension.status_code == 422
    assert seed_zero.status_code == 200
    assert seed_zero.json()["seed"] == 0
    assert aspect_mismatch.status_code == 200
    assert "aspect_ratio_mismatch" in aspect_mismatch.json()["readiness"]["blocking_issues"]


def test_keyframe_task_primary_secondary_and_scene_readiness(
    migrated_client: TestClient,
) -> None:
    data = create_ready_shot_fixture(migrated_client)
    secondary_character = create_character(migrated_client, data["project_id"], name="Friend")
    secondary_look = create_look(
        migrated_client, data["project_id"], str(secondary_character["id"]), name="Friend Look"
    )
    bind_shot_character(
        migrated_client,
        data["project_id"],
        str(data["shot"]["id"]),
        str(secondary_character["id"]),
        str(secondary_look["id"]),
        is_primary_subject=False,
    )

    with_secondary_missing = create_keyframe_task(
        migrated_client,
        data["project_id"],
        str(data["shot"]["id"]),
    )
    no_reference_task = create_keyframe_task(
        migrated_client,
        data["project_id"],
        str(data["shot"]["id"]),
        copy_current_references=False,
    )
    empty_shot = create_shot(migrated_client, data["project_id"], name="No Character Shot")
    no_character_task = create_keyframe_task(
        migrated_client,
        data["project_id"],
        str(empty_shot["id"]),
        copy_current_references=False,
    )

    assert with_secondary_missing["readiness"]["readiness_status"] == "ready"
    assert (
        "missing_secondary_character_reference" in with_secondary_missing["readiness"]["warnings"]
    )
    assert (
        "missing_primary_character_reference" in no_reference_task["readiness"]["blocking_issues"]
    )
    assert "missing_scene_reference" in no_reference_task["readiness"]["blocking_issues"]
    assert (
        "missing_primary_character_reference"
        not in no_character_task["readiness"]["blocking_issues"]
    )


def test_keyframe_task_reference_add_duplicate_delete_and_order(
    migrated_client: TestClient,
) -> None:
    data = create_ready_shot_fixture(migrated_client)
    task = create_keyframe_task(
        migrated_client,
        data["project_id"],
        str(data["shot"]["id"]),
        copy_current_references=False,
    )

    first = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/references",
        json={"shot_reference_id": data["shot_character_reference"]["id"], "purpose": "identity"},
    )
    duplicate = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/references",
        json={"shot_reference_id": data["shot_character_reference"]["id"], "purpose": "identity"},
    )
    other_purpose = migrated_client.post(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/references",
        json={
            "shot_reference_id": data["shot_character_reference"]["id"],
            "purpose": "appearance",
        },
    )
    move = migrated_client.patch(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/references/"
        f"{other_purpose.json()['references'][-1]['id']}",
        json={"order_index": 1},
    )
    delete = migrated_client.delete(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/references/"
        f"{first.json()['references'][0]['id']}"
    )
    references = migrated_client.get(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}/references"
    ).json()["items"]

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "KEYFRAME_TASK_REFERENCE_ALREADY_EXISTS"
    assert other_purpose.status_code == 201
    assert move.status_code == 200
    assert delete.status_code == 204
    assert delete.content == b""
    assert [reference["order_index"] for reference in references] == [1]


def test_keyframe_task_source_reference_delete_keeps_task_media(
    migrated_client: TestClient,
) -> None:
    data = create_ready_shot_fixture(migrated_client)
    task = create_keyframe_task(migrated_client, data["project_id"], str(data["shot"]["id"]))
    character_task_reference = next(
        reference for reference in task["references"] if reference["reference_type"] == "character"
    )
    media_id = character_task_reference["media_asset_id"]

    delete_source = migrated_client.delete(
        f"/api/projects/{data['project_id']}/characters/{data['character']['id']}/looks/"
        f"{data['look']['id']}/references/{data['character_reference']['id']}"
    )
    refreshed = migrated_client.get(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}"
    )
    media_response = migrated_client.get(f"/api/media/{media_id}/content")

    assert delete_source.status_code == 204
    assert refreshed.status_code == 200
    updated_reference = next(
        reference
        for reference in refreshed.json()["references"]
        if reference["media_asset_id"] == media_id
    )
    assert updated_reference["character_reference_id"] is None
    assert updated_reference["source_reference_deleted"] is True
    assert updated_reference["media_asset"]["id"] == media_id
    assert media_response.status_code == 200


def test_keyframe_task_delete_does_not_delete_assets_or_shot_references(
    migrated_client: TestClient,
) -> None:
    data = create_ready_shot_fixture(migrated_client)
    task = create_keyframe_task(migrated_client, data["project_id"], str(data["shot"]["id"]))
    media_id = task["references"][0]["media_asset_id"]

    delete = migrated_client.delete(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}"
    )
    references = migrated_client.get(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/references"
    )
    media_response = migrated_client.get(f"/api/media/{media_id}/content")

    assert delete.status_code == 204
    assert delete.content == b""
    assert references.status_code == 200
    assert references.json()["total"] == 2
    assert media_response.status_code == 200


def test_keyframe_task_shot_change_warning_is_dynamic(
    migrated_client: TestClient,
) -> None:
    data = create_ready_shot_fixture(migrated_client)
    task = create_keyframe_task(migrated_client, data["project_id"], str(data["shot"]["id"]))

    migrated_client.patch(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}",
        json={"visual_description": "镜头已经被修改。"},
    )
    refreshed = migrated_client.get(
        f"/api/projects/{data['project_id']}/keyframe-tasks/{task['id']}"
    )

    assert refreshed.status_code == 200
    assert refreshed.json()["shot_changed_since_snapshot"] is True
    assert "shot_changed_since_snapshot" in refreshed.json()["readiness"]["warnings"]


def test_keyframe_task_database_constraints_reject_invalid_values(
    migrated_client: TestClient,
) -> None:
    data = create_ready_shot_fixture(migrated_client)
    now = "2026-06-29T00:00:00+00:00"

    with get_session_factory()() as session:
        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    """
                    INSERT INTO keyframe_generation_tasks (
                        id, project_id, shot_id, name, status, shot_snapshot,
                        source_shot_updated_at, prompt_zh, aspect_ratio, width, height,
                        seed, steps, guidance_scale, output_count, created_at, updated_at
                    )
                    VALUES (
                        'invalid-keyframe-task', :project_id, :shot_id, 'Invalid',
                        'queued', :snapshot, :updated_at, 'prompt', '9:16', 768, 1360,
                        NULL, 30, 7.0, 1, :created_at, :updated_at
                    )
                    """
                ),
                {
                    "project_id": data["project_id"],
                    "shot_id": data["shot"]["id"],
                    "snapshot": (
                        '{"schema_version":1,"shot_id":"x","order_index":1,'
                        '"title":"x","shot_scale":"unknown","camera_angle":"unknown",'
                        '"camera_height":"unknown","composition_type":"unknown",'
                        '"camera_movement":"unknown","characters":[]}'
                    ),
                    "created_at": now,
                    "updated_at": now,
                },
            )
            session.commit()
