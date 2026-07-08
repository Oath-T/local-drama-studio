# Sprint 13: Prompt / Context Builder v1

Sprint 13 adds a side-effect-free Prompt / Context Builder for shot work.

## Scope

- Generate editable prompt drafts from the current shot context.
- Use deterministic rule templates only.
- Return a Chinese context summary, English first-frame prompt, English end-frame prompt,
  English motion prompt, English negative prompt, camera motion text, and advisory warnings.
- Let the frontend fill existing keyframe and video task form fields.

## Data Sources

The builder reads existing project-scoped records:

- Shot description, visual description, action summary, mood, focal subject, camera fields, and scene binding.
- Shot characters, character identity prompt, look appearance prompt, costume, hair, makeup, and shot-level action/expression/position.
- Scene prompt environment, scene state prompt, time, weather, lighting, season, crowd, and environment condition.
- Shot reference bindings and official reference metadata.

It does not read local absolute paths, `relative_path`, `stored_filename`, media binary content, base64 data, or image pixels.

## API

```http
POST /api/projects/{project_id}/shots/{shot_id}/prompt-draft
```

The API is read-only. It does not create records, update tasks, trigger ComfyUI, call a runner, or call a model provider.

The response uses `source_shot_updated_at` from the shot instead of a request-time timestamp, so identical input remains testable and stable.

## Prompt Fields

- `context_summary_zh`: Chinese explanation of the current shot context.
- `first_frame_prompt_en`: English prompt for a keyframe or first video frame.
- `end_frame_prompt_en`: English prompt emphasizing same character, same outfit, same scene, and continuity.
- `motion_prompt_en`: English prompt for video motion.
- `negative_prompt_en`: Short default negative prompt.
- `camera_motion`: Conservative camera motion text derived from shot camera movement.

## Frontend Mapping

Keyframe task editor:

- `prompt_en = first_frame_prompt_en`
- `negative_prompt = negative_prompt_en`

Video task editor:

- `prompt = motion_prompt_en`
- `negative_prompt = negative_prompt_en`
- `camera_motion = camera_motion`

The frontend only fills form drafts. Users must manually save tasks. Existing prompt content requires confirmation before overwrite.

## Warnings

Warnings are advisory and never block saving, mark-ready, or generation.

Stable codes include:

- `NO_CHARACTERS`
- `CHARACTER_LOOK_MISSING`
- `CHARACTER_REFERENCE_MISSING`
- `IDENTITY_REFERENCE_MISSING`
- `SCENE_MISSING`
- `SCENE_STATE_MISSING`
- `SCENE_REFERENCE_MISSING`
- `SPATIAL_REFERENCE_MISSING`
- `SHOT_VISUAL_DESCRIPTION_MISSING`
- `SHOT_ACTION_MISSING`
- `WEAK_END_FRAME_SIGNAL`
- `NO_CAMERA_MOTION`

## Explicit Non-Goals

Sprint 13 does not implement LLM calls, OpenAI calls, local model calls, vision model calls, prompt persistence, prompt versioning, automatic task saving, automatic mark-ready, automatic generation, new ComfyUI workflows, runner/provider changes, workflow JSON changes, manifest changes, database migrations, subtitles, dubbing, music, editing, or automatic directing.

## Known Limits

- Existing keyframe tasks have one `prompt_en` field, so the first-frame prompt is filled into that field while the end-frame prompt remains a copyable draft.
- There are no dedicated shot start/end action fields yet, so end-frame prompts are conservative and derived from current shot description, action summary, mood, and focal subject.
- Rule templates are explainable and deterministic, but less expressive than a future provider-neutral prompt refinement model.
