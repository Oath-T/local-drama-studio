# Sprint 8: Local ComfyUI Keyframe Run

Sprint 8 adds a user-triggered local keyframe generation run for prepared keyframe tasks. It is a narrow execution layer on top of Sprint 7 task preparation.

## Scope

- Register the fixed `keyframe_basic_v1` workflow.
- Submit one ready keyframe task to local ComfyUI.
- Persist a generation run before the background runner starts.
- Poll ComfyUI queue/history until the run completes, fails, or times out.
- Save completed images as platform `MediaAsset` records and expose them through the existing safe media endpoints.
- Let the user select one generated output per keyframe task.

This sprint does not implement video generation, cancellation, batch generation, reference-image workflows, IP-Adapter, ControlNet, Custom Nodes, model downloads, automatic asset binding, or ComfyUI `/interrupt`.

## Basic Workflow

`keyframe_basic_v1` is a basic txt2img API workflow using only built-in ComfyUI node types:

- `CheckpointLoaderSimple`
- `CLIPTextEncode`
- `EmptyLatentImage`
- `KSampler`
- `VAEDecode`
- `SaveImage`

The committed workflow file is auditable JSON. It contains no absolute paths, user directories, Base64 image payloads, output history, UI coordinates, real checkpoint filename, or Custom Node dependencies.

The real checkpoint is injected from:

```text
LDS_API_COMFYUI_DEFAULT_CHECKPOINT
```

If this value is empty, the API still starts and the provider may still report online, but the workflow is unavailable and run creation returns `workflow_model_missing`.

## Reference Inputs

The first workflow intentionally does not use task character or scene reference images. The UI must always show:

```text
当前基础工作流仅使用提示词和生成参数，不使用任务中的参考图。
```

Run snapshots still keep task reference IDs for audit, but also store:

```json
{
  "reference_inputs_used": false
}
```

Future reference-image workflows must be added as separate workflow manifests instead of changing this value implicitly.

## Run Lifecycle

1. The Service validates task readiness, output count, workflow availability, provider availability, sampler, scheduler, and checkpoint configuration.
2. The Service resolves the effective prompt and seed.
3. A queued run is committed to the database.
4. The background runner receives only `run_id`.
5. `/prompt` success stores `provider_job_id`; the run may remain queued until queue/history polling confirms progress.
6. Queue detection marks the run `running`.
7. History outputs mark the run `completed`; execution errors or timeout mark it `failed`.

Empty ComfyUI history is treated as an intermediate waiting state, not an immediate failure.

Startup recovery inspects active runs without blocking application startup. Runs without `provider_job_id` are marked `interrupted`; runs with a provider job are synchronized through history and queue polling.

## Prompt And Parameters

- `prompt_en` wins when non-empty; otherwise `prompt_zh` is used.
- The snapshot stores `effective_prompt_language` and `effective_positive_prompt`.
- The platform never concatenates or translates prompts in this sprint.
- `seed=null` is randomized once at run creation and persisted in the snapshot.
- `seed=0` is preserved.
- `output_count` must be exactly `1`; larger values return `workflow_output_count_unsupported`.
- Sampler and scheduler values must be supported by the workflow manifest. Unknown values return `workflow_sampler_unsupported` or `workflow_scheduler_unsupported`.

## Output Persistence

Generated outputs are downloaded from ComfyUI and stored through `MediaStorageService`. The platform validates image type, MIME type, dimensions, and maximum output size before creating media records.

Output de-duplication uses:

```text
run_id + provider_filename + provider_subfolder + output_index
```

If database persistence fails after a local file is written, the runner attempts to remove the newly written original and thumbnail files. It does not delete ComfyUI's original output.

Deleting a keyframe task cascades run and output database rows, but keeps generated `MediaAsset` rows and files for future cleanup tooling. This is an intentional Sprint 8 limitation.

## Capabilities

`GET /api/system/capabilities` reports provider reachability only:

```json
{
  "keyframe_generation": {
    "available": true,
    "provider": "comfyui",
    "status": "online"
  }
}
```

Workflow availability is reported separately by:

```text
GET /api/projects/{project_id}/keyframe-workflows
```

A provider can be online while `keyframe_basic_v1` is unavailable because the checkpoint is not configured or required node types are missing.

## Known Limits

- No cancellation or global ComfyUI interrupt.
- No reference-image generation workflow.
- No generated output cleanup when a task is deleted.
- No progress percentage; the UI shows stable queued/running/completed/failed states.
- Real generation requires a user-managed local ComfyUI instance and configured checkpoint.
