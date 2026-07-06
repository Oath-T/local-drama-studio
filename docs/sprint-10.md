# Sprint 10: Information Architecture And Workbench UI Consolidation

Sprint 10 reorganizes Local Drama Studio from feature accumulation into a clearer local short-drama production workbench.

This sprint does not add model capability, change ComfyUI execution, change workflow JSON, change manifests, add batch generation, add cancellation, add cloud workers, or perform database migrations.

## Navigation

Project-level navigation is organized as:

- Project overview.
- Asset library.
  - Character library.
  - Scene library.
- Shot workbench.
- Generation center.
- Media library.
- Settings.

Global character, scene, shot, media, and generation routes should guide the user to select a project first. The app must not infer a hidden current project from local storage or temporary client state.

## Project Overview

The project overview uses existing project, character, scene, shot, and generation-task APIs to show real data:

- Project name and description.
- Character count.
- Scene count.
- Shot count.
- Keyframe task count.
- Video task count.
- Active generation task count.
- Selected output count.
- Recent shots.
- Recent generation tasks.
- Recent outputs.

If data is unavailable or empty, the page shows explicit empty states rather than fabricated examples.

## Generation Center

The generation center is a project-level read-only view of keyframe and video generation tasks.

It uses:

```http
GET /api/projects/{project_id}/generation-tasks
```

The endpoint is read-only. It does not trigger generation, mutate task status, modify runs, modify outputs, or modify media assets.

The first version supports filtering by:

- All.
- Keyframe.
- Video.
- Draft.
- Ready.
- Running.
- Completed.
- Failed.

## Shot Workbench Cleanup

The shot workbench keeps the existing three-column direction. Sprint 10 reduces right-panel noise by keeping task lists and summaries visible, while detailed task editing happens in dialogs.

The existing video generation flow remains intact:

- Save task.
- Mark ready.
- Return draft.
- Start generation.
- View runs.
- View outputs.
- Select or unselect output.

## ComfyUI Impact

Sprint 10 must not touch:

- ComfyUI provider.
- Generation runner.
- Workflow JSON.
- Workflow manifests.
- Active run handling.

Existing running ComfyUI jobs are not restarted or interrupted by this UI consolidation.

## Known Limits

- The media library is a clear placeholder, not a full media manager.
- Settings is a clear placeholder, not a full configuration system.
- Asset Picker is intentionally deferred.
- Character and scene asset database upgrades are deferred.
- Project-level generation task summaries do not expose local paths or provider URLs.
