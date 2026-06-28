# Sprint 3: Scene Asset Management

Sprint 3 adds project-scoped scene assets without implementing AI analysis, scene generation, shots, props, ComfyUI, batch upload, media sharing, or global scene libraries.

## Scope

- Scene CRUD.
- SceneState CRUD, default state management, and deletion rules.
- SceneReference upload, metadata editing, primary image, spatial anchor, empty plate, original preview, and deletion.
- Reuse of the existing `media_assets` table and `/api/media/{media_asset_id}` read endpoints.
- Backend and frontend tests for scene flows plus character/project regressions.

## Domain Boundaries

`Scene` stores stable place information:

- `name`
- `scene_type`
- `description`
- `fixed_environment_description`
- `spatial_layout_description`
- `visual_style_description`
- `prompt_environment`
- `notes`

`SceneState` stores environment changes:

- `time_of_day`
- `weather`
- `custom_weather`
- `lighting`
- `custom_lighting`
- `season`
- `environment_condition`
- `crowd_level`
- `prompt_state`

`SceneReference` stores image metadata only:

- `shot_scale`
- `camera_position`
- `custom_camera_position`
- `view_direction`
- `custom_view_direction`
- `composition_type`
- `custom_composition`
- `is_empty_plate`
- `is_primary`
- `is_spatial_anchor`
- `tags`
- `description`
- `notes`

Do not add official time, weather, lighting, or season fields to `SceneReference`; those belong to `SceneState`.

## Rules

- A scene can have no states.
- The first state becomes default.
- Later states do not automatically replace the default.
- Deleting the only state is rejected.
- Deleting a default state is allowed when more than one state exists; the backend selects the remaining earliest state by `created_at`, then `id`.
- The first reference in a state becomes primary.
- Setting a new primary reference clears the old primary reference.
- Deleting a primary reference selects the remaining earliest reference by `created_at`, then `id`.
- Primary, spatial anchor, and empty plate are independent flags.
- `weather`, `lighting`, `camera_position`, `view_direction`, and `composition_type` require their matching custom field when set to `custom`; non-custom values clear stale custom fields.

## Media Ownership

Scene references reuse `media_assets`. This sprint keeps a simple ownership rule: one scene reference owns one media asset, enforced for scene references by a unique `media_asset_id`.

Media sharing, many-to-many asset reuse, and global asset libraries are intentionally not implemented.

## File Cleanup

SQLite transactions and the local filesystem are not atomic together. Deletion uses the current minimal recoverable strategy:

1. Query and record original and thumbnail relative paths before deletion.
2. Delete database records and owned media assets in a transaction.
3. After commit, delete files from storage.
4. Missing files are treated as already cleaned.
5. Cleanup failures are logged as server warnings and do not roll back the committed database delete.
6. File delete paths are resolved and verified under `STORAGE_ROOT`.

Known limitation: failed post-commit file cleanup can leave orphan files. A future maintenance command should scan and remove orphaned files.

## Future Vision Analysis

Scene reference records reserve:

- `analysis_status`
- `suggestion_review_status`
- `analysis_suggestions`

Future model output must remain provider-neutral and enter the system as suggestions. A later Service-layer confirmation flow should validate suggestions, apply user-confirmed values to official metadata, and update review status. Sprint 3 does not implement a VisionAnalysisProvider, background task, AI button, or fake suggestions.
