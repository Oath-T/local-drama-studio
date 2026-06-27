from collections.abc import Generator
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient

from alembic import command
from app.core.config import get_settings
from app.infrastructure.database import reset_database_engine
from app.main import create_app


@pytest.fixture(autouse=True)
def isolated_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Generator[None, None, None]:
    database_path = tmp_path / "test-local-drama-studio.db"
    monkeypatch.setenv("LDS_API_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("LDS_API_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    reset_database_engine()
    yield
    get_settings.cache_clear()
    reset_database_engine()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def migrated_client() -> Generator[TestClient, None, None]:
    command.upgrade(Config("alembic.ini"), "head")
    with TestClient(create_app()) as test_client:
        yield test_client
