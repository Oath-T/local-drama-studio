from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.core.errors import AppError
from app.service.media_storage_service import MediaStorageService


def create_project(client: TestClient, name: str = "Sprint 2 Project") -> dict[str, object]:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()


def create_character(
    client: TestClient,
    project_id: str,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Lead Character",
        "role_type": "protagonist",
        "description": "Initial description",
    }
    payload.update(overrides)
    response = client.post(f"/api/projects/{project_id}/characters", json=payload)
    assert response.status_code == 201
    return response.json()


def create_look(
    client: TestClient,
    project_id: str,
    character_id: str,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Evening Look",
        "description": "Initial look",
        "condition_description": "Rain scene",
    }
    payload.update(overrides)
    response = client.post(
        f"/api/projects/{project_id}/characters/{character_id}/looks",
        json=payload,
    )
    assert response.status_code == 201
    return response.json()


def make_image_bytes(format_name: str = "PNG") -> bytes:
    image = Image.new("RGB", (32, 24), color=(64, 96, 128))
    stream = BytesIO()
    image.save(stream, format=format_name)
    return stream.getvalue()


def upload_reference(
    client: TestClient,
    project_id: str,
    character_id: str,
    look_id: str,
    filename: str = "reference.png",
    content_type: str = "image/png",
    description: str = "Reference image",
) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references",
        files={"file": (filename, make_image_bytes(), content_type)},
        data={
            "shot_type": "closeup",
            "view_angle": "front",
            "expression": "neutral",
            "pose_type": "standing",
            "tags": "identity, studio",
            "description": description,
            "notes": "Original note",
            "is_identity_anchor": "true",
        },
    )
    assert response.status_code == 201
    return response.json()


def get_storage_files() -> list[Path]:
    root = get_settings().resolved_storage_dir / "projects"
    if not root.exists():
        return []
    return [path for path in root.rglob("*") if path.is_file()]


def test_character_list_initially_empty(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)

    response = migrated_client.get(f"/api/projects/{project['id']}/characters")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_create_character_has_no_automatic_look(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)

    character = create_character(migrated_client, str(project["id"]))

    assert character["name"] == "Lead Character"
    assert character["role_type"] == "protagonist"
    assert character["look_count"] == 0
    assert character["reference_count"] == 0
    assert character["default_look"] is None


def test_update_character_patch_keeps_unsubmitted_fields(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    character = create_character(
        migrated_client,
        str(project["id"]),
        aliases="Old Alias",
        description="Keep me",
    )

    response = migrated_client.patch(
        f"/api/projects/{project['id']}/characters/{character['id']}",
        json={"name": "Updated Character"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Character"
    assert data["aliases"] == "Old Alias"
    assert data["description"] == "Keep me"


def test_update_character_null_and_blank_name_rules(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]), aliases="Alias")

    clear_response = migrated_client.patch(
        f"/api/projects/{project['id']}/characters/{character['id']}",
        json={"aliases": None},
    )
    blank_response = migrated_client.patch(
        f"/api/projects/{project['id']}/characters/{character['id']}",
        json={"name": "   "},
    )

    assert clear_response.status_code == 200
    assert clear_response.json()["aliases"] is None
    assert blank_response.status_code == 422
    assert blank_response.json()["error"]["code"] == "CHARACTER_NAME_REQUIRED"


def test_invalid_character_id_returns_safe_error(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)

    response = migrated_client.get(f"/api/projects/{project['id']}/characters/not-a-uuid")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_CHARACTER_ID"


def test_first_look_becomes_default(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))

    look = create_look(migrated_client, str(project["id"]), str(character["id"]))

    assert look["is_default"] is True
    refreshed = migrated_client.get(
        f"/api/projects/{project['id']}/characters/{character['id']}"
    ).json()
    assert refreshed["look_count"] == 1
    assert refreshed["default_look"]["id"] == look["id"]


