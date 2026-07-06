# Sprint 11: Callable Asset Library v1

Sprint 11 makes the relationships between character assets, scene assets, shots, and generation tasks visible without changing generation behavior.

This sprint adds read-only asset summaries:

- Character asset summary.
- Scene asset summary.
- Shot asset binding summary.
- Keyframe task inherited shot-asset context.
- Video task shot-context display.

## Scope

The summaries answer:

- Which character assets can be used for generation.
- Which scene assets can be used for generation.
- Which character and scene assets a shot currently binds.
- Which shot context a keyframe or video task inherits or displays.

Asset completeness is advisory only. Missing identity anchors, spatial anchors, default looks, or reference images are shown as warnings and do not block saving, marking ready, or starting existing generation flows.

## Read-only APIs

```http
GET /api/projects/{project_id}/characters/{character_id}/asset-summary
GET /api/projects/{project_id}/scenes/{scene_id}/asset-summary
GET /api/projects/{project_id}/shots/{shot_id}/asset-summary
```

These endpoints:

- Do not cross project boundaries.
- Do not trigger generation.
- Do not mutate tasks, runs, outputs, references, media assets, or files.
- Do not return local absolute paths, storage roots, `relative_path`, or stored filenames.
- Do not require a database migration.

## Default Display Rules

Character summaries use existing data only:

- Default look: `is_default=true`, otherwise earliest created look.
- Identity references: `is_identity_anchor=true`.
- Primary display references: `is_primary=true`.
- Face and full-body coverage are derived from existing reference metadata.

Scene summaries use existing data only:

- Default state: `is_default=true`, otherwise earliest created state.
- Spatial references: `is_spatial_anchor=true`.
- Empty plates: `is_empty_plate=true`.
- Wide/environment coverage is derived from existing scene reference metadata.

No new fields are written for these rules.

## Generation Task Context

Keyframe tasks already store a shot snapshot and copied task references. Sprint 11 displays that inherited context.

Video tasks directly use start frame, end frame, prompt, workflow, and parameters. Sprint 11 may display the source shot context, but it must not imply character or scene reference images are directly sent to the video workflow unless a future workflow actually passes them as inputs.

## Deferred

- Full Asset Picker.
- Automatic asset selection.
- Automatic binding.
- Prompt Builder.
- Batch generation.
- Media library management.
- Any ComfyUI provider, runner, workflow JSON, or manifest changes.
