from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

from app.infrastructure.database import get_session_factory
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.keyframe_task import KeyframeGenerationTaskRecord
from app.infrastructure.models.video_generation import VideoGenerationTaskRecord


def create_project(client: TestClient, name: str = "Asset Summary Project") -> dict[str, object]:
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


def create_look(client: TestClient, project_id: str, character_id: str) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/characters/{character_id}/looks",
        json={"name": "Default Look"},
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


def create_state(client: TestClient, project_id: str, scene_id: str) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/scenes/{scene_id}/states",
        json={"name": "Night", "time_of_day": "night"},
    )
    assert response.status_code == 201
    return response.json()


def create_shot(client: TestClient, project_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {"name": "Shot 1"}
    payload.update(overrides)
    response = client.post(f"/api/projects/{project_id}/shots", json=payload)
    assert response.status_code == 201
    return response.json()


def make_image_bytes() -> bytes:
    image = Image.new("RGB", (32, 24), color=(16, 32, 64))
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def upload_character_reference(
    client: TestClient,
    project_id: str,
    character_id: str,
    look_id: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references",
        files={"file": ("character.png", make_image_bytes(), "image/png")},
        data={
            "shot_type": "full_body",
            "view_angle": "front",
            "expression": "neutral",
            "pose_type": "standing",
            "description": "Hero full body",
            "is_identity_anchor": "true",
        },
    )
    assert response.status_code == 201
    return response.json()


def upload_scene_reference(
    client: TestClient,
    project_id: str,
    scene_id: str,
    state_id: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references",
        files={"file": ("scene.png", make_image_bytes(), "image/png")},
        data={
            "shot_scale": "wide",
            "camera_position": "eye_level",
            "view_direction": "front",
            "composition_type": "centered",
            "description": "Wide environment",
            "is_empty_plate": "true",
            "is_spatial_anchor": "true",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_character_asset_summary_returns_callable_asset_counts(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    project_id = str(project["id"])
    character = create_character(migrated_client, project_id, "Hero")
    look = create_look(migrated_client, project_id, str(character["id"]))
    upload_character_reference(migrated_client, project_id, str(character["id"]), str(look["id"]))
    shot = create_shot(migrated_client, project_id)
    migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/characters",
        json={"character_id": character["id"], "look_id": look["id"]},
    )

    response = migrated_client.get(
        f"/api/projects/{project_id}/characters/{character['id']}/asset-summary"
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["name"] == "Hero"
    assert payload["look_count"] == 1
    assert payload["reference_count"] == 1
    assert payload["identity_anchor_count"] == 1
    assert payload["used_shot_count"] == 1
    assert payload["recent_shots"][0]["id"] == shot["id"]
    assert payload["featured_references"][0]["media_asset"]["content_url"].startswith("/api/media/")
    assert "relative_path" not in response.text


def test_scene_asset_summary_returns_scene_reference_counts(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    project_id = str(project["id"])
    scene = create_scene(migrated_client, project_id, "Office")
    state = create_state(migrated_client, project_id, str(scene["id"]))
    upload_scene_reference(migrated_client, project_id, str(scene["id"]), str(state["id"]))
    shot = create_shot(
        migrated_client,
        project_id,
        scene_id=scene["id"],
        scene_state_id=state["id"],
    )

    response = migrated_client.get(f"/api/projects/{project_id}/scenes/{scene['id']}/asset-summary")
    payload = response.json()

    assert response.status_code == 200
    assert payload["name"] == "Office"
    assert payload["state_count"] == 1
    assert payload["reference_count"] == 1
    assert payload["spatial_anchor_count"] == 1
    assert payload["empty_plate_count"] == 1
    assert payload["used_shot_count"] == 1
    assert payload["recent_shots"][0]["id"] == shot["id"]
    assert "relative_path" not in response.text


def test_shot_asset_summary_returns_bindings_and_generation_counts(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    project_id = str(project["id"])
    character = create_character(migrated_client, project_id)
    look = create_look(migrated_client, project_id, str(character["id"]))
    character_reference = upload_character_reference(
        migrated_client, project_id, str(character["id"]), str(look["id"])
    )
    scene = create_scene(migrated_client, project_id)
    state = create_state(migrated_client, project_id, str(scene["id"]))
    scene_reference = upload_scene_reference(
        migrated_client, project_id, str(scene["id"]), str(state["id"])
    )
    shot = create_shot(
        migrated_client,
        project_id,
        scene_id=scene["id"],
        scene_state_id=state["id"],
    )
    shot_character = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/characters",
        json={"character_id": character["id"], "look_id": look["id"]},
    ).json()
    migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/references",
        json={
            "reference_type": "character",
            "character_reference_id": character_reference["id"],
            "shot_character_id": shot_character["id"],
            "purpose": "identity",
        },
    )
    migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/references",
        json={
            "reference_type": "scene",
            "scene_reference_id": scene_reference["id"],
            "purpose": "environment",
        },
    )
    keyframe_task = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/keyframe-tasks",
        json={},
    )
    video_task = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/video-tasks",
        json={},
    )

    response = migrated_client.get(f"/api/projects/{project_id}/shots/{shot['id']}/asset-summary")
    payload = response.json()

    assert keyframe_task.status_code == 201
    assert video_task.status_code == 201
    assert response.status_code == 200
    assert payload["characters"][0]["character_name"] == "Lead"
    assert payload["characters"][0]["bound_reference_count"] == 1
    assert payload["scene"]["scene_name"] == "Lobby"
    assert payload["scene"]["bound_reference_count"] == 1
    assert payload["generation"]["keyframe_task_count"] == 1
    assert payload["generation"]["video_task_count"] == 1
    assert len(payload["references"]) == 2


def test_asset_summaries_enforce_project_scope_and_do_not_mutate_records(
    migrated_client: TestClient,
) -> None:
    first = create_project(migrated_client, "First")
    second = create_project(migrated_client, "Second")
    character = create_character(migrated_client, str(first["id"]))

    with get_session_factory()() as session:
        before_media_count = len(list(session.scalars(select(MediaAssetRecord)).all()))
        before_keyframe_count = len(
            list(session.scalars(select(KeyframeGenerationTaskRecord)).all())
        )
        before_video_count = len(list(session.scalars(select(VideoGenerationTaskRecord)).all()))

    response = migrated_client.get(
        f"/api/projects/{second['id']}/characters/{character['id']}/asset-summary"
    )

    with get_session_factory()() as session:
        after_media_count = len(list(session.scalars(select(MediaAssetRecord)).all()))
        after_keyframe_count = len(
            list(session.scalars(select(KeyframeGenerationTaskRecord)).all())
        )
        after_video_count = len(list(session.scalars(select(VideoGenerationTaskRecord)).all()))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CHARACTER_NOT_FOUND"
    assert after_media_count == before_media_count
    assert after_keyframe_count == before_keyframe_count
    assert after_video_count == before_video_count
