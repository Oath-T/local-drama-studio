# Local Drama Studio

Local Drama Studio is a local-first AI short-drama production platform. Sprint 5 adds real-time, explainable shot reference recommendations on top of the project, character, scene, and shot systems.

This sprint does not implement AI Agents, image generation, video generation, ComfyUI calls, background AI analysis jobs, model training, model fine-tuning, local or external vision model calls, login, cloud services, infinite canvas, drag-and-drop sorting, or a 3D director stage.

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

Scene endpoints:

```text
GET    /api/projects/{project_id}/scenes
POST   /api/projects/{project_id}/scenes
GET    /api/projects/{project_id}/scenes/{scene_id}
PATCH  /api/projects/{project_id}/scenes/{scene_id}
DELETE /api/projects/{project_id}/scenes/{scene_id}

GET    /api/projects/{project_id}/scenes/{scene_id}/states
POST   /api/projects/{project_id}/scenes/{scene_id}/states
PATCH  /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}
POST   /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/set-default
DELETE /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}

GET    /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references
POST   /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references
PATCH  /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}
POST   /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/set-primary
DELETE /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}
```

Shot endpoints:

```text
GET    /api/projects/{project_id}/shots
POST   /api/projects/{project_id}/shots
GET    /api/projects/{project_id}/shots/{shot_id}
PATCH  /api/projects/{project_id}/shots/{shot_id}
DELETE /api/projects/{project_id}/shots/{shot_id}
POST   /api/projects/{project_id}/shots/{shot_id}/move
POST   /api/projects/{project_id}/shots/{shot_id}/duplicate

GET    /api/projects/{project_id}/shots/{shot_id}/characters
POST   /api/projects/{project_id}/shots/{shot_id}/characters
PATCH  /api/projects/{project_id}/shots/{shot_id}/characters/{shot_character_id}
DELETE /api/projects/{project_id}/shots/{shot_id}/characters/{shot_character_id}
POST   /api/projects/{project_id}/shots/{shot_id}/characters/{shot_character_id}/move

GET    /api/projects/{project_id}/shots/{shot_id}/references
POST   /api/projects/{project_id}/shots/{shot_id}/references
DELETE /api/projects/{project_id}/shots/{shot_id}/references/{shot_reference_id}
POST   /api/projects/{project_id}/shots/{shot_id}/references/{shot_reference_id}/move

GET    /api/projects/{project_id}/shots/{shot_id}/recommendations
```

Shot recommendations are computed from current shot parameters and asset metadata. They are not stored, do not call AI models, and do not automatically bind references.

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
- `/projects/:projectId/scenes`: project scene library.
- `/projects/:projectId/scenes/:sceneId`: scene detail, states, and reference images.
- `/projects/:projectId/shots`: project shot workbench.
- `/projects/:projectId/shots/:shotId`: project shot workbench with a selected shot.

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
