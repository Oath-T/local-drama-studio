from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.schemas.vision_analysis import (
    CharacterVisionAnalysisSuggestion,
    SceneVisionAnalysisSuggestion,
)
from app.core.config import get_settings
from app.domain.vision_analysis import VisionAnalysisErrorCode, VisionProviderRuntimeError
from app.infrastructure.database import get_session_factory
from app.infrastructure.models.character import CharacterReferenceRecord
from app.infrastructure.models.vision_analysis import VisionAnalysisTaskRecord
from app.infrastructure.vision.base import (
    CharacterAnalysisContext,
    SceneAnalysisContext,
    VisionImageInput,
)
from app.service.vision_analysis_task_runner import VisionAnalysisTaskRunner
from tests.test_characters import create_character, create_look, create_project, upload_reference
from tests.test_scenes import (
    create_scene,
    create_state,
)
from tests.test_scenes import (
    upload_reference as upload_scene_reference,
)


class StubVisionProvider:
    async def analyze_character_reference(
        self,
        image: VisionImageInput,
        context: CharacterAnalysisContext,
    ) -> CharacterVisionAnalysisSuggestion:
        return CharacterVisionAnalysisSuggestion(
            shot_type="closeup",
            view_angle="front",
            expression="neutral",
            pose_type="standing",
            tags=["正脸", "清晰"],
            description="正面近景参考图",
            quality_notes=["画面清晰"],
            identity_anchor_recommended=True,
            appearance_summary="可见面部特征",
            costume_summary="深色服装",
            hair_summary="短发",
            confidence_notes="基于可见画面判断",
        )

    async def analyze_scene_reference(
        self,
        image: VisionImageInput,
        context: SceneAnalysisContext,
    ) -> SceneVisionAnalysisSuggestion:
        return SceneVisionAnalysisSuggestion(
            shot_scale="wide",
            camera_position="eye_level",
            view_direction="front",
            composition_type="centered",
            tags=["空间", "入口"],
            description="宽景空间参考图",
            quality_notes=["结构清楚"],
            spatial_anchor_recommended=True,
            empty_plate_recommended=True,
            detected_time_of_day="night",
            detected_weather="indoor",
            detected_lighting="cool_indoor",
        )


class FailingProvider:
    async def analyze_character_reference(
        self,
        image: VisionImageInput,
        context: CharacterAnalysisContext,
    ) -> CharacterVisionAnalysisSuggestion:
        raise VisionProviderRuntimeError(
            VisionAnalysisErrorCode.PROVIDER_TIMEOUT,
            "data:image/png;base64,secret",
            retryable=False,
        )

    async def analyze_scene_reference(
        self,
        image: VisionImageInput,
        context: SceneAnalysisContext,
    ) -> SceneVisionAnalysisSuggestion:
        raise VisionProviderRuntimeError(
            VisionAnalysisErrorCode.PROVIDER_TIMEOUT,
            "data:image/png;base64,secret",
            retryable=False,
        )


def setup_character_reference(
    client: TestClient,
) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    project = create_project(client)
    character = create_character(client, str(project["id"]))
    look = create_look(client, str(project["id"]), str(character["id"]))
    reference = upload_reference(client, str(project["id"]), str(character["id"]), str(look["id"]))
    return project, character, look, reference


def setup_scene_reference(
    client: TestClient,
) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    project = create_project(client)
    scene = create_scene(client, str(project["id"]))
    state = create_state(client, str(project["id"]), str(scene["id"]))
    reference = upload_scene_reference(
        client,
        str(project["id"]),
        str(scene["id"]),
        str(state["id"]),
    )
    return project, scene, state, reference


def enable_provider(monkeypatch) -> None:
    monkeypatch.setenv("LDS_API_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LDS_API_OPENAI_VISION_MODEL", "test-vision-model")
    get_settings.cache_clear()


