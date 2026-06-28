from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.core.errors import AppError
from app.service.media_storage_service import MediaStorageService


def create_project(client: TestClient, name: str = "Sprint 3 Project") -> dict[str, object]:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()


def create_scene(
    client: TestClient,
    project_id: str,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Office Exterior",
        "scene_type": "exterior",
        "fixed_environment_description": "Black stone wall and glass facade",
    }
    payload.update(overrides)
    response = client.post(f"/api/projects/{project_id}/scenes", json=payload)
    assert response.status_code == 201
    return response.json()


def create_state(
    client: TestClient,
    project_id: str,
    scene_id: str,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Night Rain",
        "time_of_day": "night",
        "weather": "heavy_rain",
        "lighting": "neon",
        "season": "unknown",
        "crowd_level": "sparse",
    }
    payload.update(overrides)
    response = client.post(f"/api/projects/{project_id}/scenes/{scene_id}/states", json=payload)
    assert response.status_code == 201
    return response.json()


def make_image_bytes(format_name: str = "PNG") -> bytes:
    image = Image.new("RGB", (40, 30), color=(24, 40, 64))
    stream = BytesIO()
    image.save(stream, format=format_name)
    return stream.getvalue()


def upload_reference(
    client: TestClient,
    project_id: str,
    scene_id: str,
    state_id: str,
    filename: str = "scene-reference.png",
    content_type: str = "image/png",
    description: str = "Scene image",
    **overrides: str,
) -> dict[str, object]:
    data = {
        "shot_scale": "wide",
        "camera_position": "eye_level",
        "view_direction": "front",
        "composition_type": "centered",
        "tags": "exterior, rain",
        "description": description,
        "is_empty_plate": "false",
        "is_spatial_anchor": "false",
    }
    data.update(overrides)
    response = client.post(
        f"/api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references",
        files={"file": (filename, make_image_bytes(), content_type)},
        data=data,
    )
    assert response.status_code == 201
    return response.json()


def get_storage_files() -> list[Path]:
    root = get_settings().resolved_storage_dir / "projects"
    if not root.exists():
        return []
    return [path for path in root.rglob("*") if path.is_file()]


def test_scene_list_empty_create_update_and_safe_errors(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)

    empty = migrated_client.get(f"/api/projects/{project['id']}/scenes")
    scene = create_scene(migrated_client, str(project["id"]), description="Keep")
    update = migrated_client.patch(
        f"/api/projects/{project['id']}/scenes/{scene['id']}",
        json={"name": "Updated Exterior", "notes": None},
    )
    invalid_id = migrated_client.get(f"/api/projects/{project['id']}/scenes/not-a-uuid")
    blank_name = migrated_client.patch(
        f"/api/projects/{project['id']}/scenes/{scene['id']}",
        json={"name": "   "},
    )

    assert empty.status_code == 200
    assert empty.json() == {"items": [], "total": 0}
    assert scene["state_count"] == 0
    assert scene["default_state"] is None
    assert update.status_code == 200
    assert update.json()["name"] == "Updated Exterior"
    assert update.json()["description"] == "Keep"
    assert update.json()["notes"] is None
    assert invalid_id.status_code == 422
    assert invalid_id.json()["error"]["code"] == "INVALID_SCENE_ID"
    assert blank_name.status_code == 422
    assert blank_name.json()["error"]["code"] == "SCENE_NAME_REQUIRED"


