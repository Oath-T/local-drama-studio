# Sprint 27B: Formal Studio Workspace

Sprint 27B promotes the Studio shell from the `/dev/studio-ui` demo into a real project route:

```text
/projects/:projectId/studio
```

The route is a creator-facing project entry point. It organizes existing project data into a formal Studio workspace without replacing the current canvas, shot workbench, generation center, timeline, or asset pages.

## Scope

- Project top bar with project identity, backend health, ComfyUI capability, and layout/session save status.
- Left global navigation and a project context panel with overview, shot, and asset tabs.
- Center Studio area with start page, storyboard summary, workflow entry, and shot console entry.
- Right Inspector with information and next-step guidance.
- Bottom workspace for running task and issue summaries.
- Project-scoped Studio session persistence in `localStorage`.
- URL context support for `shotId`, `entityType`, `entityId`, and `intent`.
- Deterministic smart continuation recommendation based on real project state.
- Safe empty, partial-failure, and backend-disconnected states.

## Session Model

The frontend stores a project-scoped Studio session with:

```text
schemaVersion
projectId
currentMode
currentView
selectedShotId
contextTab
inspectorTab
bottomTab
bottomOpen
lastRoute
updatedAt
```

Invalid, corrupted, mismatched, or stale sessions fall back to a default session. A selected shot that no longer exists is cleared instead of crashing the page.

`恢复默认布局` resets the resizable panel layout. `清除工作现场` clears the Studio session for the current project.

## Recommendation Rules

The next-step recommendation is deterministic and does not call an LLM. It uses the current project counts, production status, generation task summaries, timeline export readiness, and video workflow availability.

Priority:

1. No character assets: create a character.
2. Characters exist but no scenes: create a scene.
3. Characters and scenes exist but no shots: create a shot.
4. Current or next incomplete shot is missing an adopted first frame: generate first frame.
5. Adopted first frame exists but adopted end frame is missing: generate end frame.
6. Adopted first and end frames exist but adopted video is missing: generate video if the video workflow is available; otherwise check generation settings.
7. Blocking or failed generation state: review production issues.
8. Continue the next incomplete shot.
9. All shots have adopted video: open the timeline/export page.

No recommendation writes data or starts generation automatically.

## Boundaries

Sprint 27B does not add backend API, Alembic migration, ComfyUI workflow changes, model downloads, workflow routing changes, node-based generation, or an Agent. It only composes existing read APIs and routes into a more usable Studio entry.

The old project canvas remains available at `/projects/:projectId/canvas`. The shot workbench and quick generation flows remain available on their existing routes.

