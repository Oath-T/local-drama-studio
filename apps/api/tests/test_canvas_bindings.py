from fastapi.testclient import TestClient

from tests.test_asset_summaries import (
    create_character,
    create_look,
    create_project,
    create_scene,
    create_shot,
    create_state,
    upload_character_reference,
    upload_scene_reference,
)


def add_node(
    client: TestClient,
    project_id: str,
    revision: int,
    node_type: str,
    entity_id: str,
    title: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/projects/{project_id}/canvas/nodes",
        json={
            "expected_revision": revision,
            "node_type": node_type,
            "entity_type": node_type,
            "entity_id": entity_id,
            "title": title,
        },
    )
    assert response.status_code == 201
    return response.json()


def setup_canvas_nodes(client: TestClient) -> dict[str, object]:
    project = create_project(client, "Canvas Binding Project")
    project_id = str(project["id"])
    character = create_character(client, project_id, "Hero")
    look = create_look(client, project_id, str(character["id"]))
    character_ref = upload_character_reference(
        client, project_id, str(character["id"]), str(look["id"])
    )
    scene = create_scene(client, project_id, "Office")
    state = create_state(client, project_id, str(scene["id"]))
    scene_ref = upload_scene_reference(client, project_id, str(scene["id"]), str(state["id"]))
    shot = create_shot(client, project_id)
    canvas = client.get(f"/api/projects/{project_id}/canvas").json()
    canvas = add_node(
        client, project_id, canvas["revision"], "character", str(character["id"]), "Hero"
    )
    canvas = add_node(client, project_id, canvas["revision"], "scene", str(scene["id"]), "Office")
    canvas = add_node(client, project_id, canvas["revision"], "shot", str(shot["id"]), "Shot")
    canvas = add_node(
        client,
        project_id,
        canvas["revision"],
        "image",
        str(character_ref["media_asset"]["id"]),
        "Character Ref",
    )
    canvas = add_node(
        client,
        project_id,
        canvas["revision"],
        "image",
        str(scene_ref["media_asset"]["id"]),
        "Scene Ref",
    )
    nodes = {node["title"]: node for node in canvas["nodes"]}
    return {
        "project_id": project_id,
        "character": character,
        "look": look,
        "character_ref": character_ref,
        "scene": scene,
        "state": state,
        "scene_ref": scene_ref,
        "shot": shot,
        "canvas": canvas,
        "nodes": nodes,
    }


def apply_binding(
    client: TestClient, project_id: str, payload: dict[str, object]
) -> dict[str, object]:
    response = client.post(f"/api/projects/{project_id}/canvas/bindings/apply", json=payload)
    assert response.status_code == 200
    return response.json()


def test_character_to_shot_binding_is_idempotent_and_updates_look(
    migrated_client: TestClient,
) -> None:
    data = setup_canvas_nodes(migrated_client)
    project_id = str(data["project_id"])
    nodes = data["nodes"]

    first = apply_binding(
        migrated_client,
        project_id,
        {
            "expected_revision": data["canvas"]["revision"],
            "source_node_id": nodes["Hero"]["id"],
            "target_node_id": nodes["Shot"]["id"],
            "semantic_type": "uses_character",
            "payload": {
                "look_id": data["look"]["id"],
                "is_primary_subject": True,
                "action_description": "pushes the door open",
            },
        },
    )
    edge = first["edges"][0]
    assert edge["data"]["status"] == "applied"
    assert edge["data"]["business_entity_type"] == "shot_character"

    second = apply_binding(
        migrated_client,
        project_id,
        {
            "expected_revision": first["revision"],
            "edge_id": edge["id"],
            "source_node_id": nodes["Hero"]["id"],
            "target_node_id": nodes["Shot"]["id"],
            "semantic_type": "uses_character",
            "payload": {"look_id": None, "position_description": "doorway"},
        },
    )
    characters = migrated_client.get(
        f"/api/projects/{project_id}/shots/{data['shot']['id']}/characters"
    ).json()
    assert second["edges"][0]["data"]["status"] == "applied"
    assert characters["total"] == 1
    assert characters["items"][0]["look_id"] is None
    assert characters["items"][0]["position_description"] == "doorway"


