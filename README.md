# Local Drama Studio

Local Drama Studio is a local-first AI short-drama production platform. Sprint 9.2 adds a real Wan2.2 14B first-last-frame ComfyUI workflow definition on top of project, character, scene, shot, rule-based recommendation, visual analysis, keyframe task preparation, keyframe generation, and local ComfyUI video task systems.

Sprint 18 adds a deterministic Director Engine v1 to the existing Prompt / Context Builder. It provides built-in shot templates, Director Context previews, and template-aware prompt drafts without using an LLM, changing the database, or triggering ComfyUI.

Sprint 19-20 adds Production Pipeline v1: structured keyframe task purposes, read-only shot/project production status APIs, a shot-level six-step production panel, and a project production board. It does not automatically generate, mark tasks ready, start ComfyUI, or adopt outputs.

Sprint 21-22 adds Timeline & Final Export v1. The project can read adopted video outputs in shot order, create stable final-export snapshots, and run a local FFmpeg-based MP4 concat export when FFmpeg and FFprobe are available. It does not add audio, subtitles, transitions, ComfyUI changes, or a timeline editor.

Sprint 23 adds Creative Workspace v1 on the shot page. It introduces a faster creator-facing frame for reference slots, first-frame/end-frame/video modes, a central result stage, and simplified prompt controls while keeping the existing professional task panels available in advanced mode. It does not change ComfyUI, workflows, manifests, runner/provider code, backend APIs, or the database.

Sprint 26 adds Canvas Quick Generate v1. Selecting a shot node on the project canvas now exposes a compact Inspector workflow for editing prompts, generating first-frame and end-frame candidates, adopting them, and generating/adopting a first-last-frame video. Sprint 26B adds a unified quick-generate preview/execute API, backend request idempotency, deterministic workflow routing, and system-owned canvas output synchronization while continuing to reuse the existing task, run, workflow, runner, provider, and output APIs. It does not add new ComfyUI workflows, download models, or automatically adopt outputs.

Sprint 27B adds the formal project Studio workspace at `/projects/:projectId/studio`. It introduces a creator-facing start page, project session restore, real project summaries, deterministic next-step guidance, and stable links back to the existing canvas, shot workbench, generation center, timeline, and asset pages. It does not add backend APIs, database migrations, ComfyUI changes, or a new generation execution path.

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
POST   /api/projects/{project_id}/shots/{shot_id}/prompt-draft
GET    /api/projects/{project_id}/assets/picker-options
GET    /api/projects/{project_id}/characters/{character_id}/asset-summary
GET    /api/projects/{project_id}/scenes/{scene_id}/asset-summary
GET    /api/projects/{project_id}/shots/{shot_id}/asset-summary
GET    /api/projects/{project_id}/shots/{shot_id}/production-status
GET    /api/projects/{project_id}/production-status
GET    /api/projects/{project_id}/timeline
GET    /api/projects/{project_id}/exports
POST   /api/projects/{project_id}/exports
GET    /api/projects/{project_id}/exports/{export_id}
POST   /api/projects/{project_id}/exports/{export_id}/mark-ready
POST   /api/projects/{project_id}/exports/{export_id}/start

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

GET    /api/projects/{project_id}/generation-tasks

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

The unified Asset Picker is read-only and currently supports project or shot-scoped selection for characters, scenes, frame images, character looks, scene states, and shot-context reference images. Actual changes still go through the existing shot, shot-reference, keyframe-task, or video-task APIs.

The Prompt / Context Builder is read-only and rule-based. It builds editable prompt drafts from the current shot context, does not call LLMs or vision models, does not save Prompt Draft records, and does not trigger ComfyUI. Keyframe and video task panels can fill their existing form fields from the draft, but users must still save and start generation manually. Sprint 13.1 adds request-scoped style presets and one-time action, motion, camera, visual-style, and mood overrides; these controls are not persisted. Sprint 14 can create real first-frame, end-frame, and video task drafts from a Prompt Draft by reusing the existing create and update task APIs; it still does not mark tasks ready or start generation automatically. Sprint 19-20 writes structured keyframe task `purpose` values for first-frame and end-frame tasks, and can ask the user whether adopted first/end frame outputs should be filled into a newly created video task draft.

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

Production Pipeline v1 is a read-only orchestration layer over existing data. The shot workbench shows six production steps: assets, Director Prompt, first frame, end frame, video, and final adoption. The project production board at `/projects/:projectId/production` summarizes the same status across shots. It never starts generation or adopts outputs automatically.

Timeline & Final Export v1 reads only explicitly adopted video outputs. A project export stores a creation-time snapshot of the current timeline clips, so later shot or adoption changes do not silently alter an existing export draft. Export execution uses local FFmpeg/FFprobe from `LDS_API_FFMPEG_BIN` and `LDS_API_FFPROBE_BIN`, normalizes clips to H.264 `yuv420p`, scale-pads to the target size, concatenates without audio, and stores the final MP4 as a safe platform `MediaAsset`. The API never returns absolute filesystem paths.

## Frontend

```powershell
cd apps\web
npm install
npm run dev
```

Open `http://localhost:5173`.

Routes:

- `/projects`: project list.
- `/projects/:projectId`: project overview.
- `/projects/:projectId/studio`: formal Studio workspace and smart continuation entry.
- `/projects/:projectId/canvas`: project creative canvas and storyboard.
- `/projects/:projectId/assets`: project asset library hub.
- `/projects/:projectId/characters`: project character library.
- `/projects/:projectId/characters/:characterId`: character detail, looks, and reference images.
- `/projects/:projectId/scenes`: project scene library.
- `/projects/:projectId/scenes/:sceneId`: scene detail, states, and reference images.
- `/projects/:projectId/shots`: project shot workbench.
- `/projects/:projectId/shots/:shotId`: project shot workbench with a selected shot.
- `/projects/:projectId/production`: project production board.
- `/projects/:projectId/timeline`: project timeline and final export.
- `/projects/:projectId/generation`: project generation center.
- `/projects/:projectId/media`: project media library, including completed final exports.
- `/projects/:projectId/settings`: project settings placeholder.

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
LDS_API_FFMPEG_BIN=ffmpeg
LDS_API_FFPROBE_BIN=ffprobe
LDS_API_EXPORT_TIMEOUT_SECONDS=1800
```

The frontend never receives the ComfyUI base URL, workflow JSON, local paths, or model paths.

## Sprint 24 Project Canvas

Project Canvas & Storyboard v1 adds a project-level creative map backed by Alembic-managed canvas tables. Canvas nodes and semantic edges are persisted separately from business entities; they do not modify shot bindings, generation tasks, adopted outputs, exports, or ComfyUI execution. See `docs/sprint-24-project-canvas.md`.
