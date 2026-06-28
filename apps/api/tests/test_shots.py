from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.infrastructure.database import get_session_factory


def create_project(client: TestClient, name: str = "Sprint 4 Project") -> dict[str, object]:
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


def make_image_bytes() -> bytes:
    image = Image.new("RGB", (32, 24), color=(64, 96, 128))
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def upload_character_reference(
    client: TestClient, project_id: str, character_id: str, look_id: str
) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references",
        files={"file": ("character.png", make_image_bytes(), "image/png")},
        data={
            "shot_type": "closeup",
            "view_angle": "front",
            "expression": "neutral",
            "pose_type": "standing",
            "description": "Character reference",
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
        files={"file": ("scene.png", make_image_bytes(), "image/png")},
        data={
            "shot_scale": "wide",
            "camera_position": "eye_level",
            "view_direction": "front",
            "composition_type": "centered",
            "description": "Scene reference",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_shot(client: TestClient, project_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {"name": "Shot 1"}
    payload.update(overrides)
    response = client.post(f"/api/projects/{project_id}/shots", json=payload)
    assert response.status_code == 201
    return response.json()


def test_shot_duration_validation_and_patch_semantics(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    project_id = str(project["id"])

    null_duration = migrated_client.post(
        f"/api/projects/{project_id}/shots",
        json={"name": "No Duration", "duration_seconds": None},
    )
    positive_duration = migrated_client.post(
        f"/api/projects/{project_id}/shots",
        json={"name": "Positive Duration", "duration_seconds": 2.5},
    )
    zero_duration = migrated_client.post(
        f"/api/projects/{project_id}/shots",
        json={"name": "Zero Duration", "duration_seconds": 0},
    )
    negative_duration = migrated_client.post(
        f"/api/projects/{project_id}/shots",
        json={"name": "Negative Duration", "duration_seconds": -1},
    )
    invalid_duration = migrated_client.post(
        f"/api/projects/{project_id}/shots",
        json={"name": "Invalid Duration", "duration_seconds": "abc"},
    )

    assert null_duration.status_code == 201
    assert null_duration.json()["duration_seconds"] is None
    assert positive_duration.status_code == 201
    assert positive_duration.json()["duration_seconds"] == 2.5
    assert zero_duration.status_code == 422
    assert zero_duration.json()["error"]["code"] == "SHOT_DURATION_SECONDS_POSITIVE"
    assert negative_duration.status_code == 422
    assert negative_duration.json()["error"]["code"] == "SHOT_DURATION_SECONDS_POSITIVE"
    assert invalid_duration.status_code == 422

    shot_id = positive_duration.json()["id"]
    patch_without_duration = migrated_client.patch(
        f"/api/projects/{project_id}/shots/{shot_id}",
        json={"visual_description": "Keep duration."},
    )
    patch_null_duration = migrated_client.patch(
        f"/api/projects/{project_id}/shots/{shot_id}",
        json={"duration_seconds": None},
    )
    patch_zero_duration = migrated_client.patch(
        f"/api/projects/{project_id}/shots/{shot_id}",
        json={"duration_seconds": 0},
    )
    patch_negative_duration = migrated_client.patch(
        f"/api/projects/{project_id}/shots/{shot_id}",
        json={"duration_seconds": -3},
    )

    assert patch_without_duration.status_code == 200
    assert patch_without_duration.json()["duration_seconds"] == 2.5
    assert patch_null_duration.status_code == 200
    assert patch_null_duration.json()["duration_seconds"] is None
    assert patch_zero_duration.status_code == 422
    assert patch_zero_duration.json()["error"]["code"] == "SHOT_DURATION_SECONDS_POSITIVE"
    assert patch_negative_duration.status_code == 422
    assert patch_negative_duration.json()["error"]["code"] == "SHOT_DURATION_SECONDS_POSITIVE"


def test_shot_duration_database_constraint_rejects_non_positive_values(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    now = "2026-06-28T00:00:00+00:00"

    for value in (0, -1):
        with get_session_factory()() as session:
            with pytest.raises(IntegrityError):
                session.execute(
                    text(
                        """
                        INSERT INTO shots (
                            id, project_id, name, order_index, duration_seconds,
                            shot_scale, camera_height, camera_angle, composition_type,
                            camera_movement, created_at, updated_at
                        )
                        VALUES (
                            :id, :project_id, :name, :order_index, :duration_seconds,
                            'unknown', 'unknown', 'unknown', 'unknown',
                            'unknown', :created_at, :updated_at
                        )
                        """
                    ),
                    {
                        "id": f"duration-constraint-{abs(value)}",
                        "project_id": project["id"],
                        "name": f"Invalid {value}",
                        "order_index": abs(value) + 20,
                        "duration_seconds": value,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                session.commit()


def test_shot_crud_readiness_and_independent_lists(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    look = create_look(migrated_client, str(project["id"]), str(character["id"]))
    character_reference = upload_character_reference(
        migrated_client, str(project["id"]), str(character["id"]), str(look["id"])
    )
    scene = create_scene(migrated_client, str(project["id"]))
    state = create_state(migrated_client, str(project["id"]), str(scene["id"]))
    scene_reference = upload_scene_reference(
        migrated_client, str(project["id"]), str(scene["id"]), str(state["id"])
    )
    shot = create_shot(
        migrated_client,
        str(project["id"]),
        visual_description="A tense arrival.",
        scene_id=scene["id"],
        scene_state_id=state["id"],
    )

    shot_character = migrated_client.post(
        f"/api/projects/{project['id']}/shots/{shot['id']}/characters",
        json={
            "character_id": character["id"],
            "look_id": look["id"],
            "is_primary_subject": True,
            "action_description": "enters frame",
        },
    )
    character_binding = shot_character.json()
    character_ref = migrated_client.post(
        f"/api/projects/{project['id']}/shots/{shot['id']}/references",
        json={
            "reference_type": "character",
            "character_reference_id": character_reference["id"],
            "shot_character_id": character_binding["id"],
            "purpose": "identity",
        },
    )
    scene_ref = migrated_client.post(
        f"/api/projects/{project['id']}/shots/{shot['id']}/references",
        json={
            "reference_type": "scene",
            "scene_reference_id": scene_reference["id"],
            "purpose": "environment",
        },
    )
    detail = migrated_client.get(f"/api/projects/{project['id']}/shots/{shot['id']}")
    characters = migrated_client.get(f"/api/projects/{project['id']}/shots/{shot['id']}/characters")
    references = migrated_client.get(f"/api/projects/{project['id']}/shots/{shot['id']}/references")

    assert shot["readiness_status"] == "draft"
    assert shot_character.status_code == 201
    assert character_ref.status_code == 201
    assert scene_ref.status_code == 201
    assert detail.status_code == 200
    assert detail.json()["readiness_status"] == "asset_ready"
    assert detail.json()["missing_items"] == []
    assert characters.status_code == 200
    assert characters.json()["total"] == 1
    assert references.status_code == 200
    assert references.json()["total"] == 2


def test_shot_patch_custom_and_scene_switch_cleans_only_scene_references(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    look = create_look(migrated_client, str(project["id"]), str(character["id"]))
    character_reference = upload_character_reference(
        migrated_client, str(project["id"]), str(character["id"]), str(look["id"])
    )
    scene = create_scene(migrated_client, str(project["id"]), "Scene A")
    state = create_state(migrated_client, str(project["id"]), str(scene["id"]), "State A")
    scene_reference = upload_scene_reference(
        migrated_client, str(project["id"]), str(scene["id"]), str(state["id"])
    )
    other_scene = create_scene(migrated_client, str(project["id"]), "Scene B")
    other_state = create_state(
        migrated_client, str(project["id"]), str(other_scene["id"]), "State B"
    )
    shot = create_shot(
        migrated_client,
        str(project["id"]),
        visual_description="Keep visual.",
        scene_id=scene["id"],
        scene_state_id=state["id"],
    )
    shot_character = migrated_client.post(
        f"/api/projects/{project['id']}/shots/{shot['id']}/characters",
        json={"character_id": character["id"], "look_id": look["id"]},
    ).json()
    migrated_client.post(
        f"/api/projects/{project['id']}/shots/{shot['id']}/references",
        json={
            "reference_type": "character",
            "character_reference_id": character_reference["id"],
            "shot_character_id": shot_character["id"],
            "purpose": "identity",
        },
    )
    migrated_client.post(
        f"/api/projects/{project['id']}/shots/{shot['id']}/references",
        json={
            "reference_type": "scene",
            "scene_reference_id": scene_reference["id"],
            "purpose": "environment",
        },
    )

    custom_missing = migrated_client.patch(
        f"/api/projects/{project['id']}/shots/{shot['id']}",
        json={"camera_height": "custom"},
    )
    switch_scene = migrated_client.patch(
        f"/api/projects/{project['id']}/shots/{shot['id']}",
        json={"scene_id": other_scene["id"], "scene_state_id": other_state["id"]},
    )
    references = migrated_client.get(
        f"/api/projects/{project['id']}/shots/{shot['id']}/references"
    ).json()["items"]

    assert custom_missing.status_code == 422
    assert custom_missing.json()["error"]["code"] == "CUSTOM_CAMERA_HEIGHT_REQUIRED"
    assert switch_scene.status_code == 200
    assert switch_scene.json()["scene_id"] == other_scene["id"]
    assert [reference["reference_type"] for reference in references] == ["character"]


def test_shot_order_duplicate_delete_and_204_body(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    first = create_shot(migrated_client, str(project["id"]), name="First")
    second = create_shot(migrated_client, str(project["id"]), name="Second")
    third = create_shot(migrated_client, str(project["id"]), name="Third")

    move = migrated_client.post(
        f"/api/projects/{project['id']}/shots/{third['id']}/move",
        json={"order_index": 1},
    )
    duplicate = migrated_client.post(f"/api/projects/{project['id']}/shots/{first['id']}/duplicate")
    delete = migrated_client.delete(f"/api/projects/{project['id']}/shots/{second['id']}")
    items = migrated_client.get(f"/api/projects/{project['id']}/shots").json()["items"]

    assert move.status_code == 200
    assert duplicate.status_code == 200
    assert duplicate.json()["name"] == "First - 副本"
    assert delete.status_code == 204
    assert delete.content == b""
    assert [item["order_index"] for item in items] == list(range(1, len(items) + 1))


def test_shot_reference_duplicate_and_database_conflict_are_safe(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    from sqlalchemy.exc import IntegrityError

    from app.repository.shot_repository import ShotRepository

    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    look = create_look(migrated_client, str(project["id"]), str(character["id"]))
    character_reference = upload_character_reference(
        migrated_client, str(project["id"]), str(character["id"]), str(look["id"])
    )
    shot = create_shot(migrated_client, str(project["id"]))
    shot_character = migrated_client.post(
        f"/api/projects/{project['id']}/shots/{shot['id']}/characters",
        json={"character_id": character["id"], "look_id": look["id"]},
    ).json()
    payload = {
        "reference_type": "character",
        "character_reference_id": character_reference["id"],
        "shot_character_id": shot_character["id"],
        "purpose": "identity",
    }
    first = migrated_client.post(
        f"/api/projects/{project['id']}/shots/{shot['id']}/references", json=payload
    )
    duplicate = migrated_client.post(
        f"/api/projects/{project['id']}/shots/{shot['id']}/references", json=payload
    )

    def fail_create_reference(self: ShotRepository, record: object) -> object:
        raise IntegrityError("insert", {}, Exception("hidden database path"))

    monkeypatch.setattr(ShotRepository, "find_duplicate_reference", lambda *args: None)
    monkeypatch.setattr(ShotRepository, "create_reference", fail_create_reference)
    conflict = migrated_client.post(
        f"/api/projects/{project['id']}/shots/{shot['id']}/references",
        json={**payload, "purpose": "appearance"},
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "SHOT_REFERENCE_ALREADY_BOUND"
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "DATABASE_CONFLICT"
    assert "hidden" not in conflict.text


def test_external_asset_deletes_update_shot_readiness_and_look_delete_sets_null(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    look = create_look(migrated_client, str(project["id"]), str(character["id"]), "A")
    backup_look = create_look(migrated_client, str(project["id"]), str(character["id"]), "B")
    character_reference = upload_character_reference(
        migrated_client, str(project["id"]), str(character["id"]), str(look["id"])
    )
    scene = create_scene(migrated_client, str(project["id"]))
    state = create_state(migrated_client, str(project["id"]), str(scene["id"]))
    scene_reference = upload_scene_reference(
        migrated_client, str(project["id"]), str(scene["id"]), str(state["id"])
    )
    shot = create_shot(
        migrated_client,
        str(project["id"]),
        visual_description="Ready.",
        scene_id=scene["id"],
        scene_state_id=state["id"],
    )
    shot_character = migrated_client.post(
        f"/api/projects/{project['id']}/shots/{shot['id']}/characters",
        json={"character_id": character["id"], "look_id": look["id"], "is_primary_subject": True},
    ).json()
    migrated_client.post(
        f"/api/projects/{project['id']}/shots/{shot['id']}/references",
        json={
            "reference_type": "character",
            "character_reference_id": character_reference["id"],
            "shot_character_id": shot_character["id"],
            "purpose": "identity",
        },
    )
    migrated_client.post(
        f"/api/projects/{project['id']}/shots/{shot['id']}/references",
        json={
            "reference_type": "scene",
            "scene_reference_id": scene_reference["id"],
            "purpose": "environment",
        },
    )

    delete_look = migrated_client.delete(
        f"/api/projects/{project['id']}/characters/{character['id']}/looks/{look['id']}"
    )
    after_look_delete = migrated_client.get(
        f"/api/projects/{project['id']}/shots/{shot['id']}/characters"
    ).json()["items"][0]
    delete_scene_ref = migrated_client.delete(
        f"/api/projects/{project['id']}/scenes/{scene['id']}/states/{state['id']}"
        f"/references/{scene_reference['id']}"
    )
    shot_after_scene_ref_delete = migrated_client.get(
        f"/api/projects/{project['id']}/shots/{shot['id']}"
    ).json()

    assert backup_look["id"] != look["id"]
    assert delete_look.status_code == 204
    assert after_look_delete["look_id"] is None
    assert delete_scene_ref.status_code == 204
    assert shot_after_scene_ref_delete["readiness_status"] == "basic_ready"
    assert "scene_references" in shot_after_scene_ref_delete["missing_items"]


def test_shot_list_uses_aggregate_data_without_loading_each_child_collection(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    from app.repository.shot_repository import ShotRepository

    project = create_project(migrated_client)
    create_shot(migrated_client, str(project["id"]), name="A")
    create_shot(migrated_client, str(project["id"]), name="B")

    def fail_list_characters(self: ShotRepository, shot_id: str) -> object:
        raise AssertionError("list endpoint should not load per-shot children")

    monkeypatch.setattr(ShotRepository, "list_characters", fail_list_characters)
    response = migrated_client.get(f"/api/projects/{project['id']}/shots")

    assert response.status_code == 200
    assert response.json()["total"] == 2
