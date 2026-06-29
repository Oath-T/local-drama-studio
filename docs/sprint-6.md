# Sprint 6: Vision Analysis Suggestions

Sprint 6 adds user-triggered reference-image analysis and a confirmation workflow for
character and scene reference metadata.

## Scope

- A replaceable `VisionAnalysisProvider` abstraction.
- OpenAI as the first real provider through the Responses API, image input, and Structured
  Outputs.
- Local `vision_analysis_tasks` records for status, attempts, safe errors, provider, and model
  audit information.
- In-process background execution with limited concurrency and frontend polling.
- Structured suggestions saved on the target reference only after schema validation.
- User review flows for accepting selected fields, editing final values, or rejecting suggestions.

This sprint does not train or fine-tune models, auto-analyze uploads, auto-overwrite official
metadata, auto-bind shot references, generate images or video, call ComfyUI, introduce Agents,
or add Redis/Celery/vector databases.

## Provider Boundary

Domain and API code use a provider-neutral `VisionAnalysisProvider` interface. Service and route
layers do not import the OpenAI SDK directly. Provider output is converted into internal Pydantic
schemas before it can be saved.

The OpenAI provider uses:

- `AsyncOpenAI`
- `responses.parse(...)`
- `input_image`
- `text_format=<PydanticModel>`
- `store=False`

The installed SDK version verified during development was `openai 2.44.0`. Local shape checks
confirmed `AsyncOpenAI.responses.parse` exposes `model`, `input`, `text_format`, and `store`.
Actual remote model capability must still be verified manually with the configured model and API
key.

## Task Lifecycle

Task statuses:

- `pending`
- `running`
- `completed`
- `failed`

Allowed transitions:

- `pending -> running`
- `pending -> failed`
- `running -> completed`
- `running -> failed`

Application startup marks stale `pending` and `running` tasks as `failed` with
`analysis_interrupted`. If the reference already had old suggestions, those suggestions remain
available and the reference returns to `completed`; otherwise the reference becomes `failed`.

Background tasks receive only `task_id`. They create a fresh database session, read the task and
media asset, commit status changes before provider calls, release database transactions during the
provider call, then open a fresh transaction to save completion or failure results.

This is intentionally a local single-process mechanism. It is not a reliable distributed queue,
and multiple workers do not share the in-process semaphore.

## Suggestion Review Rules

Suggestions and official metadata remain separate.

Normal reference PATCH endpoints never copy suggestions into official fields. Confirmation must
use the analysis confirmation endpoints.

Review status:

- `accepted`: all suggested official fields were accepted unchanged.
- `edited_and_accepted`: the user accepted a subset or edited values before accepting.
- `rejected`: no official metadata changed; suggestions remain viewable.

Boolean semantic flags are never selected by default:

- character `is_identity_anchor`
- scene `is_spatial_anchor`
- scene `is_empty_plate`

Custom enum fields are validated as pairs. For example, `expression=custom` requires
`custom_expression`, and non-custom values clear the custom field. Scene camera, view direction,
and composition custom fields follow the same rule.

## API

```text
GET  /api/system/capabilities
GET  /api/projects/{project_id}/vision-analysis/tasks/{task_id}

POST /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/analysis/tasks
GET  /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/analysis/latest-task
POST /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/analysis/confirm
POST /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/analysis/reject

POST /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/analysis/tasks
GET  /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/analysis/latest-task
POST /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/analysis/confirm
POST /api/projects/{project_id}/scenes/{scene_id}/states/{state_id}/references/{reference_id}/analysis/reject
```

`GET /api/system/capabilities` returns only safe availability data. It does not return API keys,
key fragments, model names, environment variable names, or full request configuration.

## Privacy And Safety

- The frontend never receives provider credentials.
- Images are sent only after the user clicks analysis.
- The backend reads the original `MediaAsset` file from `STORAGE_ROOT` and rejects traversal.
- Base64 data URLs are constructed only in memory.
- API responses, task errors, and logs must not include API keys, base64 image payloads, absolute
  paths, raw provider responses, or model reasoning.
- Prompt text instructs the provider to analyze visible information only and avoid real-person
  identity, sensitive attributes, celebrity comparisons, private addresses, and invisible facts.

## Manual Provider Acceptance

Automatic tests use stub providers and never call the real API.

For manual acceptance:

1. Configure `LDS_API_OPENAI_API_KEY` and `LDS_API_OPENAI_VISION_MODEL`.
2. Start the API and confirm `/api/system/capabilities` reports `available=true`.
3. Upload one non-sensitive character reference image and run analysis once.
4. Upload one non-sensitive scene reference image and run analysis once.
5. Confirm suggestions are structured, editable, and not automatically applied.
6. Do not paste keys or raw provider responses into repository files.

## Known Limits

- The background runner is process-local and not a durable queue.
- Re-analysis failure preserves previous suggestions, but users must inspect the failed task state
  to understand that the latest attempt failed.
- No automatic image compression is implemented; images over the configured analysis size limit are
  rejected before being read into memory.
- Actual provider/model capability depends on the configured OpenAI model and account access.
