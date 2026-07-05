# Local Drama Studio

Local Drama Studio is a local-first AI short-drama production platform. Sprint 9.2 adds a real Wan2.2 14B first-last-frame ComfyUI workflow definition on top of project, character, scene, shot, rule-based recommendation, visual analysis, keyframe task preparation, keyframe generation, and local ComfyUI video task systems.

This sprint does not implement AI Agents, cloud services, multi-machine workers, batch automatic generation, arbitrary workflow upload or editing, Custom Node installation, model downloads, automatic analysis, model training, model fine-tuning, login, cloud asset storage, infinite canvas, drag-and-drop sorting, a timeline editor, subtitles, dubbing, music, or a 3D director stage.

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

GET    /api/projects/{project_id}/video-workflows
POST   /api/projects/{project_id}/video-inputs/images
GET    /api/projects/{project_id}/shots/{shot_id}/video-tasks
POST   /api/projects/{project_id}/shots/{shot_id}/video-tasks
GET    /api/projects/{project_id}/video-tasks/{task_id}
PATCH  /api/projects/{project_id}/video-tasks/{task_id}
DELETE /api/projects/{project_id}/video-tasks/{task_id}
POST   /api/projects/{project_id}/video-tasks/{task_id}/mark-ready
POST   /api/projects/{project_id}/video-tasks/{task_id}/mark-draft
POST   /api/projects/{project_id}/video-tasks/{task_id}/runs
GET    /api/projects/{project_id}/video-tasks/{task_id}/runs
POST   /api/projects/{project_id}/video-outputs/{output_id}/select
DELETE /api/projects/{project_id}/video-outputs/{output_id}/select

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

Keyframe generation runs are separate execution records. Sprint 8 supports the fixed
`keyframe_basic_v1` ComfyUI API workflow only. It uses prompt text and generation parameters,
does not use task reference images, requires `output_count=1`, and saves generated images as
platform `MediaAsset` records through safe media URLs.

Video generation tasks are separate from keyframe generation. Sprint 9 supports a provider-neutral
image-to-video task and run model with the fixed `video_i2v_14b_v1` workflow identifier. Sprint 9.1
adds role-based `start_frame` and `end_frame` inputs. Sprint 9.2 includes the real
`video_wan22_14b_flf2v_v1` first-last-frame workflow definition exported from ComfyUI. The platform
does not download models, install Custom Nodes, or modify the user's ComfyUI directory. If a
configured workflow JSON is missing or fails safety checks, that workflow is reported as unavailable
and no fake generation is exposed.

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

ComfyUI keyframe generation configuration:

```text
LDS_API_KEYFRAME_PROVIDER=comfyui
LDS_API_COMFYUI_BASE_URL=http://127.0.0.1:8188
LDS_API_COMFYUI_DEFAULT_CHECKPOINT=
LDS_API_COMFYUI_WORKFLOW_DIR=./workflows
LDS_API_COMFYUI_TIMEOUT_SECONDS=30
LDS_API_COMFYUI_POLL_INTERVAL_SECONDS=2
LDS_API_COMFYUI_JOB_TIMEOUT_SECONDS=900
LDS_API_COMFYUI_MAX_CONCURRENCY=1
LDS_API_GENERATED_OUTPUT_MAX_MB=25
LDS_API_GENERATED_VIDEO_MAX_MB=500
```

The frontend never receives the ComfyUI base URL, workflow JSON, local paths, or model paths.
