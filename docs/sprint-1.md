# Sprint 1: Project System

## Goal

Sprint 1 implements the real project system: SQLite-backed project CRUD, project list and detail pages, Chinese-first user copy, and Alembic-managed schema changes.

Out of scope: characters, scenes, props, shots, uploads, AI generation, ComfyUI, login, cloud services, task queues, infinite canvas, and 3D director tools.

## Chinese-First Product Rules

The default interface language is Simplified Chinese. User-visible labels, form errors, empty states, confirmations, loading states, and request errors are centralized in `apps/web/src/locales/zh-CN.ts`. `en-US.ts` is only a lightweight future placeholder.

## Data Model

`projects` contains:

- `id`: backend-generated UUID string.
- `name`: required, trimmed, 1-100 characters.
- `description`: nullable, max 1000 characters.
- `aspect_ratio`: one of `9:16`, `16:9`, `1:1`, `4:3`.
- `default_style`: nullable, max 200 characters.
- `default_language`: `zh-CN` or `en-US`, default `zh-CN`.
- `default_fps`: one of `24`, `25`, `30`, default `24`.
- `cover_image_path`: nullable, output only for this sprint.
- `created_at` and `updated_at`: timezone-aware UTC timestamps.

## API

- `GET /api/projects`
- `POST /api/projects`
- `GET /api/projects/{project_id}`
- `PATCH /api/projects/{project_id}`
- `DELETE /api/projects/{project_id}`

List responses use `{ "items": [], "total": 0 }` for future pagination expansion.

## Frontend Pages

- `/projects`: project list, empty state, create/edit/delete.
- `/projects/:projectId`: real project detail data and a placeholder for future workbench modules.

No fake project data or fake statistics are shown.

## Alembic

Run migrations from `apps/api`:

```powershell
alembic upgrade head
```

The API startup path does not call `create_all`.

## Tests

Backend:

```powershell
pytest
ruff check .
```

Frontend:

```powershell
npm run typecheck
npm run test
npm audit
```

## Known Limits

This sprint does not implement cover image upload, asset directories, generated media, or project workbench modules beyond the detail placeholder.

## Next Step

Sprint 2 can add the first asset domain, likely the character library, reusing the project-owned data structure and Chinese-first UI patterns established here.
