# Sprint 13.1: Prompt Builder Quality Enhancement

Sprint 13.1 improves the rule-based Prompt / Context Builder without adding model calls,
database fields, ComfyUI changes, workflow changes, or automatic generation.

## Scope

- Add one-time prompt draft overrides for start action, end action, motion direction,
  camera motion, visual style, and mood.
- Add fixed style presets:
  - `cinematic_short_drama`
  - `ultra_realistic`
  - `rain_night_neon`
  - `office_drama`
  - `emotional_closeup`
  - `action_tension`
- Keep all overrides request-scoped. They are not persisted and do not modify shots,
  tasks, runs, outputs, assets, or workflows.
- Add separate keyframe fill actions for first-frame and end-frame prompt drafts.

## API Behavior

`POST /api/projects/{project_id}/shots/{shot_id}/prompt-draft` accepts an optional
`overrides` object:

```json
{
  "style": "rain_night_neon",
  "overrides": {
    "start_action": "character looks toward the door",
    "end_action": "character steps into the rain",
    "motion_direction": "move from hesitation to a decisive step",
    "camera_motion": "slow push-in with subtle handheld sway",
    "visual_style": "cold blue neon reflections",
    "mood": "suppressed anger becoming determination"
  }
}
```

The response includes `applied_style` so the frontend can display or test the effective
preset. The response still uses the shot `updated_at` as `source_shot_updated_at`;
there is no request-time timestamp.

## Prompt Rules

- `first_frame_prompt_en` prefers `start_action` when provided.
- `end_frame_prompt_en` prefers `end_action` and strengthens continuity language for
  same character, face, outfit, scene, and emotion transition.
- `motion_prompt_en` uses `motion_direction` and `camera_motion` when provided, and
  strengthens smooth transition, facial expression continuity, environmental motion,
  and anti-flicker / anti-jump-cut language.
- `camera_motion` resolves as: override, custom shot camera movement, enum label, default.
- `visual_style` and `mood` append prompt fragments. They do not replace asset context.

## Warnings

New advisory warning codes:

- `OVERRIDE_USED`
- `STYLE_PRESET_USED`

If `end_action` is provided, `WEAK_END_FRAME_SIGNAL` is suppressed for that response
because the user supplied an explicit end-frame signal.

Warnings remain advisory. They do not block saving, mark-ready, or generation.

## Frontend

The Prompt Draft card exposes generation settings for style preset and one-time
overrides. The keyframe task editor can fill either the first-frame prompt or the
end-frame prompt into the existing `prompt_en` field. Video tasks continue to fill:

- `prompt = motion_prompt_en`
- `negative_prompt = negative_prompt_en`
- `camera_motion = camera_motion`

All fills are local form actions. Users still manually save tasks.

## Non-Goals

Sprint 13.1 does not implement LLM calls, prompt persistence, prompt versioning,
automatic prompt optimization, automatic saving, automatic mark-ready, automatic
generation, new ComfyUI workflows, runner/provider changes, workflow JSON changes,
manifest changes, database migrations, subtitles, dubbing, music, or editing.
