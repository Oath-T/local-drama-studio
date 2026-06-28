# Sprint 4: Shot Workbench

Sprint 4 adds project-scoped shot management and reference binding. It does not implement AI analysis, generation, ComfyUI, props, drag-and-drop sorting, infinite canvas, batch upload, 3D direction, or cross-project media reuse.

## Scope

- Shot create, edit, delete, duplicate, and up/down ordering.
- ShotCharacter binding, edit, delete, and up/down ordering.
- ShotReference binding, delete, and up/down ordering for character and scene references.
- Three-column frontend workbench: shot list, shot detail, and reference binding panel.
- Readiness calculation from current relationships.
- Scene/state switch cleanup for incompatible scene reference bindings.
- Backend and frontend tests, including character and scene regression coverage.

## API

Shot routes are project scoped:

```text
GET    /api/projects/{project_id}/shots
POST   /api/projects/{project_id}/shots
GET    /api/projects/{project_id}/shots/{shot_id}
PATCH  /api/projects/{project_id}/shots/{shot_id}
DELETE /api/projects/{project_id}/shots/{shot_id}
POST   /api/projects/{project_id}/shots/{shot_id}/move
POST   /api/projects/{project_id}/shots/{shot_id}/duplicate

GET    /api/projects/{project_id}/shots/{shot_id}/characters
POST   /api/projects/{project_id}/shots/{shot_id}/characters
PATCH  /api/projects/{project_id}/shots/{shot_id}/characters/{shot_character_id}
DELETE /api/projects/{project_id}/shots/{shot_id}/characters/{shot_character_id}
POST   /api/projects/{project_id}/shots/{shot_id}/characters/{shot_character_id}/move

GET    /api/projects/{project_id}/shots/{shot_id}/references
POST   /api/projects/{project_id}/shots/{shot_id}/references
DELETE /api/projects/{project_id}/shots/{shot_id}/references/{shot_reference_id}
POST   /api/projects/{project_id}/shots/{shot_id}/references/{shot_reference_id}/move
```

Move requests use:

```json
{
  "order_index": 1
}
```

`order_index` is 1-based. The backend clamps out-of-range values, compacts order after deletion, and returns the final state from the database. Concurrent move requests use last committed result; the frontend refetches after success.

## Data Rules

- `readiness_status` and `missing_items` are not stored. They are calculated on each read.
- Shot list summaries use aggregate queries for counts plus batched scene/state lookups instead of loading each shot's full child graph.
- Duplicating a shot runs in one database transaction and copies only shot rows, ShotCharacter rows, and ShotReference bindings. It references existing character, scene, and media assets.
- Changing or clearing scene/state removes only incompatible scene reference bindings. Character bindings and character references are not removed.
- A character reference whose look differs from `ShotCharacter.look_id` is allowed. The UI shows a non-blocking warning.
- Deleting a ShotCharacter cascades ShotReferences explicitly tied to that ShotCharacter. CharacterReference and MediaAsset records are not deleted.

## Database Constraints

The Sprint 4 migration adds shot tables and foreign keys for core consistency:

- `Character` deletion cascades ShotCharacter rows.
- `CharacterLook` deletion sets `ShotCharacter.look_id` to null.
- `CharacterReference` deletion cascades ShotReference rows.
- `Scene` deletion clears `Shot.scene_id` and `Shot.scene_state_id`.
- `SceneState` deletion clears `Shot.scene_state_id`.
- `SceneReference` deletion cascades ShotReference rows.
- `Shot` deletion cascades ShotCharacter and ShotReference rows.

SQLite foreign keys are enabled when connections are opened by the application.

## Duplicate Reference Guard

The same source reference can be bound more than once when the purpose differs. The forbidden duplicate combination is:

```text
shot_id
+ reference_type
+ actual reference id
+ purpose
+ shot_character_id
```

Sprint 4 uses Service-layer lookup, supporting indexes, and safe database-exception handling. Known limitation: two highly concurrent requests can pass the Service lookup before either commits; the API still returns a safe error if the database rejects the write, but this sprint does not add triggers or a more complex locking scheme.

## Timestamp Note

Shot readiness is derived from live relationships. Deleting external character, look, character reference, scene, state, or scene reference records makes the next shot read return the correct readiness. Those external asset changes do not necessarily update `Shot.updated_at`; a future lightweight maintenance/event strategy can revisit this if sorting by asset-impact time becomes important.