def test_scene_binding_requires_replace_confirmation(migrated_client: TestClient) -> None:
    data = setup_canvas_nodes(migrated_client)
    project_id = str(data["project_id"])
    other_scene = create_scene(migrated_client, project_id, "Street")
    shot_id = str(data["shot"]["id"])
    patch = migrated_client.patch(
        f"/api/projects/{project_id}/shots/{shot_id}",
        json={"scene_id": other_scene["id"]},
    )
    assert patch.status_code == 200

    failed = apply_binding(
        migrated_client,
        project_id,
        {
            "expected_revision": data["canvas"]["revision"],
            "source_node_id": data["nodes"]["Office"]["id"],
            "target_node_id": data["nodes"]["Shot"]["id"],
            "semantic_type": "uses_scene",
            "payload": {"scene_state_id": data["state"]["id"]},
        },
    )
    assert failed["edges"][0]["data"]["status"] == "failed"

    applied = apply_binding(
        migrated_client,
        project_id,
        {
            "expected_revision": failed["revision"],
            "edge_id": failed["edges"][0]["id"],
            "source_node_id": data["nodes"]["Office"]["id"],
            "target_node_id": data["nodes"]["Shot"]["id"],
            "semantic_type": "uses_scene",
            "payload": {"scene_state_id": data["state"]["id"], "replace_existing_scene": True},
        },
    )
    shot = migrated_client.get(f"/api/projects/{project_id}/shots/{shot_id}").json()
    assert applied["edges"][0]["data"]["status"] == "applied"
    assert shot["scene_id"] == data["scene"]["id"]
    assert shot["scene_state_id"] == data["state"]["id"]


def test_image_to_shot_reference_and_unbind(migrated_client: TestClient) -> None:
    data = setup_canvas_nodes(migrated_client)
    project_id = str(data["project_id"])
    nodes = data["nodes"]
    character_edge = apply_binding(
        migrated_client,
        project_id,
        {
            "expected_revision": data["canvas"]["revision"],
            "source_node_id": nodes["Hero"]["id"],
            "target_node_id": nodes["Shot"]["id"],
            "semantic_type": "uses_character",
            "payload": {"look_id": data["look"]["id"]},
        },
    )
    shot_character_id = character_edge["edges"][0]["data"]["business_entity_id"]
    reference_canvas = apply_binding(
        migrated_client,
        project_id,
        {
            "expected_revision": character_edge["revision"],
            "source_node_id": nodes["Character Ref"]["id"],
            "target_node_id": nodes["Shot"]["id"],
            "semantic_type": "identity_reference",
            "payload": {"shot_character_id": shot_character_id},
        },
    )
    edge = next(
        edge for edge in reference_canvas["edges"] if edge["semantic_type"] == "identity_reference"
    )
    references = migrated_client.get(
        f"/api/projects/{project_id}/shots/{data['shot']['id']}/references"
    ).json()
    assert references["total"] == 1
    assert references["items"][0]["purpose"] == "identity"

    deleted = migrated_client.request(
        "DELETE",
        f"/api/projects/{project_id}/canvas/bindings/{edge['id']}",
        json={"expected_revision": reference_canvas["revision"], "mode": "unbind_business"},
    )
    assert deleted.status_code == 200
    references_after = migrated_client.get(
        f"/api/projects/{project_id}/shots/{data['shot']['id']}/references"
    ).json()
    assert references_after["total"] == 0


def test_scene_reference_and_video_input_binding(migrated_client: TestClient) -> None:
    data = setup_canvas_nodes(migrated_client)
    project_id = str(data["project_id"])
    nodes = data["nodes"]
    scene_bound = apply_binding(
        migrated_client,
        project_id,
        {
            "expected_revision": data["canvas"]["revision"],
            "source_node_id": nodes["Office"]["id"],
            "target_node_id": nodes["Shot"]["id"],
            "semantic_type": "uses_scene",
            "payload": {"scene_state_id": data["state"]["id"]},
        },
    )
    scene_reference_bound = apply_binding(
        migrated_client,
        project_id,
        {
            "expected_revision": scene_bound["revision"],
            "source_node_id": nodes["Scene Ref"]["id"],
            "target_node_id": nodes["Shot"]["id"],
            "semantic_type": "scene_reference",
            "payload": {},
        },
    )
    assert scene_reference_bound["edges"][-1]["data"]["status"] == "applied"

    task = migrated_client.post(
        f"/api/projects/{project_id}/shots/{data['shot']['id']}/video-tasks",
        json={},
    ).json()
    video_bound = apply_binding(
        migrated_client,
        project_id,
        {
            "expected_revision": scene_reference_bound["revision"],
            "source_node_id": nodes["Character Ref"]["id"],
            "target_node_id": nodes["Shot"]["id"],
            "semantic_type": "start_frame",
            "payload": {"video_task_id": task["id"]},
        },
    )
    refreshed_task = migrated_client.get(
        f"/api/projects/{project_id}/video-tasks/{task['id']}"
    ).json()
    assert video_bound["edges"][-1]["data"]["business_entity_type"] == "video_task_input"
    assert refreshed_task["inputs"][0]["role"] == "start_frame"
    assert (
        refreshed_task["inputs"][0]["media_asset_id"] == data["character_ref"]["media_asset"]["id"]
    )


