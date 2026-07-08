# Sprint 12.1: Asset Picker Extension v1

Sprint 12.1 extends the unified Asset Picker into shot-context asset operations without changing generation execution, ComfyUI workflows, or the database schema.

## Scope

This sprint adds picker support for:

- `character_look`: choose a look for an existing shot character.
- `scene_state`: choose a state for the current shot scene.
- `reference_image`: choose reference images from the current shot context.

The picker options API remains read-only. User actions still go through the existing write APIs for shot characters, shots, shot references, and keyframe task references.

## API Extension

```http
GET /api/projects/{project_id}/assets/picker-options
```

Additional supported query parameters:

- `asset_type`: now also accepts `character_look`, `scene_state`, and `reference_image`.
- `character_id`: required for `character_look`.
- `scene_id`: required for `scene_state`.
- `shot_character_id`: optional current shot-character binding state for look picks.
- `task_id`: optional current keyframe task state for reference-image picks.
- `source=shot_context`: required direction for `reference_image` in this sprint.

`reference_image` is restricted to `scope=shot` and the current shot context. It can return:

- Existing `ShotReference` images.
- Character reference images available through characters already bound to the shot.
- Scene reference images available through the shot's selected scene state.

The response still returns safe display fields and metadata only. It does not return storage roots, local absolute paths, `relative_path`, or stored filenames.

## Frontend Integrations

Shot workbench:

- Change a shot character's look from the Asset Picker.
- Change the shot scene state from the Asset Picker.
- Add a shot reference from current shot-context reference-image options.

Keyframe task editor:

- Add task references through the Asset Picker only when the item is already an existing shot reference.
- Raw character or scene reference candidates are shown as unavailable for direct task insertion.
- Keyframe task writes continue to submit `shot_reference_id` through the existing task-reference API.

## Safety And Boundaries

- No database migration.
- No ComfyUI provider, runner, workflow JSON, or manifest changes.
- No Prompt Builder.
- No automatic prompt generation.
- No automatic recommendation or binding.
- No multi-select.
- No global media library picker.
- No raw `CharacterReference` or `SceneReference` direct insertion into keyframe tasks.
- No changes to video start-frame or end-frame selection behavior.

## Known Limits

- Reference-image filtering is intentionally minimal and scoped to the current shot context.
- Keyframe tasks cannot directly consume raw asset-library references until the user first binds them to the shot.
- Advanced Asset Picker filters, multi-select, and a full media library remain deferred.
