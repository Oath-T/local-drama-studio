# Local Drama Studio API

FastAPI backend for the local development platform foundation.

## Run

```powershell
alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The application does not create or modify tables during startup. Run Alembic migrations before starting the API.

## Project API

```text
GET    /api/projects
POST   /api/projects
GET    /api/projects/{project_id}
PATCH  /api/projects/{project_id}
DELETE /api/projects/{project_id}
```

## Test

```powershell
pytest
```
