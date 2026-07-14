from fastapi.testclient import TestClient
from test_prompt_builder import create_project, table_counts


def create_director_shot(client: TestClient) -> tuple[str, str]:
    project = create_project(client, "Director Project")
    project_id = str(project["id"])
    character = client.post(
        f"/api/projects/{project_id}/characters",
        json={
            "name": "男主",
            "role_type": "protagonist",
            "prompt_identity": "young male lead with sharp determined eyes",
        },
    ).json()
    look = client.post(
        f"/api/projects/{project_id}/characters/{character['id']}/looks",
        json={
            "name": "黑西装",
            "costume_description": "tailored black suit and white shirt",
            "prompt_appearance": "black suit, clean business style",
        },
    ).json()
    scene = client.post(
        f"/api/projects/{project_id}/scenes",
        json={
            "name": "董事会议室",
            "scene_type": "interior",
            "spatial_layout_description": "long meeting table, doorway visible at the back",
            "prompt_environment": "luxury corporate boardroom",
        },
    ).json()
    state = client.post(
        f"/api/projects/{project_id}/scenes/{scene['id']}/states",
        json={
            "name": "夜晚会议",
            "time_of_day": "night",
            "weather": "unknown",
            "lighting": "low_key",
            "season": "unknown",
            "crowd_level": "crowded",
            "environment_condition": "tense stillness in the room",
        },
    ).json()
    shot = client.post(
        f"/api/projects/{project_id}/shots",
        json={
            "name": "男主冲进会议室",
            "story_description": "董事会正在开会。",
            "visual_description": "会议桌和众人都在画面中。",
            "action_summary": "男主推门冲进会议室，所有人震惊。",
            "mood_description": "紧张和压迫感",
            "shot_scale": "medium_wide",
            "camera_angle": "front",
            "camera_height": "eye_level",
            "composition_type": "centered",
            "camera_movement": "push_in",
            "scene_id": scene["id"],
            "scene_state_id": state["id"],
        },
    ).json()
    client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/characters",
        json={
            "character_id": character["id"],
            "look_id": look["id"],
            "is_primary_subject": True,
            "action_description": "pushes the door open and rushes in",
            "expression_description": "urgent and determined",
            "position_description": "doorway foreground",
        },
    )
    return project_id, str(shot["id"])


def test_director_recommends_enter_room_shock_and_is_stable(
    migrated_client: TestClient,
) -> None:
    project_id, shot_id = create_director_shot(migrated_client)
    before = table_counts()
    body = {"style": "cinematic_short_drama"}

    first = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot_id}/prompt-draft", json=body
    )
    second = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot_id}/prompt-draft", json=body
    )

    assert first.status_code == 200
    assert first.json() == second.json()
    payload = first.json()
    assert payload["recommended_template_id"] == "enter_room_shock"
    assert payload["applied_template_id"] == "enter_room_shock"
    assert payload["workflow_hint"] == "pose_control"
    assert "doorway" in payload["first_frame_prompt_en"]
    assert "meeting table" in payload["first_frame_prompt_en"]
    assert "shock" in payload["first_frame_prompt_en"]
    assert "medium wide" in payload["first_frame_prompt_en"]
    assert "not a seated business portrait" in payload["first_frame_prompt_en"]
    assert "everyone turns" in payload["motion_prompt_en"]
    assert payload["director_context"]["subjects"][0]["position"] == "doorway foreground"
    assert table_counts() == before


def test_user_template_id_takes_priority_over_recommendation(
    migrated_client: TestClient,
) -> None:
    project_id, shot_id = create_director_shot(migrated_client)

    response = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot_id}/prompt-draft",
        json={"template_id": "emotional_closeup"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommended_template_id"] == "enter_room_shock"
    assert payload["applied_template_id"] == "emotional_closeup"
    assert payload["workflow_hint"] == "portrait"


def test_director_overrides_replace_template_defaults(migrated_client: TestClient) -> None:
    project_id, shot_id = create_director_shot(migrated_client)

    response = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot_id}/prompt-draft",
        json={
            "template_id": "enter_room_shock",
            "director_overrides": {
                "subject_position": "left doorway foreground",
                "start_action": "kicks the door open",
                "end_action": "points at the executives",
                "crowd_action": "executives stand up from the table",
                "crowd_emotion": "panic",
                "camera_movement": "aggressive handheld push-in",
                "composition": "hero at left doorway, executives around the table",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    context = payload["director_context"]
    assert context["subjects"][0]["position"] == "left doorway foreground"
    assert context["subjects"][0]["start_action"] == "kicks the door open"
    assert context["subjects"][0]["end_action"] == "points at the executives"
    assert context["reaction"]["crowd_action"] == "executives stand up from the table"
    assert context["reaction"]["crowd_emotion"] == "panic"
    assert context["camera"]["movement"] == "aggressive handheld push-in"
    assert context["camera"]["composition"] == "hero at left doorway, executives around the table"
    assert "kicks the door open" in payload["first_frame_prompt_en"]
    assert "points at the executives" in payload["end_frame_prompt_en"]


def test_director_empty_context_returns_new_warnings(migrated_client: TestClient) -> None:
    project = create_project(migrated_client, "Empty Director")
    shot = migrated_client.post(
        f"/api/projects/{project['id']}/shots",
        json={"name": "空镜头"},
    ).json()

    response = migrated_client.post(
        f"/api/projects/{project['id']}/shots/{shot['id']}/prompt-draft",
        json={},
    )

    assert response.status_code == 200
    codes = {item["code"] for item in response.json()["warnings"]}
    assert "NO_PRIMARY_SUBJECT" in codes
    assert "SCENE_MISSING" in codes
    assert "CROWD_REACTION_MISSING" in codes


def test_pose_template_returns_advisory_warning(migrated_client: TestClient) -> None:
    project_id, shot_id = create_director_shot(migrated_client)

    response = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot_id}/prompt-draft",
        json={"template_id": "enter_room_shock"},
    )

    assert response.status_code == 200
    codes = {item["code"] for item in response.json()["warnings"]}
    assert "POSE_CONTROL_RECOMMENDED" in codes
