# Sprint 18: Director Engine v1

Sprint 18 adds a deterministic Director Engine layer on top of the existing Prompt / Context Builder.

The goal is to convert the current shot context, character bindings, scene context, and a simple action summary into a clearer director structure and stronger prompt drafts.

This sprint does not use an LLM, does not call OpenAI, does not trigger ComfyUI, does not create generation runs, and does not add a database migration.

## Scope

- Director Context schema in the prompt-draft response.
- 12 built-in shot templates.
- Deterministic template matching from shot text.
- Template-aware prompt composition.
- Temporary director overrides in the Prompt Draft UI.
- Director Context preview in the shot workbench.

## Built-In Templates

- `enter_room_shock`: 闯入震惊
- `door_open_reveal`: 开门揭示
- `character_walks_forward`: 人物逼近
- `character_turns_head`: 人物转头
- `emotional_closeup`: 情绪特写
- `two_person_confrontation`: 双人对峙
- `phone_reveal`: 手机信息揭示
- `meeting_room_wide`: 会议室全景
- `authority_stands_up`: 权威人物起身
- `crowd_reaction`: 群众反应
- `character_leaves`: 人物离场
- `establishing_scene`: 场景建立镜头

Templates are code constants in the backend. They are not stored in the database and are not editable in this sprint.

## Matching Rules

Template recommendation is deterministic and keyword-based. Matching checks fields in this order:

1. `Shot.action_summary`
2. `Shot.visual_description`
3. `Shot.story_description`
4. `Shot.name`

The recommended template is returned as `recommended_template_id`. If the user selects a template, it is returned as `applied_template_id` and takes priority over the recommendation.

## Prompt Composition

The composer uses a fixed order:

1. Subject
2. Identity and look
3. Screen position
4. First-frame or end-frame action
5. Expression
6. Crowd reaction
7. Scene
8. Camera scale, angle, and composition
9. Lighting
10. Style
11. Continuity constraints

Quality terms may appear at the end, but they do not replace the director structure.

## Temporary Overrides

Prompt Draft requests may include `director_overrides`:

- `subject_position`
- `start_action`
- `end_action`
- `crowd_action`
- `crowd_emotion`
- `camera_movement`
- `composition`
- `environment_motion`

These overrides only affect the current prompt draft. They are not saved to the shot and do not start generation.

## Compatibility

Existing Prompt Draft fields remain available:

- `context_summary_zh`
- `first_frame_prompt_en`
- `end_frame_prompt_en`
- `motion_prompt_en`
- `negative_prompt_en`
- `camera_motion`
- `warnings`
- `source_shot_updated_at`
- `applied_style`

Task draft creation continues to use the same prompt fields. The Director Engine does not change keyframe, video, runner, provider, manifest, or workflow behavior.

## Warnings

Director warnings are advisory only. They do not block prompt generation, task draft creation, or manual generation flows.

Examples:

- `NO_PRIMARY_SUBJECT`
- `SUBJECT_POSITION_MISSING`
- `START_ACTION_MISSING`
- `END_ACTION_MISSING`
- `CROWD_REACTION_MISSING`
- `SCENE_MISSING`
- `CAMERA_COMPOSITION_MISSING`
- `POSE_CONTROL_RECOMMENDED`
- `SCENE_LAYOUT_CONFLICT_RISK`

## Deferred

- Workflow Router
- Template persistence
- User template editor
- LLM Director
- Multi-shot Director Context
- Pose-control workflow routing
