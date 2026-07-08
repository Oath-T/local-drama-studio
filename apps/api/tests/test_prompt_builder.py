from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import func, select

from app.infrastructure.database import get_session_factory
from app.infrastructure.models.character import MediaAssetRecord
from app.infrastructure.models.keyframe_generation import (
    KeyframeGenerationOutputRecord,
    KeyframeGenerationRunRecord,
)
from app.infrastructure.models.keyframe_task import KeyframeGenerationTaskRecord
from app.infrastructure.models.shot import ShotRecord
from app.infrastructure.models.video_generation import (
    VideoGenerationOutputRecord,
    VideoGenerationRunRecord,
    VideoGenerationTaskRecord,
)


def create_project(client: TestClient, name: str = "Prompt Project") -> dict[str, object]:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()


def make_image_bytes() -> bytes:
    image = Image.new("RGB", (32, 24), color=(72, 92, 120))
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def build_complete_shot(client: TestClient) -> tuple[str, str]:
    project = create_project(client)
    project_id = str(project["id"])
    character = client.post(
        f"/api/projects/{project_id}/characters",
        json={
            "name": "男主",
            "role_type": "protagonist",
            "appearance_description": "sharp facial features",
            "prompt_identity": "young male lead with determined eyes",
        },
    ).json()
    look = client.post(
        f"/api/projects/{project_id}/characters/{character['id']}/looks",
        json={
            "name": "黑夹克",
            "costume_description": "black jacket and dark trousers",
            "hair_description": "short black hair",
            "prompt_appearance": "modern urban black jacket outfit",
        },
    ).json()
    character_reference = client.post(
        f"/api/projects/{project_id}/characters/{character['id']}/looks/{look['id']}/references",
        files={"file": ("character.png", make_image_bytes(), "image/png")},
        data={
            "shot_type": "closeup",
            "view_angle": "front",
            "expression": "neutral",
            "pose_type": "standing",
            "description": "clear identity portrait",
            "is_identity_anchor": "true",
        },
    ).json()
    scene = client.post(
        f"/api/projects/{project_id}/scenes",
        json={
            "name": "办公楼门口",
            "scene_type": "exterior",
            "fixed_environment_description": "black stone facade and glass doors",
            "prompt_environment": "luxury office building entrance",
        },
    ).json()
    state = client.post(
        f"/api/projects/{project_id}/scenes/{scene['id']}/states",
        json={
            "name": "雨夜",
            "time_of_day": "night",
            "weather": "heavy_rain",
            "lighting": "neon",
            "season": "unknown",
            "environment_condition": "wet ground reflections",
            "crowd_level": "sparse",
            "prompt_state": "rainy night with blue neon reflections",
        },
    ).json()
    scene_reference = client.post(
        f"/api/projects/{project_id}/scenes/{scene['id']}/states/{state['id']}/references",
        files={"file": ("scene.png", make_image_bytes(), "image/png")},
        data={
            "shot_scale": "wide",
            "camera_position": "eye_level",
            "view_direction": "front",
            "composition_type": "centered",
            "description": "wide entrance reference",
            "is_spatial_anchor": "true",
        },
    ).json()
    shot = client.post(
        f"/api/projects/{project_id}/shots",
        json={
            "name": "雨夜入场",
            "story_description": "主角来到办公楼。",
            "visual_description": "雨夜中，男主站在办公楼门口。",
            "action_summary": "男主低头看手机，然后抬头走向入口。",
            "mood_description": "从压抑转为坚定。",
            "focal_subject": "男主的面部和黑色夹克",
            "scene_id": scene["id"],
            "scene_state_id": state["id"],
            "shot_scale": "medium",
            "camera_angle": "front",
            "camera_height": "eye_level",
            "composition_type": "centered",
            "camera_movement": "push_in",
        },
    ).json()
    shot_character = client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/characters",
        json={
            "character_id": character["id"],
            "look_id": look["id"],
            "is_primary_subject": True,
            "action_description": "looks down at the phone and walks forward",
            "expression_description": "restrained anger turning into resolve",
            "position_description": "center foreground",
        },
    ).json()
    character_ref_response = client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/references",
        json={
            "reference_type": "character",
            "character_reference_id": character_reference["id"],
            "shot_character_id": shot_character["id"],
            "purpose": "identity",
        },
    )
    scene_ref_response = client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/references",
        json={
            "reference_type": "scene",
            "scene_reference_id": scene_reference["id"],
            "purpose": "environment",
        },
    )
    assert character_ref_response.status_code == 201
    assert scene_ref_response.status_code == 201
    return project_id, str(shot["id"])


