from fastapi.testclient import TestClient

from app.main import create_app


def create_project(client: TestClient, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "逆袭归来",
        "description": "都市逆袭题材短剧",
        "aspect_ratio": "9:16",
        "default_style": "写实电影质感",
        "default_language": "zh-CN",
        "default_fps": 24,
    }
    payload.update(overrides)
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 201
    return response.json()


def test_empty_project_list_returns_success(migrated_client: TestClient) -> None:
    response = migrated_client.get("/api/projects")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_create_valid_project_success(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)

    assert project["name"] == "逆袭归来"
    assert project["description"] == "都市逆袭题材短剧"
    assert project["cover_image_path"] is None
    assert isinstance(project["id"], str)
    assert project["created_at"].endswith("Z")
    assert project["updated_at"].endswith("Z")


def test_create_project_uses_default_fields(migrated_client: TestClient) -> None:
    response = migrated_client.post("/api/projects", json={"name": "默认配置项目"})

    assert response.status_code == 201
    data = response.json()
    assert data["aspect_ratio"] == "9:16"
    assert data["default_language"] == "zh-CN"
    assert data["default_fps"] == 24


def test_empty_name_create_fails(migrated_client: TestClient) -> None:
    response = migrated_client.post("/api/projects", json={"name": ""})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_whitespace_name_create_fails(migrated_client: TestClient) -> None:
    response = migrated_client.post("/api/projects", json={"name": "   "})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PROJECT_NAME_REQUIRED"


def test_too_long_name_create_fails(migrated_client: TestClient) -> None:
    response = migrated_client.post("/api/projects", json={"name": "项" * 101})

    assert response.status_code == 422


def test_invalid_aspect_ratio_fails(migrated_client: TestClient) -> None:
    response = migrated_client.post("/api/projects", json={"name": "测试", "aspect_ratio": "2:1"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_ASPECT_RATIO"


def test_invalid_default_language_fails(migrated_client: TestClient) -> None:
    response = migrated_client.post(
        "/api/projects",
        json={"name": "测试", "default_language": "fr-FR"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_DEFAULT_LANGUAGE"


def test_invalid_default_fps_fails(migrated_client: TestClient) -> None:
    response = migrated_client.post("/api/projects", json={"name": "测试", "default_fps": 60})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_DEFAULT_FPS"


def test_get_existing_project_success(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)

    response = migrated_client.get(f"/api/projects/{project['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == project["id"]


def test_get_missing_project_returns_404(migrated_client: TestClient) -> None:
    response = migrated_client.get("/api/projects/00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_invalid_project_id_returns_safe_error(migrated_client: TestClient) -> None:
    response = migrated_client.get("/api/projects/not-a-uuid")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PROJECT_ID"


def test_partial_update_project_success(migrated_client: TestClient) -> None:
    project = create_project(migrated_client, description="旧简介", default_style="旧风格")

    response = migrated_client.patch(
        f"/api/projects/{project['id']}",
        json={"name": "更新后的项目"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "更新后的项目"
    assert data["description"] == "旧简介"
    assert data["default_style"] == "旧风格"


def test_patch_null_clears_nullable_fields(migrated_client: TestClient) -> None:
    project = create_project(migrated_client, description="旧简介", default_style="旧风格")

    response = migrated_client.patch(
        f"/api/projects/{project['id']}",
        json={"description": None, "default_style": None},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["description"] is None
    assert data["default_style"] is None


def test_update_missing_project_returns_404(migrated_client: TestClient) -> None:
    response = migrated_client.patch(
        "/api/projects/00000000-0000-4000-8000-000000000000",
        json={"name": "不存在"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_delete_project_success(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)

    response = migrated_client.delete(f"/api/projects/{project['id']}")

    assert response.status_code == 204
    assert response.content == b""


def test_delete_missing_project_returns_404(migrated_client: TestClient) -> None:
    response = migrated_client.delete("/api/projects/00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_project_list_uses_stable_sorting(migrated_client: TestClient) -> None:
    first = create_project(migrated_client, name="第一")
    create_project(migrated_client, name="第二")
    migrated_client.patch(f"/api/projects/{first['id']}", json={"description": "触发更新时间"})

    response = migrated_client.get("/api/projects")

    assert response.status_code == 200
    names = [item["name"] for item in response.json()["items"]]
    assert names == ["第一", "第二"]


def test_default_language_is_zh_cn(migrated_client: TestClient) -> None:
    project = create_project(migrated_client, name="语言默认项目")

    assert project["default_language"] == "zh-CN"


def test_project_persists_after_new_app_instance(migrated_client: TestClient) -> None:
    project = create_project(migrated_client, name="持久化项目")

    with TestClient(create_app()) as fresh_client:
        response = fresh_client.get(f"/api/projects/{project['id']}")

    assert response.status_code == 200
    assert response.json()["name"] == "持久化项目"
