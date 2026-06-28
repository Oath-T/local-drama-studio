from alembic.config import Config
from sqlalchemy import inspect, text

from alembic import command
from app.infrastructure.database import get_engine, get_session_factory, initialize_database


def test_database_initializes_successfully() -> None:
    initialize_database()

    with get_session_factory()() as session:
        result = session.execute(text("SELECT 1")).scalar_one()

    assert result == 1


def test_database_migrations_upgrade_to_head() -> None:
    alembic_config = Config("alembic.ini")

    command.upgrade(alembic_config, "head")

    inspector = inspect(get_engine())
    tables = inspector.get_table_names()
    assert "projects" in tables
    assert "characters" in tables
    assert "character_looks" in tables
    assert "media_assets" in tables
    assert "character_references" in tables
    assert "scenes" in tables
    assert "scene_states" in tables
    assert "scene_references" in tables
    assert "shots" in tables


def test_shot_duration_zero_migrates_to_null() -> None:
    alembic_config = Config("alembic.ini")
    now = "2026-06-28T00:00:00+00:00"

    command.upgrade(alembic_config, "20260628_0300")
    with get_session_factory()() as session:
        session.execute(
            text(
                """
                INSERT INTO projects (
                    id, name, aspect_ratio, default_language, default_fps, created_at, updated_at
                )
                VALUES (
                    'duration-migration-project', 'Duration Migration', '9:16',
                    'zh-CN', 24, :created_at, :updated_at
                )
                """
            ),
            {"created_at": now, "updated_at": now},
        )
        session.execute(
            text(
                """
                INSERT INTO shots (
                    id, project_id, name, order_index, duration_seconds,
                    shot_scale, camera_height, camera_angle, composition_type,
                    camera_movement, created_at, updated_at
                )
                VALUES (
                    'duration-migration-shot', 'duration-migration-project', 'Legacy Zero',
                    1, 0, 'unknown', 'unknown', 'unknown', 'unknown',
                    'unknown', :created_at, :updated_at
                )
                """
            ),
            {"created_at": now, "updated_at": now},
        )
        session.commit()

    command.upgrade(alembic_config, "head")

    with get_session_factory()() as session:
        duration = session.execute(
            text("SELECT duration_seconds FROM shots WHERE id = 'duration-migration-shot'")
        ).scalar_one()

    assert duration is None
