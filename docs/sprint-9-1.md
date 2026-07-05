# Sprint 9.1: Role-Based Video Frame Inputs

Sprint 9.1 extends local video generation task preparation from one legacy input image to role-based frame inputs.

## Scope

- Add `VideoGenerationTaskInput` records for video task inputs.
- Support the first two roles only:
  - `start_frame`
  - `end_frame`
- Keep `video_generation_tasks.input_media_asset_id` as the legacy start-frame field.
- Treat old tasks with no input rows and a legacy input image as having a `start_frame`.
- Add a manifest placeholder for `video_wan22_14b_flf2v_v1`.
- Show start-frame and end-frame slots in the existing video generation panel.

This sprint does not add real workflow JSON files, model downloads, Custom Node installation, batch upload, drag-and-drop, pose/depth/control references, video evaluation, or automatic generation.

## Data Model

`video_generation_task_inputs` stores one row per task input role:

- `task_id`
- `role`
- `media_asset_id`
- optional keyframe output source fields
- stable `sort_order`

The first version keeps a unique `task_id + role` constraint. A single task can have at most one `start_frame` and one `end_frame`.

`media_asset_id` uses `ON DELETE SET NULL`. The input row remains, so readiness can report a role-specific missing or unavailable input instead of silently removing the role.

## Compatibility

Legacy Sprint 9 tasks are still readable:

- If input rows exist, the service uses them.
- If no input rows exist and `input_media_asset_id` exists, the service exposes it as a synthetic `start_frame`.
- Create and update requests may still use the legacy single-image fields.
- New frontend writes role-based `inputs`.

Run snapshots now use `schema_version=2` and include:

```json
{
  "inputs": [
    { "role": "start_frame", "media_asset_id": "..." },
    { "role": "end_frame", "media_asset_id": "..." }
  ]
}
```

Old `schema_version=1` snapshots with `input_media_asset_id` remain readable by the runner.

## Workflow Modes

Workflow manifests now declare:

- `mode`
- `required_input_roles`
- role-specific image bindings

Default legacy behavior is:

```text
mode = single_image_to_video
required_input_roles = [start_frame]
```

`first_last_frame_to_video` requires both `start_frame` and `end_frame`. If a first-last manifest does not declare `end_frame`, the workflow is unavailable.

The repository includes:

```text
workflows/video_wan22_14b_flf2v_v1.manifest.json
```

The matching real workflow JSON is intentionally not committed. Until the user provides it locally, the workflow is shown as unavailable.

## Readiness

Readiness is calculated dynamically:

- missing start frame
- missing end frame
- role media unavailable
- role media is not an image
- workflow unavailable
- first-last workflow missing an end-frame role declaration

Using the same image for start and end produces a warning, not a blocking issue.

## Runner Behavior

The runner reads the frozen run snapshot, uploads required role images to ComfyUI in manifest role order, and injects each uploaded image into the role-specific workflow binding.

If any role upload fails, the runner marks the run failed and does not submit `/prompt`.

## Known Limits

- No real `video_wan22_14b_flf2v_v1.json` is shipped.
- The UI supports simple upload slots only.
- No shared media input library or batch upload.
- No cancellation change from Sprint 9.
- The legacy `input_media_asset_id` field remains for compatibility and can be removed only through a future migration plan.
