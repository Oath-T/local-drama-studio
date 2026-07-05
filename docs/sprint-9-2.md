# Sprint 9.2: Wan2.2 14B FLF2V Workflow Definition

Sprint 9.2 adds the real ComfyUI API workflow definition for `video_wan22_14b_flf2v_v1`.

The workflow JSON was exported manually from ComfyUI by the user and is stored as a small built-in workflow definition. It is not a model file, generated video, database, storage asset, or local ComfyUI output.

## Scope

- Include `workflows/video_wan22_14b_flf2v_v1.json`.
- Keep only the normalized workflow filename.
- Update `workflows/video_wan22_14b_flf2v_v1.manifest.json` to bind the real ComfyUI node IDs.
- Inject uploaded `start_frame` and `end_frame` filenames through manifest image bindings.
- Inject prompt, size, fps, seed, and computed length through manifest parameter bindings.
- Save only allowed video outputs from the manifest output node.

This sprint does not download models, install Custom Nodes, modify the user's ComfyUI directory, add arbitrary workflow editing, add video evaluation, add batch generation, or call any cloud service.

## Workflow Mapping

The manifest maps platform fields to the ComfyUI API workflow:

- `start_frame`: node `80`, input `image`
- `end_frame`: node `89`, input `image`
- `positive_prompt`: node `90`, input `text`
- `negative_prompt`: node `78`, input `text`
- `width`: node `81`, input `width`
- `height`: node `81`, input `height`
- `length_frames`: node `81`, input `length`
- `fps`: node `86`, input `fps`
- `seed`: node `84`, input `noise_seed`
- output: node `83`, `SaveVideo`

Node `87` keeps the workflow export behavior:

- `noise_seed = 0`
- `add_noise = disable`

## Length Calculation

ComfyUI node `81.length` is a frame count, not seconds.

The platform computes:

```text
length = duration_seconds * fps + 1
```

The computation uses the explicit `duration_seconds_times_fps_plus_one` binding type. The runner does not evaluate arbitrary expressions.

## Negative Prompt

If the user provides `negative_prompt`, it replaces node `78.text`.

If the user leaves `negative_prompt` empty, node `78.text` keeps the default negative prompt exported in the workflow JSON.

## Safety Checks

Workflow loading rejects:

- ComfyUI UI workflow format with top-level `nodes`, `links`, or `groups`.
- Windows absolute paths such as `C:\` or `F:\`.
- Unix user paths such as `/Users/` or `/home/`.
- Base64 and `data:image` or `data:video` payloads.
- Abnormally long strings.
- Missing required nodes or input bindings.
- Missing or invalid `SaveVideo` output node for this workflow.

Local model filenames such as `.safetensors` references are allowed because they are configuration references inside the workflow, not model file contents.

## Output Handling

The runner reads only manifest `output_node_ids`, currently node `83`.

It checks output keys in this order:

```text
videos, files, gifs, images
```

It saves only:

```text
mp4, webm, mov, gif
```

Preview images, ComfyUI URLs, absolute paths, and local storage paths are not returned to the frontend.

## First Real Test Recommendation

Local 14B video generation can be very slow. That is expected.

For the first real test, use:

- `duration_seconds = 2` or `3`
- `fps = 16`
- `width = 640`
- `height = 640`
- fixed seed

## Known Limits

- The platform assumes the user's local ComfyUI already has the required models and nodes.
- The placeholder image names inside the JSON do not need to exist because runtime uploads replace them.
- Failed local ComfyUI execution is reported through the existing video run error flow.
