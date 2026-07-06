# Sprint 12: Unified Asset Picker v1

Sprint 12 adds the first shared Asset Picker foundation so shot and generation workflows can choose existing project assets from one consistent dialog.

## Scope

This sprint implements:

- A reusable frontend `AssetPickerDialog`.
- A read-only picker options API.
- Shot character selection from the project character library.
- Shot scene selection from the project scene library.
- Video task start-frame and end-frame selection from available frame images.

The picker is intentionally conservative. It does not automatically bind assets, generate prompts, run models, or change ComfyUI execution behavior.

## Read-only API

```http
GET /api/projects/{project_id}/assets/picker-options
```

Supported query parameters:

- `scope`: `project` or `shot`.
- `asset_type`: `character`, `scene`, or `frame_image`.
- `shot_id`: required for shot-scoped picks and frame-image picks.
- `q`: optional search text.
- `limit`: optional item limit.

The response returns safe display fields only, including name, description, media URLs, badges, selection state, source labels, and metadata needed by the current UI. It does not return local absolute paths, storage roots, `relative_path`, or stored filenames.

## Current Integrations

Shot workbench:

- Add a shot character from the picker.
- Change the shot scene from the picker.

Video task editor:

- Choose `start_frame` from existing frame assets.
- Choose `end_frame` from existing frame assets.

Frame-image candidates are gathered from existing video frame inputs, keyframe outputs, and shot reference images for the current shot. The picker only selects an existing media asset or keyframe output; the existing video task update flow still saves the actual task input.

## Safety And Boundaries

- No database migration.
- No writes from the picker options API.
- No ComfyUI provider, runner, workflow JSON, or manifest changes.
- No full media library picker.
- No keyframe task reference picker in this sprint.
- No automatic context selection or prompt generation.

## Deferred

- Full reference image picker.
- Character look picker.
- Scene state picker.
- Asset Picker integration for keyframe task references.
- Advanced filtering and sorting.
- Global media library management.
