# Local Drama Studio Web

React + TypeScript + Vite frontend for the Local Drama Studio workbench.

## Run

```powershell
npm install
npm run dev
```

Open `http://localhost:5173`.

## Test

```powershell
npm run typecheck
npm run test
```

## Shot Recommendations

The shot workbench includes a "智能推荐" tab in the reference panel. Recommendations are
computed from shot parameters and existing asset metadata, do not use trained models, and
never bind automatically. Manual character reference, scene reference, and selected-asset
tabs remain available.

## Vision Analysis

Character and scene reference cards can start user-triggered image analysis when the backend is
configured. Results are shown as suggestions in a review dialog. Users may accept selected fields,
edit final values before accepting, reject a suggestion, or run analysis again. Boolean semantic
flags such as identity anchor, spatial anchor, and empty plate are never selected automatically.

If the backend has no provider key, manual asset management remains fully usable and the analysis
action shows a safe Chinese error.

## Keyframe Tasks And Generation

The shot workbench includes a keyframe task panel. It can create, edit, duplicate, delete, mark
ready, mark draft, manage task-level references from the current shot's already-bound references,
and start the first local ComfyUI keyframe run when the backend provider and workflow are ready.

Sprint 8 only supports the fixed `keyframe_basic_v1` basic txt2img workflow. The generation area
always explains that the current workflow uses only prompts and generation parameters, not task
reference images. It does not support batch generation, reference-image workflows, Custom Nodes,
model downloads, cancellation, video generation, or automatic binding.

## Routes

- `/projects`: project list.
- `/projects/:projectId`: project detail.
- `/projects/:projectId/characters`: project character library.
- `/projects/:projectId/characters/:characterId`: character details, looks, and reference images.
- `/projects/:projectId/scenes`: project scene library.
- `/projects/:projectId/scenes/:sceneId`: scene details, states, and reference images.
- `/projects/:projectId/shots`: project shot workbench.
- `/projects/:projectId/shots/:shotId`: shot detail, bindings, recommendations, and keyframe task preparation.
- `/characters`, `/scenes`, `/shots`, `/tasks`: top-level guide or empty states when no project context is selected.

User-visible product copy defaults to Simplified Chinese. Keep future language expansion lightweight and avoid large i18n frameworks until explicitly needed.