def test_capabilities_hide_model_and_key(migrated_client: TestClient, monkeypatch) -> None:
    enable_provider(monkeypatch)

    response = migrated_client.get("/api/system/capabilities")

    assert response.status_code == 200
    data = response.json()
    assert data["vision_analysis"] == {"available": True, "provider": "openai"}
    assert "test-key" not in response.text
    assert "test-vision-model" not in response.text


def test_start_without_key_returns_safe_error(migrated_client: TestClient) -> None:
    project, character, look, reference = setup_character_reference(migrated_client)

    response = migrated_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}/analysis/tasks"
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "vision_provider_not_configured"
    assert "OPENAI" not in response.text


def test_character_analysis_task_completes_after_request_session(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_provider(monkeypatch)
    monkeypatch.setattr(
        "app.service.vision_analysis_task_runner.create_vision_analysis_provider",
        lambda settings: StubVisionProvider(),
    )
    project, character, look, reference = setup_character_reference(migrated_client)

    response = migrated_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}/analysis/tasks"
    )

    assert response.status_code == 202
    task = response.json()
    task_response = migrated_client.get(
        f"/api/projects/{project['id']}/vision-analysis/tasks/{task['id']}"
    )
    assert task_response.status_code == 200
    assert task_response.json()["status"] == "completed"
    assert task_response.json()["attempt_count"] == 1
    refreshed = migrated_client.get(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}"
    ).json()
    assert refreshed["analysis_status"] == "completed"
    assert refreshed["suggestion_review_status"] == "not_reviewed"
    assert refreshed["analysis_suggestions"]["schema_version"] == 1
    assert refreshed["analysis_suggestions"]["identity_anchor_recommended"] is True


def test_scene_analysis_task_completes(migrated_client: TestClient, monkeypatch) -> None:
    enable_provider(monkeypatch)
    monkeypatch.setattr(
        "app.service.vision_analysis_task_runner.create_vision_analysis_provider",
        lambda settings: StubVisionProvider(),
    )
    project, scene, state, reference = setup_scene_reference(migrated_client)

    response = migrated_client.post(
        f"/api/projects/{project['id']}/scenes/{scene['id']}"
        f"/states/{state['id']}/references/{reference['id']}/analysis/tasks"
    )

    assert response.status_code == 202
    refreshed = migrated_client.get(
        f"/api/projects/{project['id']}/scenes/{scene['id']}"
        f"/states/{state['id']}/references/{reference['id']}"
    ).json()
    assert refreshed["analysis_status"] == "completed"
    assert refreshed["analysis_suggestions"]["detected_time_of_day"] == "night"
    assert refreshed["analysis_suggestions"]["spatial_anchor_recommended"] is True
    assert refreshed["is_spatial_anchor"] is False
    assert refreshed["is_empty_plate"] is False


def test_duplicate_active_task_is_rejected(migrated_client: TestClient, monkeypatch) -> None:
    enable_provider(monkeypatch)
    project, character, look, reference = setup_character_reference(migrated_client)
    session_factory = get_session_factory()
    with session_factory() as session:
        db_ref = session.get(CharacterReferenceRecord, reference["id"])
        assert db_ref is not None
        db_ref.analysis_status = "pending"
        task = VisionAnalysisTaskRecord(
            id="11111111-1111-1111-1111-111111111111",
            project_id=str(project["id"]),
            target_type="character_reference",
            character_reference_id=str(reference["id"]),
            scene_reference_id=None,
            provider="openai",
            model_name="test",
            status="pending",
            attempt_count=0,
            error_code=None,
            error_message_safe=None,
            started_at=None,
            completed_at=None,
            created_at=db_ref.created_at,
            updated_at=db_ref.updated_at,
        )
        session.add(task)
        session.commit()

    response = migrated_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}/analysis/tasks"
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "analysis_already_running"


