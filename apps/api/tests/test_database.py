from sqlalchemy import text

from app.infrastructure.database import SessionLocal, initialize_database


def test_database_initializes_successfully() -> None:
    initialize_database()

    with SessionLocal() as session:
        result = session.execute(text("SELECT 1")).scalar_one()

    assert result == 1
