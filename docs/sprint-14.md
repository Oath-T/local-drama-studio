# Sprint 14: Prompt Draft To Generation Task Draft

Sprint 14 lets users create real generation task drafts from a Prompt Draft.

## Scope

- Create a first-frame keyframe task draft from `first_frame_prompt_en`.
- Create an end-frame keyframe task draft from `end_frame_prompt_en`.
- Create a video task draft from `motion_prompt_en`.
- Reuse existing task APIs from the frontend.
- Keep Prompt Draft read-only and non-persistent.

## API Strategy

No new backend aggregation API is introduced in this sprint.

Keyframe task draft creation uses the existing two-step flow:

1. `POST /api/projects/{project_id}/shots/{shot_id}/keyframe-tasks`
   with `copy_current_references=true`.
2. `PATCH /api/projects/{project_id}/keyframe-tasks/{task_id}` to fill:
   - `prompt_zh = context_summary_zh`
   - `prompt_en = first_frame_prompt_en` or `end_frame_prompt_en`
   - `negative_prompt = negative_prompt_en`

Video task draft creation uses:

1. `POST /api/projects/{project_id}/shots/{shot_id}/video-tasks`
2. `PATCH /api/projects/{project_id}/video-tasks/{task_id}` to fill:
   - `name`
   - `prompt = motion_prompt_en`
   - `negative_prompt = negative_prompt_en`
   - `camera_motion = camera_motion`
   - `duration_seconds = shot.duration_seconds` only when the shot duration is greater than 0

## Reference Handling

First-frame and end-frame keyframe tasks copy the current shot-bound references through
the existing `copy_current_references=true` behavior. This copies `ShotReference`
bindings into `KeyframeTaskReference` records and does not bind raw character or scene
references directly.

Video task drafts do not copy character or scene references. They still use the existing
`start_frame` and `end_frame` inputs, which the user must choose manually.

## Failure Handling

The frontend uses create + patch as two separate API calls. This is intentionally not
treated as an atomic transaction in Sprint 14.

If create succeeds but patch fails, the task draft is kept and the UI shows:

```text
任务草稿已创建，但提示词填充失败，请在任务中手动检查。
```

The frontend does not automatically delete the created task because it may already have
copied references or other useful draft state.

## Non-Goals

Sprint 14 does not add database migrations, Prompt Draft persistence, Prompt versioning,
automatic mark-ready, automatic generation, automatic ComfyUI submission, automatic video
start/end frame selection, aggregation APIs, LLM calls, workflow changes, provider/runner
changes, subtitles, dubbing, or editing.
