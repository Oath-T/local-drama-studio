from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import text

from app.infrastructure.database import get_session_factory
from app.infrastructure.models.character import CharacterReferenceRecord
from app.infrastructure.models.scene import SceneReferenceRecord
from app.infrastructure.models.shot import ShotCharacterRecord, ShotRecord
from app.service.character_reference_ranker import CharacterReferenceRanker
from app.service.scene_reference_ranker import SceneReferenceRanker


def create_project(client: TestClient, name: str = "Sprint 5 Project") -> dict[str, object]:
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


def make_image_bytes() -> bytes:
    image = Image.new("RGB", (32, 24), color=(64, 96, 128))
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def upload_character_reference(
    client: TestClient,
    project_id: str,
    character_id: str,
    look_id: str,
    **overrides: str,
) -> dict[str, object]:
    data = {
        "shot_type": "closeup",
        "view_angle": "front",
        "expression": "neutral",
        "pose_type": "standing",
        "tags": "identity, calm",
        "description": "front calm identity",
        "is_identity_anchor": "true",
    }
    data.update(overrides)
    response = client.post(
        f"/api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references",
        files={"file": ("character.png", make_image_bytes(), "image/png")},
        data=data,
    )
    assert response.status_code == 201
    return response.json()


def upload_scene_reference(
    client: TestClient,
    project_id: str,
    scene_id: str,
    state_id: str,
    **overrides: str,
) -> dict[str, object]:
    data = {
        "shot_scale": "wide",
        "camera_position": "eye_level",
        "view_direction": "front",
        "composition_type": "centered",
        "tags": "neon, lobby",
        "description": "wide neon lobby",
        "is_spatial_anchor": "true",
        "is_empty_plate": "true",
    }
    data.update(overrides)
    response = client.post(
        f"/api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references",
        files={"file": ("scene.png", make_image_bytes(), "image/png")},
        data=data,
    )
    assert response.status_code == 201
    return response.json()


def create_shot(client: TestClient, project_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Shot 1",
        "visual_description": "Lead walks through neon light with a calm face.",
        "mood_description": "neon",
        "shot_scale": "wide",
        "camera_height": "eye_level",
        "camera_angle": "front",
        "composition_type": "centered",
    }
    payload.update(overrides)
    response = client.post(f"/api/projects/{project_id}/shots", json=payload)
    assert response.status_code == 201
    return response.json()


def count_core_records() -> dict[str, int]:
    with get_session_factory()() as session:
        rows = session.execute(
            text(
                """
                SELECT 'shots', count(*) FROM shots
                UNION ALL SELECT 'shot_characters', count(*) FROM shot_characters
                UNION ALL SELECT 'shot_references', count(*) FROM shot_references
                UNION ALL SELECT 'character_references', count(*) FROM character_references
                UNION ALL SELECT 'scene_references', count(*) FROM scene_references
                """
            )
        ).all()
    return {str(name): int(count) for name, count in rows}


def test_recommendations_are_stable_safe_and_do_not_write_database(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    project_id = str(project["id"])
    character = create_character(migrated_client, project_id)
    look = create_look(migrated_client, project_id, str(character["id"]))
    upload_character_reference(migrated_client, project_id, str(character["id"]), str(look["id"]))
    scene = create_scene(migrated_client, project_id)
    state = create_state(migrated_client, project_id, str(scene["id"]))
    upload_scene_reference(migrated_client, project_id, str(scene["id"]), str(state["id"]))
    shot = create_shot(
        migrated_client,
        project_id,
        scene_id=scene["id"],
        scene_state_id=state["id"],
    )
    migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/characters",
        json={"character_id": character["id"], "look_id": look["id"]},
    )

    before = count_core_records()
    first = migrated_client.get(f"/api/projects/{project_id}/shots/{shot['id']}/recommendations")
    second = migrated_client.get(f"/api/projects/{project_id}/shots/{shot['id']}/recommendations")
    after = count_core_records()

    assert first.status_code == 200
    assert first.json() == second.json()
    assert before == after
    payload = first.json()
    assert payload["generated_from_updated_at"] == shot["updated_at"]
    character_item = payload["character_recommendations"][0]["items"][0]
    scene_item = payload["scene_recommendations"]["items"][0]
    assert character_item["thumbnail_url"].startswith("/api/media/")
    assert scene_item["content_url"].startswith("/api/media/")
    assert "relative_path" not in str(payload)
    assert ":/" not in str(payload)
    assert ":\\" not in str(payload)


def test_character_groups_include_empty_candidates_and_scene_status_codes(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    project_id = str(project["id"])
    character = create_character(migrated_client, project_id)
    shot = create_shot(migrated_client, project_id)
    migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/characters",
        json={"character_id": character["id"]},
    )

    response = migrated_client.get(f"/api/projects/{project_id}/shots/{shot['id']}/recommendations")

    assert response.status_code == 200
    data = response.json()
    assert data["character_recommendations"][0]["items"] == []
    assert data["scene_recommendations"] == {
        "status_code": "scene_state_required",
        "items": [],
    }