def test_draft_edge_does_not_modify_business_and_cross_project_is_rejected(
    migrated_client: TestClient,
) -> None:
    data = setup_canvas_nodes(migrated_client)
    project_id = str(data["project_id"])
    draft = apply_binding(
        migrated_client,
        project_id,
        {
            "expected_revision": data["canvas"]["revision"],
            "source_node_id": data["nodes"]["Hero"]["id"],
            "target_node_id": data["nodes"]["Shot"]["id"],
            "semantic_type": "uses_character",
            "apply_business": False,
            "payload": {},
        },
    )
    assert draft["edges"][0]["data"]["status"] == "draft"
    characters = migrated_client.get(
        f"/api/projects/{project_id}/shots/{data['shot']['id']}/characters"
    ).json()
    assert characters["total"] == 0

    other = create_project(migrated_client, "Other Project")
    response = migrated_client.post(
        f"/api/projects/{other['id']}/canvas/bindings/preview",
        json={
            "source_node_id": data["nodes"]["Hero"]["id"],
            "target_node_id": data["nodes"]["Shot"]["id"],
            "semantic_type": "uses_character",
            "payload": {},
        },
    )
    assert response.status_code == 404


def test_binding_relation_matrix_rejects_invalid_connections_without_creating_edges(
    migrated_client: TestClient,
) -> None:
    data = setup_canvas_nodes(migrated_client)
    project_id = str(data["project_id"])
    nodes = data["nodes"]
    second_shot = create_shot(migrated_client, project_id, name="Second Shot")
    canvas = add_node(
        migrated_client,
        project_id,
        data["canvas"]["revision"],
        "shot",
        str(second_shot["id"]),
        "Second Shot",
    )
    nodes = {node["title"]: node for node in canvas["nodes"]}

    preview = migrated_client.post(
        f"/api/projects/{project_id}/canvas/bindings/preview",
        json={
            "source_node_id": nodes["Office"]["id"],
            "target_node_id": nodes["Hero"]["id"],
            "semantic_type": "continuity_from",
            "payload": {},
        },
    )
    assert preview.status_code == 200
    assert preview.json()["can_apply"] is False
    assert preview.json()["summary"] == "这两类节点目前不能直接连接。"

    invalid = migrated_client.post(
        f"/api/projects/{project_id}/canvas/bindings/apply",
        json={
            "expected_revision": canvas["revision"],
            "source_node_id": nodes["Office"]["id"],
            "target_node_id": nodes["Hero"]["id"],
            "semantic_type": "continuity_from",
            "apply_business": False,
            "payload": {},
        },
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["message"] == "这两类节点目前不能直接连接。"
    after_invalid = migrated_client.get(f"/api/projects/{project_id}/canvas").json()
    assert after_invalid["edges"] == []

    continuity = apply_binding(
        migrated_client,
        project_id,
        {
            "expected_revision": after_invalid["revision"],
            "source_node_id": nodes["Shot"]["id"],
            "target_node_id": nodes["Second Shot"]["id"],
            "semantic_type": "continuity_from",
            "apply_business": False,
            "payload": {},
        },
    )
    assert continuity["edges"][0]["semantic_type"] == "continuity_from"
    assert continuity["edges"][0]["data"]["status"] == "draft"

    generated = migrated_client.post(
        f"/api/projects/{project_id}/canvas/bindings/apply",
        json={
            "expected_revision": continuity["revision"],
            "source_node_id": nodes["Shot"]["id"],
            "target_node_id": nodes["Second Shot"]["id"],
            "semantic_type": "generated_from",
            "apply_business": False,
            "payload": {},
        },
    )
    assert generated.status_code == 422
    assert generated.json()["error"]["message"] == "生成来源关系只能由系统建立。"
    after_generated = migrated_client.get(f"/api/projects/{project_id}/canvas").json()
    assert len(after_generated["edges"]) == 1