def test_reanalysis_failure_preserves_old_suggestions_and_review_status(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_provider(monkeypatch)
    project, character, look, reference = setup_character_reference(migrated_client)
    monkeypatch.setattr(
        "app.service.vision_analysis_task_runner.create_vision_analysis_provider",
        lambda settings: StubVisionProvider(),
    )
    migrated_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}/analysis/tasks"
    )
    confirm = migrated_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}/analysis/confirm",
        json={
            "accepted_fields": ["description"],
            "values": {"description": "人工确认后的描述"},
        },
    )
    assert confirm.status_code == 200
    assert confirm.json()["suggestion_review_status"] == "edited_and_accepted"
    monkeypatch.setattr(
        "app.service.vision_analysis_task_runner.create_vision_analysis_provider",
        lambda settings: FailingProvider(),
    )

    response = migrated_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}/analysis/tasks"
    )

    assert response.status_code == 202
    refreshed = migrated_client.get(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}"
    ).json()
    assert refreshed["analysis_status"] == "completed"
    assert refreshed["suggestion_review_status"] == "edited_and_accepted"
    assert refreshed["analysis_suggestions"]["description"] == "正面近景参考图"
    task = migrated_client.get(
        f"/api/projects/{project['id']}/vision-analysis/tasks/{response.json()['id']}"
    ).json()
    assert task["status"] == "failed"
    assert task["error_code"] == "vision_provider_timeout"
    assert "data:image/" not in str(task)


def test_reanalysis_success_resets_review_status(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_provider(monkeypatch)
    monkeypatch.setattr(
        "app.service.vision_analysis_task_runner.create_vision_analysis_provider",
        lambda settings: StubVisionProvider(),
    )
    project, character, look, reference = setup_character_reference(migrated_client)
    endpoint = (
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}/analysis/tasks"
    )
    migrated_client.post(endpoint)
    migrated_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}/analysis/reject"
    )

    migrated_client.post(endpoint)

    refreshed = migrated_client.get(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}"
    ).json()
    assert refreshed["suggestion_review_status"] == "not_reviewed"


def test_confirm_accept_all_and_partial_are_computed_by_backend(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_provider(monkeypatch)
    monkeypatch.setattr(
        "app.service.vision_analysis_task_runner.create_vision_analysis_provider",
        lambda settings: StubVisionProvider(),
    )
    project, character, look, reference = setup_character_reference(migrated_client)
    migrated_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}/analysis/tasks"
    )

    partial = migrated_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}/analysis/confirm",
        json={"accepted_fields": ["description"], "values": {"description": "正面近景参考图"}},
    )

    assert partial.status_code == 200
    assert partial.json()["suggestion_review_status"] == "edited_and_accepted"


