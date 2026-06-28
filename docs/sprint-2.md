# Sprint 2: Character Assets

## Goal

Sprint 2 implements the first real asset domain for Local Drama Studio: project-owned characters, character looks, reference image upload, thumbnails, and structured reference metadata.

Out of scope: AI model calls, ComfyUI, video generation, background jobs, AI analysis buttons, fake AI suggestions, scenes, props, shots, login, cloud services, infinite canvas, and 3D director tools.

## Data Model

Character records belong to a project and store identity-oriented metadata:

- `name`, `aliases`, `role_type`
- `description`, `appearance_description`, `personality_description`
- `prompt_identity`, `notes`
- timezone-aware UTC `created_at` and `updated_at`

Character looks belong to a character and store appearance variants:

- `name`
- `description`, `costume_description`, `hair_description`, `makeup_description`
- `condition_description`, `prompt_appearance`
- `is_default`

Reference images belong to a character look and are linked to media assets:

- official metadata: `shot_type`, `view_angle`, `expression`, `pose_type`
- optional custom expression/pose fields
- `tags`, `description`, `notes`
- `is_primary`, `is_identity_anchor`
- future analysis fields: `analysis_status`, `suggestion_review_status`, `analysis_suggestions`

Media assets store file metadata and relative storage paths only. Absolute machine paths are not returned by the API.

## Upload Rules

Reference image upload accepts JPG, PNG, and WEBP files. The backend validates extension, MIME type, image decodeability, and configured size limit before storing files.

Environment settings:

- `LDS_API_STORAGE_DIR`
- `LDS_API_MAX_IMAGE_UPLOAD_MB`
- `LDS_API_THUMBNAIL_MAX_SIZE`

Physical media paths are intentionally short for Windows compatibility. Domain relationships are represented by database foreign keys rather than deep filesystem nesting.

## API

Character API:

```text
GET    /api/projects/{project_id}/characters
POST   /api/projects/{project_id}/characters
GET    /api/projects/{project_id}/characters/{character_id}
PATCH  /api/projects/{project_id}/characters/{character_id}
DELETE /api/projects/{project_id}/characters/{character_id}
```

Look API:

```text
GET    /api/projects/{project_id}/characters/{character_id}/looks
POST   /api/projects/{project_id}/characters/{character_id}/looks
GET    /api/projects/{project_id}/characters/{character_id}/looks/{look_id}
PATCH  /api/projects/{project_id}/characters/{character_id}/looks/{look_id}
POST   /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/set-default
DELETE /api/projects/{project_id}/characters/{character_id}/looks/{look_id}
```

Reference image API:

```text
GET    /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references
POST   /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references
GET    /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}
PATCH  /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}
POST   /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}/set-primary
DELETE /api/projects/{project_id}/characters/{character_id}/looks/{look_id}/references/{reference_id}
```

Media serving API:

```text
GET /api/media/{media_asset_id}/thumbnail
GET /api/media/{media_asset_id}/content
```

## Future Vision Analysis Adapter

Reference images reserve a future integration point for external or local multimodal vision models. No provider is hard-coded into character, look, reference, or media domain models.

Reserved analysis task status:

- `not_analyzed`
- `pending`
- `completed`
- `failed`

Reserved suggestion review status:

- `not_reviewed`
- `accepted`
- `edited_and_accepted`
- `rejected`

`analysis_suggestions` is stored as JSON but must be validated through a Pydantic schema before write or read. The schema currently reserves:

- `shot_type`
- `view_angle`
- `expression`
- `pose_type`
- `tags`
- `description`
- `quality_notes`
- `identity_anchor_recommended`

Future flow:

1. A `VisionAnalysisProvider` interface can connect cloud or local vision models.
2. Analysis output is saved only as suggestions.
3. The UI presents suggestions for review.
4. Service-layer confirmation validates suggestions, writes user-approved values into official metadata, and updates `suggestion_review_status`.
5. Normal PATCH endpoints must not implicitly copy suggestions into official metadata.

This sprint does not implement the provider, a start-analysis endpoint, background jobs, fake suggestions, or an AI analysis button. When `analysis_suggestions` is empty, the frontend does not render an empty AI suggestion panel.

## Tests

Backend:

```powershell
ruff check .
pytest
```

Frontend:

```powershell
npm run typecheck
npm run test
```

## Known Limits

- Character asset management now covers create, edit, delete, default look, primary reference, identity anchor, metadata editing, and original-image preview.
- Local file deletion is intentionally not atomic with SQLite transactions. The backend deletes database records first, then safely cleans files inside `STORAGE_ROOT`; missing files count as already cleaned, and cleanup failures are logged without exposing paths. A future maintenance task should handle orphan-file scanning and cleanup.
- Visual analysis is only represented by reserved status fields and schemas.
- Scenes, props, shots, and generation tasks remain empty-state surfaces.
