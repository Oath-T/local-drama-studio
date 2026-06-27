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
    assert "projects" in inspector.get_table_names()
