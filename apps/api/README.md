# Local Drama Studio API

FastAPI backend for the local development platform.

## Run

```powershell
alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The application does not create or modify tables during startup. Run Alembic migrations before starting the API.

## APIs

Project API:

```text
GET    /api/projects
POST   /api/projects
GET    /api/projects/{project_id}
PATCH  /api/projects/{project_id}
DELETE /api/projects/{project_id}
```

Character asset API:

```text
GET    /api/projects/{project_id}/characters
POST   /api/projects/{project_id}/characters
GET    /api/projects/{project_id}/characters/{character_id}
PATCH  /api/projects/{project_id}/characters/{character_id}
DELETE /api/projects/{project_id}/characters/{character_id}

GET    /api/projects/{project_id}/characters/{character_id}/looks
POST   /api/projects/{project_id}/characters/{character_id}/looks
GET    /api/projects/{project_id}/characters/{character_id}/looks/{look_id}
PATCH  /api/projects/{project_id}/characters/{character_id}/looks/{look_id}
POST   /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/set-default
DELETE /api/projects/{project_id}/characters/{character_id}/looks/{look_id}

GET    /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references
POST   /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references
GET    /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}
PATCH  /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}
POST   /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/set-primary
DELETE /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}

GET    /api/media/{media_asset_id}/thumbnail
GET    /api/media/{media_asset_id}/content
```

Scene asset API:

```text
GET    /api/projects/{project_id}/scenes
POST   /api/projects/{project_id}/scenes
GET    /api/projects/{project_id}/scenes/{scene_id}
PATCH  /api/projects/{project_id}/scenes/{scene_id}
DELETE /api/projects/{project_id}/scenes/{scene_id}

GET    /api/projects/{project_id}/scenes/{scene_id}/states
POST   /api/projects/{project_id}/scenes/{scene_id}/states
GET    /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}
PATCH  /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}
POST   /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/set-default
DELETE /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}

GET    /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references
POST   /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references
GET    /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}
PATCH  /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}
POST   /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/set-primary
DELETE /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}
```

Reference image uploads accept JPG, PNG, and WEBP images. Upload size and thumbnail size are configured through environment variables.

Shot recommendation API:

```text
GET /api/projects/{project_id}/shots/{shot_id}/recommendations?limit=5
```

Recommendations are real-time, rule-based, and explainable. They do not call AI models,
do not persist recommendation results, and still require the user to confirm binding through
the existing ShotReference create endpoint.

Vision analysis API:

```text
GET  /api/system/capabilities
GET  /api/projects/{project_id}/vision-analysis/tasks/{task_id}
POST /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/analysis/tasks
GET  /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/analysis/latest-task
POST /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/analysis/confirm
POST /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/analysis/reject
POST /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/analysis/tasks
GET  /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/analysis/latest-task
POST /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/analysis/confirm
POST /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/analysis/reject
```

Vision analysis uses a provider-neutral service boundary. OpenAI is the first provider, configured
through environment variables. Suggestions never overwrite official metadata without the dedicated
confirmation API.

## Test

```powershell
ruff check .
pytest
```
