# Sprint 19-20: Production Pipeline v1

## Scope

This milestone connects the existing shot, Prompt Builder, keyframe task, video task, and selected-output features into a readable production pipeline.

It does not add model capabilities, ComfyUI workflow changes, automatic generation, batch generation, LLM calls, or auto-adoption.

## Keyframe Task Purpose

Keyframe tasks now have a structured `purpose`:

- `first_frame`: first-frame candidate task.
- `end_frame`: end-frame candidate task.
- `concept`: concept or exploration image task.
- `reference`: reference-support task.

Historical tasks are backfilled by strict name prefixes during migration:

- `首帧草稿%` becomes `first_frame`.
- `尾帧草稿%` becomes `end_frame`.
- All others become `concept`.

New tasks created from Prompt Draft write the purpose explicitly and no longer rely on name parsing.

## Production Status APIs

The new read-only APIs are:

```text
GET /api/projects/{project_id}/shots/{shot_id}/production-status
GET /api/projects/{project_id}/production-status
```

They aggregate existing records only:

- shot asset readiness
- Director Engine template availability
- first-frame and end-frame task/output adoption
- video task/input/output adoption
- continuity candidate from the previous shot
- next recommended manual actions

These APIs do not create, update, delete, mark ready, start runs, select outputs, or modify media.

## Shot Production Panel

The shot workbench shows six steps:

1. 资产准备
2. 导演 Prompt
3. 首帧
4. 尾帧
5. 视频
6. 最终采用

Buttons only navigate to existing UI areas or create an editable video draft. They do not mark tasks ready, start ComfyUI, or adopt outputs automatically.

## Video Task Creation From Adopted Frames

When creating a video task from Prompt Draft or the production panel, the frontend checks the production status for adopted first-frame and end-frame outputs.

If adopted outputs exist, the user is asked whether to fill them into the new video task. Rejecting the confirmation keeps the video task as a normal draft without inputs.

Only selected/adopted keyframe outputs are used. Unselected completed outputs are not treated as production inputs.

## Project Production Board

The project route `/projects/{project_id}/production` displays a read-only production board with per-shot status, blockers, first/end frame adoption, video status, and shot navigation.

The board is an overview surface only. Generation still happens through the existing shot workbench task panels.

## Known Limits

- Prompt Draft generated state is still frontend session state and is not persisted.
- Production status is computed on read and may not change `Shot.updated_at` when external task/output state changes.
- Continuity candidates are informational only and are not automatically applied.
- The board is not a batch control surface.
