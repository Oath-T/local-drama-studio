# Sprint 26: Canvas Quick Generate v1

Sprint 26 adds a node-local quick generation panel to the project canvas Inspector.

## Scope

When a shot node is selected on the canvas, the Inspector can now:

- Show the shot's bound character, scene, and reference count context.
- Build an editable Prompt draft from the existing Prompt / Context Builder.
- Preview workflow routing and missing inputs before starting a run.
- Create or reuse a first-frame keyframe task through the unified quick-generate API.
- Submit a first-frame keyframe run through the existing ComfyUI keyframe runner.
- Show first-frame output candidates and let the user adopt one.
- Create or reuse an end-frame keyframe task.
- Submit an end-frame keyframe run and let the user adopt one.
- Create or reuse a video task using the adopted first and end frame outputs.
- Submit a video run through the existing video generation runner.
- Show video candidates and let the user adopt one.
- Synchronize completed outputs back to canvas image/video nodes with system-owned
  `generated_from` edges.

## Architecture

Sprint 26A was implemented as a frontend orchestration panel. Sprint 26B adds a backend
orchestration layer while still reusing the existing task, run, output, runner, provider,
and workflow infrastructure.

New backend pieces:

- Workflow Capability Registry for executable API workflows.
- Deterministic Workflow Router for first frame, end frame, and video modes.
- `POST /api/projects/{project_id}/shots/{shot_id}/quick-generate/preview`.
- `POST /api/projects/{project_id}/shots/{shot_id}/quick-generate`.
- A small `quick_generate_requests` table for backend request idempotency.
- Canvas output synchronization that creates or reuses image/video nodes and system-owned
  `generated_from` edges.

The quick-generate execute API does not introduce a new runner. It creates or updates the
existing KeyframeTask or VideoTask, marks it ready, creates a normal Run, and starts the
existing background runner.

## Boundaries

- The panel does not expose ComfyUI internal nodes.
- The panel does not auto-adopt outputs; the user must choose candidates.
- The panel does not change Run, Output, MediaAsset, or adopted-output semantics.
- `generated_from` edges are system-owned and read-only for users.
- The existing shot workspace, advanced task panels, generation center, and timeline export remain available.
- No ComfyUI workflow JSON, manifest, model directory, or provider logic is changed.

## Known Limits

- The first version keeps advanced generation settings minimal.
- Keyframe generation still uses the existing fixed keyframe workflow.
- Video generation still depends on an available first-last-frame video workflow.
- If the current ComfyUI instance lacks Wan2.2 model files, the video workflow is reported
  as unavailable and no video Run is created. Keyframe generation remains independently usable.
- There is no LLM Agent and no automatic adoption.
