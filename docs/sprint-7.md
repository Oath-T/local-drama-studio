# Sprint 7: Keyframe Generation Task Foundation

Sprint 7 adds the data model, API, and workbench UI for keyframe generation tasks. It prepares shot snapshots, prompts, generation parameters, and task-level reference bindings.

This sprint does not generate images, call ComfyUI, call any model, create a background queue, or write generated outputs.

## Scope

- `KeyframeGenerationTask` stores one shot snapshot, prompt fields, model parameter placeholders, and status.
- `KeyframeGenerationTaskReference` stores the task's selected character and scene references.
- Task references can only be created from references already bound to the current shot.
- The frontend adds a `关键帧任务` tab inside the shot workbench reference panel.
- Task readiness is calculated dynamically and is not persisted.

## Status Model

The only persisted task statuses in Sprint 7 are:

- `draft`
- `ready`

Future execution statuses such as queued, running, succeeded, failed, or canceled are intentionally documented only and are not accepted by the database or API in this sprint.

## Shot Snapshot

`shot_snapshot` is stored as validated JSON with:

```json
{
  "schema_version": 1
}
```

The snapshot uses explicit Pydantic schemas. It is not an unvalidated arbitrary JSON blob.

If the source shot changes after task creation, task reads show `shot_changed_since_snapshot` and the corresponding readiness warning. The snapshot is not silently overwritten.

## Readiness Rules

Readiness is calculated by `KeyframeTaskReadinessService`.

Blocking issues include missing task name, missing prompt, invalid dimensions, aspect ratio mismatch, missing primary character references, missing scene references for a selected scene state, and unavailable media.

Warnings include missing English prompt, missing negative prompt, no model selected, changed source shot, no identity reference, no spatial reference, no seed, and missing secondary character references.

Primary shot characters require a matching task character reference by `source_shot_character_id`. Secondary missing references are warnings only. A shot with no characters has no character-reference requirement.

Scene references are required only when the snapshot has a `scene_state_id`, and the task reference must match that state.

## Media Ownership

Task references keep `media_asset_id`. If the original character or scene reference is deleted, the task reference keeps the media and the source reference FK is set to `NULL`; the UI shows that the source reference was deleted.

Direct media deletion while media is task-referenced should be blocked by the database FK strategy. The current product has no direct media delete API. Orphan media retained for task history is a known limitation for a future cleanup/maintenance task.

Deleting a keyframe task deletes only the task and task reference rows. It does not delete shots, source asset references, media records, or files.

## Parameters

- Width and height: 256-4096 and multiples of 8.
- Preset `9:16` uses the product-approved default `768x1360`.
- Aspect ratio mismatch can be saved, but blocks readiness.
- Seed: `null` means random, `0` is a valid fixed seed.
- Steps: 1-150.
- Guidance scale: 0-30.
- Output count: 1-8.

## Prompt Template

The default Chinese prompt is deterministic and rule-based. It uses ordered shot, scene, and character fields and ignores empty or unknown values.

No AI model is used to create prompts in Sprint 7.

## Known Limits

- No generation queue or execution state exists yet.
- No generated image output table exists yet.
- Task snapshot refresh is manual; creating a new task is the current way to capture a fresh snapshot.
- Task-retained orphan media is not automatically cleaned.
- Readiness uses current media availability checks, so missing local files can block readiness even when database rows remain.
