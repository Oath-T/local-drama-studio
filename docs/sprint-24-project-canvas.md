# Sprint 24: Project Canvas & Storyboard v1

Sprint 24 introduces the project-level creative canvas as the new project entry direction. The existing Sprint 23 shot workspace remains available as the detailed Shot Inspector and is not removed.

## Scope

- Adds `/projects/{project_id}/canvas`.
- Adds persistent project canvas data: canvas, nodes, and semantic edges.
- Adds workflow and storyboard views.
- Adds a collapsible asset drawer for existing characters, scenes, shots, and generated outputs.
- Adds a right-side Inspector / assistant placeholder.
- Adds bottom toolbar actions for adding nodes, connecting selected nodes, auto layout, fit view, undo, redo, and deletion.

## Boundaries

- Canvas semantic edges do not modify shot bindings, generation tasks, project exports, adopted outputs, or media assets.
- The UI does not expose ComfyUI internal nodes.
- This sprint does not add LLM Agent behavior, Workflow Router behavior, in-node generation, or drag-to-business-binding.
- Existing shot workspace, generation center, production board, timeline export, ComfyUI runner, provider, manifests, and workflow JSON remain unchanged.

## Data Model

The canvas uses three tables:

- `project_canvases`
- `project_canvas_nodes`
- `project_canvas_edges`

Every mutating canvas API uses optimistic revision checks. A stale revision returns a conflict instead of silently overwriting another editor.

## First Node Types

- `text`
- `character`
- `scene`
- `shot`
- `image`
- `video`
- `export`

## First Semantic Edge Types

- `uses_character`
- `uses_scene`
- `identity_reference`
- `look_reference`
- `scene_reference`
- `pose_reference`
- `start_frame`
- `end_frame`
- `continuity_from`
- `generated_from`
- `included_in_export`

## Deferred

Sprint 25 should connect drag-and-drop assets to real binding flows. Sprint 26 should introduce node-local generation through an approved Workflow Router. Sprint 27 can add assistant planning with explicit user confirmation.
