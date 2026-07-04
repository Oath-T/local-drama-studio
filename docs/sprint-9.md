# Sprint 9: Local ComfyUI Image-To-Video Run

Sprint 9 adds a local, user-triggered image-to-video generation loop. It is separate from Sprint 8 keyframe image generation and does not upgrade or replace the `keyframe_basic_v1` image workflow.

## Scope

- Create and edit video generation tasks for a shot.
- Accept one safe platform image as the input image.
- Submit a ready task to local ComfyUI through a provider-neutral runner.
- Poll queue and history state without blocking API startup.
- Save completed video-like outputs as platform `MediaAsset` records.
- Preview saved outputs through the existing safe media content endpoint.

This sprint does not implement cloud services, multi-machine workers, model downloads, Custom Node installation, arbitrary workflow upload or editing, batch generation, timeline editing, subtitles, dubbing, music, cancellation, ComfyUI `/interrupt`, or video quality agents.

## Data Model

`VideoGenerationTask` stores the editable task definition:

- `shot_id`
- `input_media_asset_id`
- `workflow_id`
- `status`: `draft` or `ready`
- prompt and negative prompt
- width, height, fps, duration, seed, and motion strength

`VideoGenerationRun` stores one execution attempt:

- `status`: `queued`, `running`, `completed`, `failed`, or `interrupted`
- frozen task snapshot
- frozen seed
- provider job id and safe error code/message

`VideoGenerationOutput` stores generated outputs for a run:

- linked `MediaAsset`
- provider filename, subfolder, type, node id, and output index
- selected output flag

Readiness is calculated dynamically and is not stored.

## Input Images

Supported input sources:

1. A `KeyframeGenerationOutput` media asset.
2. An existing project image `MediaAsset`.
3. A minimal project-level input image upload that creates a `MediaAsset` only.

Before submitting to ComfyUI, the runner validates that the input asset is an image, the resolved file exists, and the resolved path stays inside the configured storage directory. The runner uploads the file to ComfyUI `/upload/image` with a safe generated filename and injects only the returned `filename`, `subfolder`, and `type` into the workflow.

## Workflow Manifest

The repository commits only:

```text
workflows/video_i2v_14b_v1.manifest.json
```

The real ComfyUI API workflow file is expected at runtime as:

```text
video_i2v_14b_v1.json
```

If the JSON file is missing, invalid, or does not satisfy the manifest bindings, the workflow is reported as unavailable. The UI shows a Chinese unavailable reason and does not pretend that real video generation is ready.

## Output Parsing

Video output discovery is manifest-driven. The manifest can define candidate output keys such as:

```json
["videos", "gifs", "files", "images"]
```

The provider filters candidates by `filename`, `subfolder`, `type`, extension, and MIME type. Supported extensions are:

```text
mp4, webm, mov, gif
```

Saved platform files are served by `/api/media/{media_asset_id}/content`. The frontend never receives local paths, ComfyUI URLs, workflow JSON, or storage roots.

## Run Lifecycle

Run creation always happens before submitting to ComfyUI:

1. Re-read the task.
2. Recalculate readiness.
3. Require `task.status=ready`.
4. Require a selected and available workflow.
5. Require provider connectivity.
6. Reject another active run for the same task.
7. Freeze seed and task snapshot.
8. Commit a queued run.
9. Start the background runner with only `run_id`.

Startup recovery marks active runs without provider job ids as `interrupted`. Runs with provider job ids are synchronized through ComfyUI history and queue checks. Recovery errors are logged and do not block API startup.

## Seed Rules

- `seed=null`: randomize once when creating a run and persist the frozen value.
- `seed=0`: valid and preserved.
- `seed>0`: valid and preserved.
- Retry creates a new run and does not overwrite an old run.

## Persistence Rules

`MediaAsset` now supports `video`. Video assets may have no thumbnail. Existing character, scene, and keyframe image logic continues to use image media.

Output saving is idempotent by:

```text
run_id + provider filename + provider subfolder + provider type + output_index
```

If database persistence fails after a new platform video file is written, the runner attempts to remove the new platform file. It never deletes the original ComfyUI output.

## Frontend

The shot workbench keeps the existing three-column layout. The `视频生成` panel appears below the keyframe task area and provides:

- task creation and editing
- input image upload
- ready/draft controls
- disabled run reasons
- run history
- safe video preview with `<video controls>`
- download through the platform media content URL

No autoplay or loop is enabled.

## Known Limits

- Real video generation requires the user to provide a compatible local ComfyUI API workflow JSON and required local models/nodes.
- Automated tests use stubs and do not prove real ComfyUI video output works.
- No cancellation or ComfyUI interrupt.
- No output cleanup tool for orphaned generated video files.
- Video duration and dimensions are stored from the frozen task snapshot; Sprint 9 does not probe generated video streams.
