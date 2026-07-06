from fastapi.testclient import TestClient

from tests.test_keyframe_tasks import (
    create_keyframe_task,
    create_project,
    create_ready_shot_fixture,
)


def test_project_generation_tasks_include_keyframe_and_video_summaries(
    migrated_client: TestClient,
) -> None:
    data = create_ready_shot_fixture(migrated_client)
    keyframe_task = create_keyframe_task(
        migrated_client,
        data["project_id"],
        str(data["shot"]["id"]),
    )
    video_response = migrated_client.post(
        f"/api/projects/{data['project_id']}/shots/{data['shot']['id']}/video-tasks",
        json={},
    )
    assert video_response.status_code == 201
    video_task = video_response.json()

    response = migrated_client.get(f"/api/projects/{data['project_id']}/generation-tasks")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    items_by_id = {item["task_id"]: item for item in payload["items"]}
    assert items_by_id[keyframe_task["id"]]["task_type"] == "keyframe"
    assert items_by_id[keyframe_task["id"]]["shot_name"] == data["shot"]["name"]
    assert items_by_id[keyframe_task["id"]]["run_count"] == 0
    assert items_by_id[keyframe_task["id"]]["has_outputs"] is False
    assert items_by_id[video_task["id"]]["task_type"] == "video"
    assert items_by_id[video_task["id"]]["workflow_id"] == video_task["workflow_id"]
    assert items_by_id[video_task["id"]]["has_selected_output"] is False


def test_project_generation_tasks_are_project_scoped(migrated_client: TestClient) -> None:
    first = create_ready_shot_fixture(migrated_client)
    create_keyframe_task(migrated_client, first["project_id"], str(first["shot"]["id"]))
    second_project = create_project(migrated_client, "Empty Project")

    response = migrated_client.get(f"/api/projects/{second_project['id']}/generation-tasks")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_project_generation_tasks_reject_missing_project(migrated_client: TestClient) -> None:
    response = migrated_client.get(
        "/api/projects/00000000-0000-4000-8000-000000000000/generation-tasks"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "project_not_found"