def test_update_look_patch_null_and_unsubmitted_fields(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    look = create_look(
        migrated_client,
        str(project["id"]),
        str(character["id"]),
        costume_description="Keep costume",
        hair_description="Clear hair",
    )

    response = migrated_client.patch(
        f"/api/projects/{project['id']}/characters/{character['id']}/looks/{look['id']}",
        json={"name": "Updated Look", "hair_description": None},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Look"
    assert data["hair_description"] is None
    assert data["costume_description"] == "Keep costume"


def test_look_default_can_be_switched(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    first = create_look(migrated_client, str(project["id"]), str(character["id"]), name="First")
    second = create_look(migrated_client, str(project["id"]), str(character["id"]), name="Second")

    response = migrated_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}/looks/{second['id']}/set-default"
    )

    assert response.status_code == 200
    assert response.json()["is_default"] is True
    looks = migrated_client.get(
        f"/api/projects/{project['id']}/characters/{character['id']}/looks"
    ).json()["items"]
    default_ids = [look["id"] for look in looks if look["is_default"]]
    assert default_ids == [second["id"]]
    assert first["id"] not in default_ids


def test_cannot_delete_last_look(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    look = create_look(migrated_client, str(project["id"]), str(character["id"]))

    response = migrated_client.delete(
        f"/api/projects/{project['id']}/characters/{character['id']}/looks/{look['id']}"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "LAST_LOOK_DELETE_FORBIDDEN"


def test_delete_default_look_selects_earliest_remaining_default(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    first = create_look(migrated_client, str(project["id"]), str(character["id"]), name="First")
    second = create_look(migrated_client, str(project["id"]), str(character["id"]), name="Second")
    third = create_look(migrated_client, str(project["id"]), str(character["id"]), name="Third")

    response = migrated_client.delete(
        f"/api/projects/{project['id']}/characters/{character['id']}/looks/{first['id']}"
    )

    assert response.status_code == 204
    assert response.content == b""
    looks = migrated_client.get(
        f"/api/projects/{project['id']}/characters/{character['id']}/looks"
    ).json()["items"]
    default_ids = [look["id"] for look in looks if look["is_default"]]
    assert default_ids == [second["id"]]
    assert third["id"] not in default_ids


def test_upload_reference_creates_media_and_analysis_defaults(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    look = create_look(migrated_client, str(project["id"]), str(character["id"]))

    reference = upload_reference(
        migrated_client,
        str(project["id"]),
        str(character["id"]),
        str(look["id"]),
    )

    assert reference["is_primary"] is True
    assert reference["is_identity_anchor"] is True
    assert reference["tags"] == ["identity", "studio"]
    assert reference["analysis_status"] == "not_analyzed"
    assert reference["suggestion_review_status"] == "not_reviewed"
    assert reference["analysis_suggestions"] is None
    assert reference["media_asset"]["thumbnail_url"].startswith("/api/media/")
    assert reference["media_asset"]["content_url"].startswith("/api/media/")
    assert "relative_path" not in reference["media_asset"]
    assert "stored_filename" not in reference["media_asset"]


def test_media_content_and_thumbnail_are_served(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    look = create_look(migrated_client, str(project["id"]), str(character["id"]))
    reference = upload_reference(
        migrated_client,
        str(project["id"]),
        str(character["id"]),
        str(look["id"]),
    )

    thumbnail = migrated_client.get(reference["media_asset"]["thumbnail_url"])
    content = migrated_client.get(reference["media_asset"]["content_url"])

    assert thumbnail.status_code == 200
    assert thumbnail.headers["content-type"] == "image/webp"
    assert content.status_code == 200
    assert content.headers["content-type"] == "image/png"


def test_update_reference_metadata_patch_rules(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    look = create_look(migrated_client, str(project["id"]), str(character["id"]))
    reference = upload_reference(
        migrated_client,
        str(project["id"]),
        str(character["id"]),
        str(look["id"]),
    )

    response = migrated_client.patch(
        (
            f"/api/projects/{project['id']}/characters/{character['id']}"
            f"/looks/{look['id']}/references/{reference['id']}"
        ),
        json={
            "view_angle": "left_45",
            "custom_expression": "subtle worry",
            "description": None,
            "tags": [],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["shot_type"] == "closeup"
    assert data["view_angle"] == "left_45"
    assert data["custom_expression"] == "subtle worry"
    assert data["description"] is None
    assert data["tags"] == []
    assert data["analysis_suggestions"] is None


def test_set_primary_and_identity_anchor_are_independent(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    look = create_look(migrated_client, str(project["id"]), str(character["id"]))
    first = upload_reference(
        migrated_client,
        str(project["id"]),
        str(character["id"]),
        str(look["id"]),
    )
    second = upload_reference(
        migrated_client,
        str(project["id"]),
        str(character["id"]),
        str(look["id"]),
        description="Second",
    )

    clear_anchor = migrated_client.patch(
        (
            f"/api/projects/{project['id']}/characters/{character['id']}"
            f"/looks/{look['id']}/references/{first['id']}"
        ),
        json={"is_identity_anchor": False},
    )
    set_primary = migrated_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{second['id']}/set-primary"
    )

    assert clear_anchor.status_code == 200
    assert clear_anchor.json()["is_primary"] is True
    assert clear_anchor.json()["is_identity_anchor"] is False
    assert set_primary.status_code == 200
    assert set_primary.json()["is_primary"] is True
    assert set_primary.json()["is_identity_anchor"] is True


def test_delete_primary_reference_selects_next_primary(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    look = create_look(migrated_client, str(project["id"]), str(character["id"]))
    first = upload_reference(
        migrated_client,
        str(project["id"]),
        str(character["id"]),
        str(look["id"]),
    )
    second = upload_reference(
        migrated_client,
        str(project["id"]),
        str(character["id"]),
        str(look["id"]),
        description="Second",
    )

    response = migrated_client.delete(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{first['id']}"
    )

    assert response.status_code == 204
    assert response.content == b""
    references = migrated_client.get(
        f"/api/projects/{project['id']}/characters/{character['id']}/looks/{look['id']}/references"
    ).json()["items"]
    primary_ids = [reference["id"] for reference in references if reference["is_primary"]]
    assert primary_ids == [second["id"]]


def test_delete_reference_cleans_files_and_missing_files_are_success(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    look = create_look(migrated_client, str(project["id"]), str(character["id"]))
    reference = upload_reference(
        migrated_client, str(project["id"]), str(character["id"]), str(look["id"])
    )
    files = get_storage_files()
    assert files
    for path in files:
        path.unlink()

    response = migrated_client.delete(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}"
    )

    assert response.status_code == 204
    assert response.content == b""


def test_file_cleanup_failure_returns_204_without_path_leak(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    look = create_look(migrated_client, str(project["id"]), str(character["id"]))
    reference = upload_reference(
        migrated_client, str(project["id"]), str(character["id"]), str(look["id"])
    )

    def fail_delete(self: MediaStorageService, relative_path: str | None) -> None:
        raise AppError(
            code="IMAGE_UPLOAD_FAILED",
            message="C:/secret/path/reference.png",
            status_code=500,
        )

    monkeypatch.setattr(MediaStorageService, "delete_relative_file", fail_delete)

    response = migrated_client.delete(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}"
    )

    assert response.status_code == 204
    assert response.content == b""


def test_delete_character_cleans_media_assets_and_files(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    look = create_look(migrated_client, str(project["id"]), str(character["id"]))
    reference = upload_reference(
        migrated_client, str(project["id"]), str(character["id"]), str(look["id"])
    )
    files = get_storage_files()
    assert files

    response = migrated_client.delete(f"/api/projects/{project['id']}/characters/{character['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert migrated_client.get(reference["media_asset"]["content_url"]).status_code == 404
    assert not [path for path in files if path.exists()]


def test_cross_project_edit_and_delete_fail(migrated_client: TestClient) -> None:
    project_a = create_project(migrated_client, "Project A")
    project_b = create_project(migrated_client, "Project B")
    character = create_character(migrated_client, str(project_a["id"]))
    look = create_look(migrated_client, str(project_a["id"]), str(character["id"]))

    update_response = migrated_client.patch(
        f"/api/projects/{project_b['id']}/characters/{character['id']}",
        json={"name": "Wrong project"},
    )
    delete_response = migrated_client.delete(
        f"/api/projects/{project_b['id']}/characters/{character['id']}/looks/{look['id']}"
    )

    assert update_response.status_code == 404
    assert delete_response.status_code == 404


def test_storage_path_must_stay_inside_storage_root(migrated_client: TestClient) -> None:
    service = MediaStorageService()

    try:
        service.resolve_relative_path("../outside.png", must_exist=False)
    except AppError as exc:
        assert exc.code == "FILE_NOT_FOUND"
        assert ":\\" not in exc.message
        assert ":/" not in exc.message
    else:
        raise AssertionError("Expected path traversal to be rejected")


def test_upload_reference_rejects_invalid_extension(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    look = create_look(migrated_client, str(project["id"]), str(character["id"]))

    response = migrated_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}/looks/{look['id']}/references",
        files={"file": ("reference.gif", make_image_bytes(), "image/gif")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "IMAGE_EXTENSION_NOT_ALLOWED"


def test_upload_reference_rejects_corrupt_image(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    look = create_look(migrated_client, str(project["id"]), str(character["id"]))

    response = migrated_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}/looks/{look['id']}/references",
        files={"file": ("reference.png", b"not-an-image", "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "IMAGE_INVALID"


def test_character_persists_after_new_app_instance(
    migrated_client: TestClient,
) -> None:
    from app.main import create_app

    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))

    with TestClient(create_app()) as fresh_client:
        response = fresh_client.get(f"/api/projects/{project['id']}/characters/{character['id']}")

    assert response.status_code == 200
    assert response.json()["name"] == "Lead Character"
