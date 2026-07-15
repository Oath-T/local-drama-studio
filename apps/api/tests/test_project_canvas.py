from fastapi.testclient import TestClient


def create_project(client: TestClient, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "画布测试项目",
        "description": "项目画布测试",
        "aspect_ratio": "9:16",
        "default_style": "写实",
        "default_language": "zh-CN",
        "default_fps": 24,
    }
    payload.update(overrides)
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 201
    return response.json()


def create_character(
    client: TestClient, project_id: str, name: str = "画布角色"
) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/characters",
        json={"name": name, "role_type": "supporting"},
    )
    assert response.status_code == 201
    return response.json()


def test_canvas_first_read_creates_empty_canvas(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)

    response = migrated_client.get(f"/api/projects/{project['id']}/canvas")

    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project["id"]
    assert data["view_mode"] == "workflow"
    assert data["revision"] == 1
    assert data["nodes"] == []
    assert data["edges"] == []


def test_canvas_save_updates_viewport_and_revision(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    canvas = migrated_client.get(f"/api/projects/{project['id']}/canvas").json()

    response = migrated_client.put(
        f"/api/projects/{project['id']}/canvas",
        json={
            "expected_revision": canvas["revision"],
            "view_mode": "storyboard",
            "viewport": {"x": 120, "y": -40, "zoom": 0.8},
            "nodes": [
                {
                    "node_type": "text",
                    "title": "开场备注",
                    "position_x": 10,
                    "position_y": 20,
                    "width": 260,
                    "height": 140,
                    "data": {"note": "从这里开始创作"},
                }
            ],
            "edges": [],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["view_mode"] == "storyboard"
    assert data["viewport"] == {"x": 120.0, "y": -40.0, "zoom": 0.8}
    assert data["revision"] == 2
    assert data["nodes"][0]["data"]["note"] == "从这里开始创作"


def test_canvas_revision_conflict_is_rejected(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    canvas = migrated_client.get(f"/api/projects/{project['id']}/canvas").json()

    first = migrated_client.post(
        f"/api/projects/{project['id']}/canvas/nodes",
        json={"expected_revision": canvas["revision"], "node_type": "text", "title": "A"},
    )
    assert first.status_code == 201

    response = migrated_client.post(
        f"/api/projects/{project['id']}/canvas/nodes",
        json={"expected_revision": canvas["revision"], "node_type": "text", "title": "B"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PROJECT_CANVAS_REVISION_CONFLICT"


def test_node_crud_and_delete_cascades_edges(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    canvas = migrated_client.get(f"/api/projects/{project['id']}/canvas").json()
    first = migrated_client.post(
        f"/api/projects/{project['id']}/canvas/nodes",
        json={"expected_revision": canvas["revision"], "node_type": "text", "title": "A"},
    ).json()
    second = migrated_client.post(
        f"/api/projects/{project['id']}/canvas/nodes",
        json={"expected_revision": first["revision"], "node_type": "text", "title": "B"},
    ).json()
    first_node_id = second["nodes"][0]["id"]
    second_node_id = second["nodes"][1]["id"]

    patched = migrated_client.patch(
        f"/api/projects/{project['id']}/canvas/nodes/{first_node_id}",
        json={
            "expected_revision": second["revision"],
            "position_x": 300,
            "position_y": 120,
            "width": 280,
            "height": 180,
            "data": {"collapsed": True},
        },
    )
    assert patched.status_code == 200
    assert patched.json()["nodes"][0]["position_x"] == 300

    edge_response = migrated_client.post(
        f"/api/projects/{project['id']}/canvas/edges",
        json={
            "expected_revision": patched.json()["revision"],
            "source_node_id": first_node_id,
            "target_node_id": second_node_id,
            "semantic_type": "continuity_from",
        },
    )
    assert edge_response.status_code == 201
    assert len(edge_response.json()["edges"]) == 1

    deleted = migrated_client.delete(
        f"/api/projects/{project['id']}/canvas/nodes/{first_node_id}"
        f"?expected_revision={edge_response.json()['revision']}"
    )
    assert deleted.status_code == 200
    assert len(deleted.json()["nodes"]) == 1
    assert deleted.json()["edges"] == []


def test_invalid_node_and_edge_types_are_rejected(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    canvas = migrated_client.get(f"/api/projects/{project['id']}/canvas").json()

    invalid_node = migrated_client.post(
        f"/api/projects/{project['id']}/canvas/nodes",
        json={"expected_revision": canvas["revision"], "node_type": "comfyui", "title": "bad"},
    )
    assert invalid_node.status_code == 422

    first = migrated_client.post(
        f"/api/projects/{project['id']}/canvas/nodes",
        json={"expected_revision": canvas["revision"], "node_type": "text", "title": "A"},
    ).json()
    second = migrated_client.post(
        f"/api/projects/{project['id']}/canvas/nodes",
        json={"expected_revision": first["revision"], "node_type": "text", "title": "B"},
    ).json()
    invalid_edge = migrated_client.post(
        f"/api/projects/{project['id']}/canvas/edges",
        json={
            "expected_revision": second["revision"],
            "source_node_id": second["nodes"][0]["id"],
            "target_node_id": second["nodes"][1]["id"],
            "semantic_type": "generates_money",
        },
    )
    assert invalid_edge.status_code == 422


def test_cross_project_entity_is_rejected(migrated_client: TestClient) -> None:
    first_project = create_project(migrated_client, name="项目 A")
    second_project = create_project(migrated_client, name="项目 B")
    foreign_character = create_character(migrated_client, str(second_project["id"]))
    canvas = migrated_client.get(f"/api/projects/{first_project['id']}/canvas").json()

    response = migrated_client.post(
        f"/api/projects/{first_project['id']}/canvas/nodes",
        json={
            "expected_revision": canvas["revision"],
            "node_type": "character",
            "entity_type": "character",
            "entity_id": foreign_character["id"],
            "title": "不应允许",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_CANVAS_ENTITY"


def test_project_isolation_and_batch_preview(migrated_client: TestClient) -> None:
    first_project = create_project(migrated_client, name="项目 A")
    second_project = create_project(migrated_client, name="项目 B")
    create_character(migrated_client, str(first_project["id"]))

    first_preview = migrated_client.get(
        f"/api/projects/{first_project['id']}/canvas/entity-batch-preview"
    )
    second_preview = migrated_client.get(
        f"/api/projects/{second_project['id']}/canvas/entity-batch-preview"
    )

    assert first_preview.status_code == 200
    assert second_preview.status_code == 200
    assert first_preview.json()["character_count"] == 1
    assert second_preview.json()["character_count"] == 0


def test_canvas_does_not_modify_business_entities(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    character = create_character(migrated_client, str(project["id"]))
    before = migrated_client.get(f"/api/projects/{project['id']}/characters").json()
    canvas = migrated_client.get(f"/api/projects/{project['id']}/canvas").json()

    response = migrated_client.post(
        f"/api/projects/{project['id']}/canvas/nodes",
        json={
            "expected_revision": canvas["revision"],
            "node_type": "character",
            "entity_type": "character",
            "entity_id": character["id"],
            "title": "画布上的角色",
        },
    )
    after = migrated_client.get(f"/api/projects/{project['id']}/characters").json()

    assert response.status_code == 201
    assert before == after
