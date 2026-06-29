# Local Drama Studio

Local Drama Studio is a local-first AI short-drama production platform. Sprint 7 adds keyframe generation task preparation on top of project, character, scene, shot, rule-based recommendation, and user-triggered visual analysis systems.

This sprint does not implement AI Agents, image generation, video generation, ComfyUI calls, generation queues, automatic analysis, model training, model fine-tuning, login, cloud asset storage, infinite canvas, drag-and-drop sorting, or a 3D director stage.

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

GET    /api/projects/{project_id}/shots/{shot_id}/keyframe-tasks
POST   /api/projects/{project_id}/shots/{shot_id}/keyframe-tasks
GET    /api/projects/{project_id}/keyframe-tasks/{task_id}
PATCH  /api/projects/{project_id}/keyframe-tasks/{task_id}
DELETE /api/projects/{project_id}/keyframe-tasks/{task_id}
POST   /api/projects/{project_id}/keyframe-tasks/{task_id}/duplicate
POST   /api/projects/{project_id}/keyframe-tasks/{task_id}/mark-ready
POST   /api/projects/{project_id}/keyframe-tasks/{task_id}/mark-draft
GET    /api/projects/{project_id}/keyframe-tasks/{task_id}/references
POST   /api/projects/{project_id}/keyframe-tasks/{task_id}/references
PATCH  /api/projects/{project_id}/keyframe-tasks/{task_id}/references/{task_reference_id}
DELETE /api/projects/{project_id}/keyframe-tasks/{task_id}/references/{task_reference_id}

GET    /api/system/capabilities
GET    /api/projects/{project_id}/vision-analysis/tasks/{task_id}
POST   /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/analysis/tasks
GET    /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/analysis/latest-task
POST   /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/analysis/confirm
POST   /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/analysis/reject
POST   /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/analysis/tasks
GET    /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/analysis/latest-task
POST   /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/analysis/confirm
POST   /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/analysis/reject
```

Shot recommendations are computed from current shot parameters and asset metadata. They are not stored, do not call AI models, and do not automatically bind references.

Vision analysis is user-triggered per reference image. Suggestions are stored separately from official metadata and must be accepted through the dedicated review flow before they change reference metadata. The API starts without an OpenAI key; manual editing remains available.

Keyframe tasks store a validated shot snapshot, prompt fields, generation parameters, and selected task references. They only support `draft` and `ready` statuses in Sprint 7 and never call image generation services.

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

Vision analysis configuration:

```text
LDS_API_VISION_PROVIDER=openai
LDS_API_OPENAI_API_KEY=
LDS_API_OPENAI_VISION_MODEL=
LDS_API_VISION_ANALYSIS_TIMEOUT_SECONDS=60
LDS_API_VISION_ANALYSIS_MAX_CONCURRENCY=1
LDS_API_VISION_ANALYSIS_MAX_RETRIES=1
LDS_API_VISION_ANALYSIS_MAX_IMAGE_MB=15
```
