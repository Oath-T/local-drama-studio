# Local Drama Studio

Local Drama Studio is a local-first AI short-drama production platform. Sprint 2 adds the first asset domain on top of the project system: character records, character looks, reference image upload, media storage, thumbnails, and metadata for future shot/reference selection.

This sprint does not implement AI Agents, image generation, video generation, ComfyUI calls, background AI analysis jobs, login, cloud services, infinite canvas, or a 3D director stage.

## Structure

```text
local-drama-studio/
|-- apps/
|   |-- web/
|   `-- api/
|-- storage/
|-- scripts/
|-- docs/
|-- .env.example
|-- .gitignore
|-- README.md
`-- docker-compose.yml
```

## Prerequisites

- Node.js 20+
- Python 3.11+

On Windows, the Python launcher command `py -3.11` or newer can be used when `python` is not on PATH.

## One Command Development Start

From the repository root:

```powershell
.\scripts\dev.ps1
```

The script runs `alembic upgrade head` before starting the API. If migration fails, startup stops. The API and web dev servers are then launched as local background processes.

## Backend

```powershell
cd apps\api
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health endpoint:

```text
GET http://127.0.0.1:8000/api/health
```

Project endpoints:

```text
GET    /api/projects
POST   /api/projects
GET    /api/projects/{project_id}
PATCH  /api/projects/{project_id}
DELETE /api/projects/{project_id}
```

Character endpoints:

```text
GET    /api/projects/{project_id}/characters
POST   /api/projects/{project_id}/characters
GET    /api/projects/{project_id}/characters/{character_id}
PATCH  /api/projects/{project_id}/characters/{character_id}
DELETE /api/projects/{project_id}/characters/{character_id}

GET    /api/projects/{project_id}/characters/{character_id}/looks
POST   /api/projects/{project_id}/characters/{character_id}/looks
POST   /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references
GET    /api/media/{media_asset_id}/thumbnail
GET    /api/media/{media_asset_id}/content
```

## Frontend

```powershell
cd apps\web
npm install
npm run dev
```

Open `http://localhost:5173`.

Routes:

- `/projects`: project list.
- `/projects/:projectId`: project detail.
- `/projects/:projectId/characters`: project character library.
- `/projects/:projectId/characters/:characterId`: character detail, looks, and reference images.

## Alembic

From `apps/api`:

```powershell
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Database structure is managed by Alembic migrations. The API startup path does not create tables automatically.

## Tests

Backend:

```powershell
cd apps\api
ruff check .
pytest
```

Frontend:

```powershell
cd apps\web
npm run typecheck
npm run test
```

## Configuration

Copy `.env.example` to `.env` when local overrides are needed. Do not commit `.env`, SQLite database files, uploaded assets, or generated output.