def test_bound_purposes_are_stable_and_bound_flags_are_explicit(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    project_id = str(project["id"])
    character = create_character(migrated_client, project_id)
    look = create_look(migrated_client, project_id, str(character["id"]))
    reference = upload_character_reference(
        migrated_client,
        project_id,
        str(character["id"]),
        str(look["id"]),
        shot_type="full_body",
        is_identity_anchor="false",
    )
    shot = create_shot(migrated_client, project_id, shot_scale="full")
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

    response = migrated_client.get(f"/api/projects/{project_id}/shots/{shot['id']}/recommendations")

    item = response.json()["character_recommendations"][0]["items"][0]
    assert item["suggested_purpose"] == "appearance"
    assert item["bound_purposes"] == ["identity"]
    assert item["is_already_bound_for_suggested_purpose"] is False
    assert "already_bound_other_purpose" in item["reasons"]
    assert len(item["reasons"]) == len(set(item["reasons"]))

    migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/references",
        json={
            "reference_type": "character",
            "character_reference_id": reference["id"],
            "shot_character_id": shot_character["id"],
            "purpose": "appearance",
        },
    )
    rebound = migrated_client.get(
        f"/api/projects/{project_id}/shots/{shot['id']}/recommendations"
    ).json()["character_recommendations"][0]["items"][0]
    assert rebound["bound_purposes"] == ["identity", "appearance"]
    assert rebound["is_already_bound_for_suggested_purpose"] is True


def test_missing_media_candidate_is_skipped_without_failing(
    migrated_client: TestClient,
) -> None:
    project = create_project(migrated_client)
    project_id = str(project["id"])
    character = create_character(migrated_client, project_id)
    look = create_look(migrated_client, project_id, str(character["id"]))
    reference = upload_character_reference(
        migrated_client,
        project_id,
        str(character["id"]),
        str(look["id"]),
    )
    shot = create_shot(migrated_client, project_id)
    migrated_client.post(
        f"/api/projects/{project_id}/shots/{shot['id']}/characters",
        json={"character_id": character["id"], "look_id": look["id"]},
    )

    with get_session_factory()() as session:
        session.execute(text("PRAGMA foreign_keys=OFF"))
        session.execute(
            text("DELETE FROM media_assets WHERE id = :id"),
            {"id": reference["media_asset_id"]},
        )
        session.commit()

    response = migrated_client.get(f"/api/projects/{project_id}/shots/{shot['id']}/recommendations")

    assert response.status_code == 200
    assert response.json()["character_recommendations"][0]["items"] == []


def test_limit_and_scene_no_references_status(migrated_client: TestClient) -> None:
    project = create_project(migrated_client)
    project_id = str(project["id"])
    scene = create_scene(migrated_client, project_id)
    state = create_state(migrated_client, project_id, str(scene["id"]))
    shot = create_shot(
        migrated_client,
        project_id,
        scene_id=scene["id"],
        scene_state_id=state["id"],
    )

    response = migrated_client.get(
        f"/api/projects/{project_id}/shots/{shot['id']}/recommendations?limit=1"
    )
    invalid_limit = migrated_client.get(
        f"/api/projects/{project_id}/shots/{shot['id']}/recommendations?limit=21"
    )

    assert response.status_code == 200
    assert response.json()["scene_recommendations"] == {
        "status_code": "no_references",
        "items": [],
    }
    assert invalid_limit.status_code == 422


def test_character_ranker_purpose_priority_and_keyword_boundaries() -> None:
    ranker = CharacterReferenceRanker()
    shot = ShotRecord(
        id="shot",
        project_id="project",
        name="Shot",
        order_index=1,
        visual_description="angry face walking, not a one character keyword",
        story_description=None,
        mood_description=None,
        action_summary=None,
        shot_scale="close_up",
        camera_height="eye_level",
        camera_angle="front",
        composition_type="centered",
        camera_movement="static",
        created_at="2026-06-28T00:00:00+00:00",
        updated_at="2026-06-28T00:00:00+00:00",
    )
    shot_character = ShotCharacterRecord(
        id="shot-character",
        shot_id="shot",
        character_id="character",
        look_id="look",
        order_index=1,
        is_primary_subject=True,
        created_at="2026-06-28T00:00:00+00:00",
        updated_at="2026-06-28T00:00:00+00:00",
    )

    expression = character_reference("expression", "look", expression="angry")
    pose = character_reference("pose", "look", expression="unknown", pose_type="walking")
    identity = character_reference(
        "identity",
        "look",
        expression="neutral",
        is_identity_anchor=True,
    )
    appearance = character_reference("appearance", "look", shot_type="full_body")
    framing = character_reference(
        "framing",
        "other-look",
        shot_type="closeup",
        view_angle="left_profile",
    )
    general = character_reference(
        "general",
        "other-look",
        shot_type="unknown",
        view_angle="unknown",
    )
    notes_only = character_reference(
        "notes",
        "look",
        expression="unknown",
        shot_type="unknown",
        view_angle="unknown",
        notes="angry",
    )

    assert ranker.rank(shot, shot_character, expression).suggested_purpose == "expression"
    assert ranker.rank(shot, shot_character, pose).suggested_purpose == "pose"
    assert ranker.rank(shot, shot_character, identity).suggested_purpose == "identity"
    assert ranker.rank(shot, shot_character, appearance).suggested_purpose == "appearance"
    framing_result = ranker.rank(shot, shot_character, framing)
    assert framing_result.suggested_purpose == "framing"
    assert "different_look" in framing_result.reasons
    assert ranker.rank(shot, shot_character, general).suggested_purpose == "general"
    assert "expression_match" not in ranker.rank(shot, shot_character, notes_only).reasons