def test_scene_state_default_custom_and_delete_rules(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    scene = create_scene(migrated_client, str(project["id"]))
    first = create_state(migrated_client, str(project["id"]), str(scene["id"]), name="First")
    second = create_state(
        migrated_client,
        str(project["id"]),
        str(scene["id"]),
        name="Second",
        time_of_day="night",
        weather="heavy_rain",
        lighting="neon",
    )
    duplicate_combo = create_state(
        migrated_client,
        str(project["id"]),
        str(scene["id"]),
        name="Second usage",
        time_of_day="night",
        weather="heavy_rain",
        lighting="neon",
    )
    custom_missing = migrated_client.patch(
        f"/api/projects/{project['id']}/scenes/{scene['id']}/states/{second['id']}",
        json={"weather": "custom"},
    )
    custom_update = migrated_client.patch(
        f"/api/projects/{project['id']}/scenes/{scene['id']}/states/{second['id']}",
        json={"weather": "custom", "custom_weather": "acid rain", "lighting": "natural_soft"},
    )
    set_default = migrated_client.post(
        f"/api/projects/{project['id']}/scenes/{scene['id']}/states/{second['id']}/set-default"
    )
    delete_default = migrated_client.delete(
        f"/api/projects/{project['id']}/scenes/{scene['id']}/states/{second['id']}"
    )
    states = migrated_client.get(
        f"/api/projects/{project['id']}/scenes/{scene['id']}/states"
    ).json()["items"]

    assert first["is_default"] is True
    assert second["is_default"] is False
    assert duplicate_combo["id"] != second["id"]
    assert custom_missing.status_code == 422
    assert custom_missing.json()["error"]["code"] == "CUSTOM_WEATHER_REQUIRED"
    assert custom_update.status_code == 200
    assert custom_update.json()["custom_weather"] == "acid rain"
    assert custom_update.json()["custom_lighting"] is None
    assert set_default.status_code == 200
    assert set_default.json()["is_default"] is True
    assert delete_default.status_code == 204
    assert delete_default.content == b""
    assert [state["id"] for state in states if state["is_default"]] == [first["id"]]


def test_cannot_delete_only_scene_state(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    scene = create_scene(migrated_client, str(project["id"]))
    state = create_state(migrated_client, str(project["id"]), str(scene["id"]))

    response = migrated_client.delete(
        f"/api/projects/{project['id']}/scenes/{scene['id']}/states/{state['id']}"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "LAST_SCENE_STATE_DELETE_FORBIDDEN"


def test_scene_reference_metadata_primary_spatial_and_empty_plate_rules(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    scene = create_scene(migrated_client, str(project["id"]))
    state = create_state(migrated_client, str(project["id"]), str(scene["id"]))
    first = upload_reference(
        migrated_client,
        str(project["id"]),
        str(scene["id"]),
        str(state["id"]),
        is_spatial_anchor="true",
    )
    second = upload_reference(
        migrated_client,
        str(project["id"]),
        str(scene["id"]),
        str(state["id"]),
        description="Second",
    )
    metadata = migrated_client.patch(
        f"/api/projects/{project['id']}/scenes/{scene['id']}/states/{state['id']}"
        f"/references/{first['id']}",
        json={
            "camera_position": "custom",
            "custom_camera_position": "inside elevator",
            "view_direction": "left",
            "composition_type": "custom",
            "custom_composition": "split foreground",
            "description": None,
            "tags": [],
            "is_empty_plate": True,
            "is_spatial_anchor": False,
        },
    )
    set_primary = migrated_client.post(
        f"/api/projects/{project['id']}/scenes/{scene['id']}/states/{state['id']}"
        f"/references/{second['id']}/set-primary"
    )
    references = migrated_client.get(
        f"/api/projects/{project['id']}/scenes/{scene['id']}/states/{state['id']}/references"
    ).json()["items"]

    assert first["is_primary"] is True
    assert first["is_spatial_anchor"] is True
    assert second["is_primary"] is False
    assert metadata.status_code == 200
    assert metadata.json()["custom_camera_position"] == "inside elevator"
    assert metadata.json()["custom_view_direction"] is None
    assert metadata.json()["custom_composition"] == "split foreground"
    assert metadata.json()["description"] is None
    assert metadata.json()["tags"] == []
    assert metadata.json()["is_empty_plate"] is True
    assert metadata.json()["is_spatial_anchor"] is False
    assert set_primary.status_code == 200
    assert set_primary.json()["is_primary"] is True
    assert set_primary.json()["is_spatial_anchor"] is False
    assert [reference["id"] for reference in references if reference["is_primary"]] == [
        second["id"]
    ]


def test_scene_reference_delete_primary_selects_next_and_cleans_missing_files(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    scene = create_scene(migrated_client, str(project["id"]))
    state = create_state(migrated_client, str(project["id"]), str(scene["id"]))
    first = upload_reference(
        migrated_client,
        str(project["id"]),
        str(scene["id"]),
        str(state["id"]),
    )
    second = upload_reference(
        migrated_client,
        str(project["id"]),
        str(scene["id"]),
        str(state["id"]),
        description="Second",
    )
    for path in get_storage_files():
        path.unlink()

    response = migrated_client.delete(
        f"/api/projects/{project['id']}/scenes/{scene['id']}/states/{state['id']}"
        f"/references/{first['id']}"
    )
    references = migrated_client.get(
        f"/api/projects/{project['id']}/scenes/{scene['id']}/states/{state['id']}/references"
    ).json()["items"]

    assert response.status_code == 204
    assert response.content == b""
    assert [reference["id"] for reference in references if reference["is_primary"]] == [
        second["id"]
    ]


def test_delete_scene_cleans_media_and_cleanup_failure_does_not_leak_path(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    project = create_project(migrated_client)
    scene = create_scene(migrated_client, str(project["id"]))
    state = create_state(migrated_client, str(project["id"]), str(scene["id"]))
    reference = upload_reference(
        migrated_client,
        str(project["id"]),
        str(scene["id"]),
        str(state["id"]),
    )
    files = get_storage_files()
    assert files

    def fail_delete(self: MediaStorageService, relative_path: str | None) -> None:
        raise AppError(
            code="IMAGE_UPLOAD_FAILED",
            message="F:/secret/storage/reference.png",
            status_code=500,
        )

    monkeypatch.setattr(MediaStorageService, "delete_relative_file", fail_delete)
    response = migrated_client.delete(f"/api/projects/{project['id']}/scenes/{scene['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert migrated_client.get(reference["media_asset"]["content_url"]).status_code == 404


def test_scene_list_summary_and_media_response_are_safe(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    older = create_scene(migrated_client, str(project["id"]), name="Older")
    newer = create_scene(migrated_client, str(project["id"]), name="Newer")
    state = create_state(migrated_client, str(project["id"]), str(newer["id"]))
    reference = upload_reference(
        migrated_client,
        str(project["id"]),
        str(newer["id"]),
        str(state["id"]),
    )

    response = migrated_client.get(f"/api/projects/{project['id']}/scenes")
    media = reference["media_asset"]

    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["id"] == newer["id"]
    assert older["id"] in [item["id"] for item in items]
    assert items[0]["state_count"] == 1
    assert items[0]["reference_count"] == 1
    assert items[0]["cover_reference"]["id"] == reference["id"]
    assert media["thumbnail_url"].startswith("/api/media/")
    assert media["content_url"].startswith("/api/media/")
    assert "relative_path" not in media
    assert "stored_filename" not in media


def test_cross_project_scene_access_fails(migrated_client: TestClient) -> None:
    project_a = create_project(migrated_client, "Project A")
    project_b = create_project(migrated_client, "Project B")
    scene = create_scene(migrated_client, str(project_a["id"]))
    state = create_state(migrated_client, str(project_a["id"]), str(scene["id"]))

    update = migrated_client.patch(
        f"/api/projects/{project_b['id']}/scenes/{scene['id']}",
        json={"name": "Wrong project"},
    )
    delete_state = migrated_client.delete(
        f"/api/projects/{project_b['id']}/scenes/{scene['id']}/states/{state['id']}"
    )

    assert update.status_code == 404
    assert delete_state.status_code == 404