def table_counts() -> dict[str, int]:
    with get_session_factory()() as session:
        return {
            "shots": int(session.scalar(select(func.count()).select_from(ShotRecord)) or 0),
            "media": int(session.scalar(select(func.count()).select_from(MediaAssetRecord)) or 0),
            "keyframe_tasks": int(
                session.scalar(select(func.count()).select_from(KeyframeGenerationTaskRecord)) or 0
            ),
            "keyframe_runs": int(
                session.scalar(select(func.count()).select_from(KeyframeGenerationRunRecord)) or 0
            ),
            "keyframe_outputs": int(
                session.scalar(select(func.count()).select_from(KeyframeGenerationOutputRecord))
                or 0
            ),
            "video_tasks": int(
                session.scalar(select(func.count()).select_from(VideoGenerationTaskRecord)) or 0
            ),
            "video_runs": int(
                session.scalar(select(func.count()).select_from(VideoGenerationRunRecord)) or 0
            ),
            "video_outputs": int(
                session.scalar(select(func.count()).select_from(VideoGenerationOutputRecord)) or 0
            ),
        }


def test_prompt_draft_returns_stable_complete_context(migrated_client: TestClient) -> None:
    project_id, shot_id = build_complete_shot(migrated_client)
    before = table_counts()

    first = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot_id}/prompt-draft",
        json={"target": "all", "style": "cinematic_short_drama", "language": "en"},
    )
    second = migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot_id}/prompt-draft",
        json={"target": "all", "style": "cinematic_short_drama", "language": "en"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    payload = first.json()
    assert "generated_at" not in payload
    assert "男主" in payload["context_summary_zh"]
    assert "办公楼门口" in payload["context_summary_zh"]
    assert "cinematic short drama" in payload["first_frame_prompt_en"]
    assert "same character" in payload["end_frame_prompt_en"]
    assert "smooth cinematic" in payload["motion_prompt_en"]
    assert payload["camera_motion"] == "slow push-in"
    assert "inconsistent character" in payload["negative_prompt_en"]
    assert "relative_path" not in first.text
    assert "stored_filename" not in first.text
    assert "base64" not in first.text.lower()
    assert table_counts() == before


def test_prompt_draft_empty_context_returns_safe_warnings(migrated_client: TestClient) -> None:
    project = create_project(migrated_client, "Empty Context")
    shot = migrated_client.post(
        f"/api/projects/{project['id']}/shots",
        json={"name": "空镜头"},
    ).json()

    response = migrated_client.post(
        f"/api/projects/{project['id']}/shots/{shot['id']}/prompt-draft",
        json={"target": "video"},
    )

    assert response.status_code == 200
    payload = response.json()
    codes = {item["code"] for item in payload["warnings"]}
    assert "NO_CHARACTERS" in codes
    assert "SCENE_MISSING" in codes
    assert "SHOT_VISUAL_DESCRIPTION_MISSING" in codes
    assert "SHOT_ACTION_MISSING" in codes
    assert "WEAK_END_FRAME_SIGNAL" in codes
    assert "NO_CAMERA_MOTION" in codes
    assert payload["camera_motion"] == "subtle cinematic camera movement, stable framing"


def test_prompt_draft_cross_project_access_fails(migrated_client: TestClient) -> None:
    source_project = create_project(migrated_client, "Source")
    other_project = create_project(migrated_client, "Other")
    shot = migrated_client.post(
        f"/api/projects/{source_project['id']}/shots",
        json={"name": "Source Shot"},
    ).json()

    response = migrated_client.post(
        f"/api/projects/{other_project['id']}/shots/{shot['id']}/prompt-draft",
        json={},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SHOT_NOT_FOUND"


def test_prompt_draft_can_omit_negative_prompt(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    shot = migrated_client.post(
        f"/api/projects/{project['id']}/shots",
        json={"name": "No Negative"},
    ).json()

    response = migrated_client.post(
        f"/api/projects/{project['id']}/shots/{shot['id']}/prompt-draft",
        json={"include_negative_prompt": False},
    )

    assert response.status_code == 200
    assert response.json()["negative_prompt_en"] == ""
