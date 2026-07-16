# Sprint 26: Canvas Quick Generate v1

Sprint 26 adds a node-local quick generation panel to the project canvas Inspector.

## Scope

When a shot node is selected on the canvas, the Inspector can now:

- Show the shot's bound character, scene, and reference count context.
- Build an editable Prompt draft from the existing Prompt / Context Builder.
- Create or reuse a first-frame keyframe task.
- Submit a first-frame keyframe run through the existing ComfyUI keyframe generation API.
- Show first-frame output candidates and let the user adopt one.
- Create or reuse an end-frame keyframe task.
- Submit an end-frame keyframe run and let the user adopt one.
- Create or reuse a video task using the adopted first and end frame outputs.
- Submit a video run through the existing video generation API.
- Show video candidates and let the user adopt one.

## Architecture

This sprint is frontend-only. It reuses existing APIs:

- Keyframe task create, update, mark-ready, run, and output selection.
- Video task create, update, mark-ready, run, and output selection.
- Prompt draft generation.
- Existing workflow availability and provider capability checks.

The quick panel does not add a backend endpoint, database table, migration, runner, provider, workflow JSON, or manifest.

## Boundaries

- The panel does not expose ComfyUI internal nodes.
- The panel does not auto-adopt outputs; the user must choose candidates.
- The panel does not change Run, Output, MediaAsset, or adopted-output semantics.
- The panel does not create `generated_from` canvas edges in v1.
- The existing shot workspace, advanced task panels, generation center, and timeline export remain available.

## Known Limits

- The first version keeps advanced generation settings minimal.
- Keyframe generation still uses the existing fixed keyframe workflow.
- Video generation still depends on an available first-last-frame video workflow.
- Canvas output nodes and system-owned `generated_from` edges are deferred to a later sprint.
