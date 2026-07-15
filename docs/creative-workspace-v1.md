# Creative Workspace v1

Sprint 23 starts the shift from an internal task form toward a creator-facing shot workspace.

## Goal

The shot page should make the main creative path feel shorter:

```text
Place references -> write prompt intent -> choose first frame / end frame / video -> generate
```

Sprint 23 implements the workspace frame only. It does not change generation APIs, ComfyUI workflows, runners, providers, manifests, or database schema.

## Workspace Structure

The shot workbench now presents three focused areas:

- **素材与参考**: reference slots for identity, appearance, environment, pose, composition, continuity, and video start/end frames.
- **当前画面与生成结果**: a large central result stage for first-frame, end-frame, or video outputs.
- **Prompt 与生成控制**: simplified prompt controls with advanced task details available on demand.

The existing professional panels remain available through advanced mode:

- shot metadata editing
- character and scene binding
- shot reference binding
- recommendations
- keyframe tasks
- video tasks
- production status

## Modes

The workspace has three creative modes:

- **首帧模式**
- **尾帧模式**
- **视频模式**

In Sprint 23, switching modes only changes the creative framing, result stage, reference slots, and next-step guidance. It does not automatically create tasks or start generation.

## Safety Boundaries

Sprint 23 deliberately does not implement:

- one-click generation
- automatic task creation
- automatic mark-ready
- automatic ComfyUI start
- drag-and-drop reference assignment
- workflow auto-assembly
- new model support
- backend API changes
- database migrations

The existing generation chain continues to run through the advanced task panels.

## Next Steps

Suggested follow-up sequence:

- **Sprint 24**: quick reference assignment interactions.
- **Sprint 25**: one-click task assembly using existing task APIs.
- **Sprint 26**: progressive advanced controls and clearer next-step guidance.

