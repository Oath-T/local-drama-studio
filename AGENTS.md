# Local Drama Studio Engineering Guide

## Product Goal

Local Drama Studio is a locally running AI short-drama production platform. The current focus is project, character, scene, prop, and shot asset management. Keyframe generation, ComfyUI integration, and video generation come later.

Do not implement Agents, a 3D director stage, infinite canvas, login, multi-user features, or cloud services unless explicitly requested.

## Project Structure

- `apps/web`: React frontend.
- `apps/api`: FastAPI backend.
- `storage`: local assets and generated results.
- `docs`: product and technical documentation.
- `scripts`: development and maintenance scripts.

Do not casually change these top-level directories.

## Backend Rules

- Python code must use type annotations.
- Use FastAPI, Pydantic, SQLAlchemy 2.x, and Alembic.
- Organize backend code by `api`, `domain`, `service`, `repository`, and `infrastructure`.
- Route handlers must not contain complex database logic.
- Database schema changes must use Alembic migrations.
- Keep API responses and error responses consistent.
- Do not hard-code Windows drive letters or user directories.

## Frontend Rules

- Use React with TypeScript strict mode.
- Use a feature-oriented directory structure.
- Use TanStack Query for server data.
- Use React Hook Form and Zod for forms.
- Use Zustand only for necessary temporary client state.
- Do not use large hard-coded mock datasets to pretend unfinished features are complete.
- Unimplemented features must show a clear Empty State.

## Development Workflow

- At the start of each task, read `README.md`, `AGENTS.md`, and relevant docs.
- Inspect existing code before proposing an implementation plan.
- Do not delete, replace, or refactor unrelated functionality.
- Complete only the current sprint scope.
- After changes, run formatting, type checks, and tests when available.
- Report architecture concerns before doing broad refactors.

## Testing And Quality

- New backend features must include pytest coverage.
- New frontend critical interactions must include Vitest coverage.
- Do not fake success by deleting tests, weakening validation, or skipping errors.
- Report all failures with their real cause.
- Delivery notes must list commands run and results.

## Security And Configuration

- Secrets, model endpoints, disk paths, and service URLs must be managed through environment variables or config files.
- Do not commit `.env`, database files, uploaded assets, or generated results.
- File uploads must validate extension, MIME type, and size when implemented.
- Do not run unknown scripts or install unrelated dependencies.

## Definition Of Done

A task is complete only when:

- The feature runs for real.
- Type checks pass.
- Relevant tests pass.
- `README.md` or relevant docs are updated.
- No fake data is used to hide unfinished functionality.
- Known limits and next steps are clearly stated.