def test_confirm_rejects_dangerous_extra_fields(migrated_client: TestClient, monkeypatch) -> None:
    enable_provider(monkeypatch)
    monkeypatch.setattr(
        "app.service.vision_analysis_task_runner.create_vision_analysis_provider",
        lambda settings: StubVisionProvider(),
    )
    project, character, look, reference = setup_character_reference(migrated_client)
    migrated_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}/analysis/tasks"
    )

    response = migrated_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}/analysis/confirm",
        json={
            "accepted_fields": ["description"],
            "values": {"description": "ok", "is_primary": True},
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "suggestion_validation_failed"


def test_latest_task_allows_polling_recovery(migrated_client: TestClient, monkeypatch) -> None:
    enable_provider(monkeypatch)
    project, character, look, reference = setup_character_reference(migrated_client)
    session_factory = get_session_factory()
    with session_factory() as session:
        db_ref = session.get(CharacterReferenceRecord, reference["id"])
        assert db_ref is not None
        now = datetime.now(UTC)
        db_ref.analysis_status = "pending"
        task = VisionAnalysisTaskRecord(
            id="22222222-2222-2222-2222-222222222222",
            project_id=str(project["id"]),
            target_type="character_reference",
            character_reference_id=str(reference["id"]),
            scene_reference_id=None,
            provider="openai",
            model_name="test",
            status="running",
            attempt_count=1,
            error_code=None,
            error_message_safe=None,
            started_at=now,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(task)
        session.commit()

    response = migrated_client.get(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}/analysis/latest-task"
    )

    assert response.status_code == 200
    assert response.json()["task"]["id"] == "22222222-2222-2222-2222-222222222222"
    assert response.json()["task"]["status"] == "running"


def test_interrupted_task_cleanup_preserves_old_suggestions(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    from app.main import create_app

    enable_provider(monkeypatch)
    monkeypatch.setattr(
        "app.service.vision_analysis_task_runner.create_vision_analysis_provider",
        lambda settings: StubVisionProvider(),
    )
    project, character, look, reference = setup_character_reference(migrated_client)
    migrated_client.post(
        f"/api/projects/{project['id']}/characters/{character['id']}"
        f"/looks/{look['id']}/references/{reference['id']}/analysis/tasks"
    )
    session_factory = get_session_factory()
    with session_factory() as session:
        db_ref = session.get(CharacterReferenceRecord, reference["id"])
        assert db_ref is not None
        now = datetime.now(UTC)
        db_ref.analysis_status = "pending"
        task = VisionAnalysisTaskRecord(
            id="33333333-3333-3333-3333-333333333333",
            project_id=str(project["id"]),
            target_type="character_reference",
            character_reference_id=str(reference["id"]),
            scene_reference_id=None,
            provider="openai",
            model_name="test",
            status="running",
            attempt_count=1,
            error_code=None,
            error_message_safe=None,
            started_at=now,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(task)
        session.commit()

    with TestClient(create_app()) as fresh_client:
        refreshed = fresh_client.get(
            f"/api/projects/{project['id']}/characters/{character['id']}"
            f"/looks/{look['id']}/references/{reference['id']}"
        ).json()
        latest = fresh_client.get(
            f"/api/projects/{project['id']}/characters/{character['id']}"
            f"/looks/{look['id']}/references/{reference['id']}/analysis/latest-task"
        ).json()

    assert refreshed["analysis_status"] == "completed"
    assert refreshed["analysis_suggestions"] is not None
    assert latest["task"]["status"] == "failed"
    assert latest["task"]["error_code"] == "analysis_interrupted"


def test_runner_media_read_rejects_files_outside_storage(
    migrated_client: TestClient,
    monkeypatch,
) -> None:
    enable_provider(monkeypatch)
    project, character, look, reference = setup_character_reference(migrated_client)
    outside = Path(get_settings().resolved_storage_dir).parent / "outside.png"
    outside.write_bytes(b"not used")
    session_factory = get_session_factory()
    with session_factory() as session:
        db_ref = session.get(CharacterReferenceRecord, reference["id"])
        assert db_ref is not None
        db_ref.media_asset.relative_path = "../outside.png"
        task = VisionAnalysisTaskRecord(
            id="44444444-4444-4444-4444-444444444444",
            project_id=str(project["id"]),
            target_type="character_reference",
            character_reference_id=str(reference["id"]),
            scene_reference_id=None,
            provider="openai",
            model_name="test",
            status="pending",
            attempt_count=0,
            error_code=None,
            error_message_safe=None,
            started_at=None,
            completed_at=None,
            created_at=db_ref.created_at,
            updated_at=db_ref.updated_at,
        )
        session.add(task)
        session.commit()

    runner = VisionAnalysisTaskRunner(session_factory=session_factory)
    import asyncio

    asyncio.run(runner.run_task("44444444-4444-4444-4444-444444444444"))

    with session_factory() as session:
        task = session.scalars(
            select(VisionAnalysisTaskRecord).where(
                VisionAnalysisTaskRecord.id == "44444444-4444-4444-4444-444444444444"
            )
        ).one()
    assert task.status == "failed"
    assert task.error_code == "media_read_failed"
    assert "outside" not in (task.error_message_safe or "")
