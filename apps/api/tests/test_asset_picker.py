from fastapi.testclient import TestClient
from sqlalchemy import select

from app.infrastructure.database import get_session_factory
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.keyframe_generation import (
    KeyframeGenerationOutputRecord,
    KeyframeGenerationRunRecord,
)
from app.infrastructure.models.keyframe_task import KeyframeGenerationTaskReferenceRecord
from app.infrastructure.models.shot import ShotReferenceRecord
from app.infrastructure.models.video_generation import (
    VideoGenerationRunRecord,
    VideoGenerationTaskRecord,
)
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


def test_picker_character_options_return_current_project_characters(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    other = create_project(migrated_client, "Other")
    project_id = str(project["id"])
    character = create_character(migrated_client, project_id, "Hero")
    look = create_look(migrated_client, project_id, str(character["id"]))
    upload_character_reference(migrated_client, project_id, str(character["id"]), str(look["id"]))
    create_character(migrated_client, str(other["id"]), "Other Hero")
    shot = create_shot(migrated_client, project_id)
    migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/characters",
        json={"character_id": character["id"], "look_id": look["id"]},
    )

    response = migrated_client.get(
        f"/api/projects/{project_id}/assets/picker-options",
        params={"scope": "shot", "asset_type": "character", "shot_id": shot["id"]},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == character["id"]
    assert payload["items"][0]["type"] == "character"
    assert payload["items"][0]["is_selected"] is True
    assert "已绑定" in payload["items"][0]["badges"]
    assert payload["items"][0]["thumbnail_url"].startswith("/api/media/")
    assert "relative_path" not in response.text
    assert "stored_filename" not in response.text


def test_picker_scene_options_return_current_project_scenes(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    project_id = str(project["id"])
    scene = create_scene(migrated_client, project_id, "Lobby")
    state = create_state(migrated_client, project_id, str(scene["id"]))
    upload_scene_reference(migrated_client, project_id, str(scene["id"]), str(state["id"]))
    shot = create_shot(migrated_client, project_id, scene_id=scene["id"])

    response = migrated_client.get(
        f"/api/projects/{project_id}/assets/picker-options",
        params={"scope": "shot", "asset_type": "scene", "shot_id": shot["id"]},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == scene["id"]
    assert payload["items"][0]["type"] == "scene"
    assert payload["items"][0]["is_selected"] is True
    assert "当前使用" in payload["items"][0]["badges"]
    assert "空间结构参考图" in payload["items"][0]["badges"]
    assert "relative_path" not in response.text


def test_picker_frame_image_options_return_current_shot_images(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    project_id = str(project["id"])
    character = create_character(migrated_client, project_id)
    look = create_look(migrated_client, project_id, str(character["id"]))
    reference = upload_character_reference(
        migrated_client, project_id, str(character["id"]), str(look["id"])
    )
    shot = create_shot(migrated_client, project_id)
    shot_character = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/characters",
        json={"character_id": character["id"], "look_id": look["id"]},
    ).json()
    migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/references",
        json={
            "reference_type": "character",
            "character_reference_id": reference["id"],
            "shot_character_id": shot_character["id"],
            "purpose": "identity",
        },
    )

    response = migrated_client.get(
        f"/api/projects/{project_id}/assets/picker-options",
        params={"scope": "shot", "asset_type": "frame_image", "shot_id": shot["id"]},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["total"] == 1
    item = payload["items"][0]
    assert item["type"] == "frame_image"
    assert item["content_url"].startswith("/api/media/")
    assert item["metadata"]["media_asset_id"] == reference["media_asset_id"]
    assert "镜头人物参考图" in item["badges"]
    assert "relative_path" not in response.text
    assert "stored_filename" not in response.text
    assert "base64" not in response.text.lower()


def test_picker_search_limit_empty_and_cross_project_scope(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    other = create_project(migrated_client, "Other")
    project_id = str(project["id"])
    create_character(migrated_client, project_id, "Alpha Lead")
    create_character(migrated_client, project_id, "Beta Guard")
    other_shot = create_shot(migrated_client, str(other["id"]))

    searched = migrated_client.get(
        f"/api/projects/{project_id}/assets/picker-options",
        params={"asset_type": "character", "q": "alpha", "limit": 1},
    )
    empty = migrated_client.get(
        f"/api/projects/{project_id}/assets/picker-options",
        params={"asset_type": "scene", "q": "missing"},
    )
    cross_project = migrated_client.get(
        f"/api/projects/{project_id}/assets/picker-options",
        params={
            "scope": "shot",
            "asset_type": "character",
            "shot_id": other_shot["id"],
        },
    )

    assert searched.status_code == 200
    assert searched.json()["total"] == 1
    assert searched.json()["items"][0]["name"] == "Alpha Lead"
    assert empty.status_code == 200
    assert empty.json() == {"items": [], "total": 0}
    assert cross_project.status_code == 404
    assert cross_project.json()["error"]["code"] == "SHOT_NOT_FOUND"


def test_picker_options_are_read_only(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    project_id = str(project["id"])
    character = create_character(migrated_client, project_id)
    look = create_look(migrated_client, project_id, str(character["id"]))
    upload_character_reference(migrated_client, project_id, str(character["id"]), str(look["id"]))

    with get_session_factory()() as session:
        before_media = len(list(session.scalars(select(MediaAssetRecord)).all()))
        before_tasks = len(list(session.scalars(select(VideoGenerationTaskRecord)).all()))
        before_runs = len(list(session.scalars(select(VideoGenerationRunRecord)).all()))
        before_keyframe_runs = len(list(session.scalars(select(KeyframeGenerationRunRecord)).all()))
        before_keyframe_outputs = len(
            list(session.scalars(select(KeyframeGenerationOutputRecord)).all())
        )

    response = migrated_client.get(
        f"/api/projects/{project_id}/assets/picker-options",
        params={"asset_type": "character"},
    )

    with get_session_factory()() as session:
        after_media = len(list(session.scalars(select(MediaAssetRecord)).all()))
        after_tasks = len(list(session.scalars(select(VideoGenerationTaskRecord)).all()))
        after_runs = len(list(session.scalars(select(VideoGenerationRunRecord)).all()))
        after_keyframe_runs = len(list(session.scalars(select(KeyframeGenerationRunRecord)).all()))
        after_keyframe_outputs = len(
            list(session.scalars(select(KeyframeGenerationOutputRecord)).all())
        )

    assert response.status_code == 200
    assert after_media == before_media
    assert after_tasks == before_tasks
    assert after_runs == before_runs
    assert after_keyframe_runs == before_keyframe_runs
    assert after_keyframe_outputs == before_keyframe_outputs


def test_picker_character_look_options_return_character_looks(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    other = create_project(migrated_client, "Other")
    project_id = str(project["id"])
    character = create_character(migrated_client, project_id, "Hero")
    look = create_look(migrated_client, project_id, str(character["id"]))
    upload_character_reference(migrated_client, project_id, str(character["id"]), str(look["id"]))
    create_character(migrated_client, str(other["id"]), "Other Hero")
    shot = create_shot(migrated_client, project_id)
    shot_character = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/characters",
        json={"character_id": character["id"], "look_id": look["id"]},
    ).json()

    response = migrated_client.get(
        f"/api/projects/{project_id}/assets/picker-options",
        params={
            "asset_type": "character_look",
            "character_id": character["id"],
            "shot_id": shot["id"],
            "shot_character_id": shot_character["id"],
            "q": "default",
        },
    )
    missing = migrated_client.get(
        f"/api/projects/{project_id}/assets/picker-options",
        params={"asset_type": "character_look"},
    )
    cross_project = migrated_client.get(
        f"/api/projects/{other['id']}/assets/picker-options",
        params={"asset_type": "character_look", "character_id": character["id"]},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == look["id"]
    assert payload["items"][0]["type"] == "character_look"
    assert payload["items"][0]["is_selected"] is True
    assert "当前使用" in payload["items"][0]["badges"]
    assert payload["items"][0]["metadata"]["reference_count"] == 1
    assert payload["items"][0]["thumbnail_url"].startswith("/api/media/")
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "CHARACTER_ID_REQUIRED"
    assert cross_project.status_code == 404
    assert "relative_path" not in response.text
    assert "stored_filename" not in response.text
    assert "base64" not in response.text.lower()


def test_picker_scene_state_options_return_scene_states(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    other = create_project(migrated_client, "Other")
    project_id = str(project["id"])
    scene = create_scene(migrated_client, project_id, "Lobby")
    state = create_state(migrated_client, project_id, str(scene["id"]))
    upload_scene_reference(migrated_client, project_id, str(scene["id"]), str(state["id"]))
    shot = create_shot(
        migrated_client,
        project_id,
        scene_id=scene["id"],
        scene_state_id=state["id"],
    )

    response = migrated_client.get(
        f"/api/projects/{project_id}/assets/picker-options",
        params={
            "asset_type": "scene_state",
            "scene_id": scene["id"],
            "shot_id": shot["id"],
            "q": "night",
            "limit": 1,
        },
    )
    missing = migrated_client.get(
        f"/api/projects/{project_id}/assets/picker-options",
        params={"asset_type": "scene_state"},
    )
    cross_project = migrated_client.get(
        f"/api/projects/{other['id']}/assets/picker-options",
        params={"asset_type": "scene_state", "scene_id": scene["id"]},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == state["id"]
    assert payload["items"][0]["type"] == "scene_state"
    assert payload["items"][0]["is_selected"] is True
    assert "当前使用" in payload["items"][0]["badges"]
    assert payload["items"][0]["metadata"]["reference_count"] == 1
    assert payload["items"][0]["thumbnail_url"].startswith("/api/media/")
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "SCENE_ID_REQUIRED"
    assert cross_project.status_code == 404
    assert "relative_path" not in response.text
    assert "stored_filename" not in response.text
    assert "base64" not in response.text.lower()


def test_picker_reference_image_options_return_shot_context_and_task_state(
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
    shot_reference = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/references",
        json={
            "reference_type": "character",
            "character_reference_id": character_reference["id"],
            "shot_character_id": shot_character["id"],
            "purpose": "identity",
        },
    ).json()
    task = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/keyframe-tasks",
        json={"copy_current_references": False},
    ).json()
    empty_task = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/keyframe-tasks",
        json={"copy_current_references": False},
    ).json()
    migrated_client.post(
        f"/api/projects/{project_id}/keyframe-tasks/{task['id']}/references",
        json={"shot_reference_id": shot_reference["id"], "purpose": "identity"},
    )

    response = migrated_client.get(
        f"/api/projects/{project_id}/assets/picker-options",
        params={
            "scope": "shot",
            "asset_type": "reference_image",
            "source": "shot_context",
            "shot_id": shot["id"],
            "task_id": task["id"],
            "limit": 10,
        },
    )
    missing = migrated_client.get(
        f"/api/projects/{project_id}/assets/picker-options",
        params={"asset_type": "reference_image"},
    )
    payload = response.json()
    empty_task_response = migrated_client.get(
        f"/api/projects/{project_id}/assets/picker-options",
        params={
            "scope": "shot",
            "asset_type": "reference_image",
            "source": "shot_context",
            "shot_id": shot["id"],
            "task_id": empty_task["id"],
            "limit": 10,
        },
    )
    empty_task_payload = empty_task_response.json()

    assert response.status_code == 200
    assert payload["total"] == 2
    shot_item = next(
        item for item in payload["items"] if item["source"]["kind"] == "shot_reference"
    )
    scene_item = next(
        item for item in payload["items"] if item["source"]["kind"] == "scene_reference"
    )
    assert shot_item["id"] == shot_reference["id"]
    assert shot_item["type"] == "reference_image"
    assert shot_item["is_selected"] is True
    assert "已加入任务" in shot_item["badges"]
    assert shot_item["metadata"]["shot_reference_id"] == shot_reference["id"]
    assert shot_item["metadata"]["character_reference_id"] == character_reference["id"]
    assert scene_item["metadata"]["scene_reference_id"] == scene_reference["id"]
    assert scene_item["metadata"]["shot_reference_id"] is None
    assert scene_item["is_selected"] is False
    empty_task_shot_item = next(
        item for item in empty_task_payload["items"] if item["source"]["kind"] == "shot_reference"
    )
    assert empty_task_response.status_code == 200
    assert empty_task_shot_item["is_selected"] is False
    assert "已加入任务" not in empty_task_shot_item["badges"]
    assert missing.status_code == 422
    assert "relative_path" not in response.text
    assert "stored_filename" not in response.text
    assert "base64" not in response.text.lower()


def test_picker_reference_image_options_are_read_only(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    project_id = str(project["id"])
    character = create_character(migrated_client, project_id)
    look = create_look(migrated_client, project_id, str(character["id"]))
    upload_character_reference(migrated_client, project_id, str(character["id"]), str(look["id"]))
    shot = create_shot(migrated_client, project_id)
    migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/characters",
        json={"character_id": character["id"], "look_id": look["id"]},
    )

    with get_session_factory()() as session:
        before_shot_references = len(list(session.scalars(select(ShotReferenceRecord)).all()))
        before_task_references = len(
            list(session.scalars(select(KeyframeGenerationTaskReferenceRecord)).all())
        )
        before_media = len(list(session.scalars(select(MediaAssetRecord)).all()))

    response = migrated_client.get(
        f"/api/projects/{project_id}/assets/picker-options",
        params={
            "scope": "shot",
            "asset_type": "reference_image",
            "source": "shot_context",
            "shot_id": shot["id"],
        },
    )

    with get_session_factory()() as session:
        after_shot_references = len(list(session.scalars(select(ShotReferenceRecord)).all()))
        after_task_references = len(
            list(session.scalars(select(KeyframeGenerationTaskReferenceRecord)).all())
        )
        after_media = len(list(session.scalars(select(MediaAssetRecord)).all()))

    assert response.status_code == 200
    assert after_shot_references == before_shot_references
    assert after_task_references == before_task_references
    assert after_media == before_media