def test_scene_ranker_clamps_score_and_purpose_priority() -> None:
    ranker = SceneReferenceRanker()
    shot = ShotRecord(
        id="shot",
        project_id="project",
        name="Shot",
        order_index=1,
        visual_description="neon centered front view",
        story_description=None,
        mood_description="neon",
        action_summary=None,
        shot_scale="wide",
        camera_height="eye_level",
        camera_angle="front",
        composition_type="centered",
        camera_movement="static",
        created_at="2026-06-28T00:00:00+00:00",
        updated_at="2026-06-28T00:00:00+00:00",
    )

    spatial = scene_reference("spatial", is_spatial_anchor=True, is_empty_plate=True)
    composition = scene_reference("composition", is_spatial_anchor=False)
    lighting = scene_reference(
        "lighting",
        is_spatial_anchor=False,
        composition_type="unknown",
        camera_position="unknown",
        view_direction="unknown",
    )
    general = scene_reference(
        "general",
        is_spatial_anchor=False,
        is_primary=False,
        shot_scale="unknown",
        composition_type="unknown",
        camera_position="unknown",
        view_direction="unknown",
        tags="[]",
        description=None,
        notes="neon",
    )

    spatial_result = ranker.rank(shot, spatial)
    assert spatial_result.score == 100
    assert spatial_result.suggested_purpose == "spatial"
    assert len(spatial_result.reasons) == len(set(spatial_result.reasons))
    assert ranker.rank(shot, composition).suggested_purpose == "composition"
    assert ranker.rank(shot, lighting).suggested_purpose == "lighting"
    assert ranker.rank(shot, general).suggested_purpose == "general"
    assert "keyword_match" not in ranker.rank(shot, general).reasons


def character_reference(
    reference_id: str,
    look_id: str,
    *,
    shot_type: str = "closeup",
    view_angle: str = "front",
    expression: str = "neutral",
    pose_type: str = "standing",
    is_identity_anchor: bool = False,
    notes: str | None = None,
) -> CharacterReferenceRecord:
    return CharacterReferenceRecord(
        id=reference_id,
        look_id=look_id,
        media_asset_id=f"media-{reference_id}",
        shot_type=shot_type,
        view_angle=view_angle,
        expression=expression,
        pose_type=pose_type,
        tags="[]",
        description=None,
        notes=notes,
        is_primary=False,
        is_identity_anchor=is_identity_anchor,
        analysis_status="not_analyzed",
        suggestion_review_status="not_reviewed",
        created_at="2026-06-28T00:00:00+00:00",
        updated_at="2026-06-28T00:00:00+00:00",
    )


def scene_reference(
    reference_id: str,
    *,
    shot_scale: str = "wide",
    camera_position: str = "eye_level",
    view_direction: str = "front",
    composition_type: str = "centered",
    is_primary: bool = True,
    is_spatial_anchor: bool = False,
    is_empty_plate: bool = False,
    tags: str = '["neon"]',
    description: str | None = "neon scene",
    notes: str | None = None,
) -> SceneReferenceRecord:
    return SceneReferenceRecord(
        id=reference_id,
        state_id="state",
        media_asset_id=f"media-{reference_id}",
        shot_scale=shot_scale,
        camera_position=camera_position,
        view_direction=view_direction,
        composition_type=composition_type,
        is_primary=is_primary,
        is_spatial_anchor=is_spatial_anchor,
        is_empty_plate=is_empty_plate,
        tags=tags,
        description=description,
        notes=notes,
        analysis_status="not_analyzed",
        suggestion_review_status="not_reviewed",
        created_at="2026-06-28T00:00:00+00:00",
        updated_at="2026-06-28T00:00:00+00:00",
    )
