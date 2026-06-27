# Local Drama Studio

Local Drama Studio is a local-first AI short-drama production platform. Sprint 0 establishes the project foundation only: a FastAPI backend, a React workbench frontend, local SQLite configuration, Alembic setup, tests, and development documentation.

This sprint does not implement AI Agents, image generation, video generation, ComfyUI calls, login, cloud services, upload flows, infinite canvas, or a 3D director stage.

## Structure

```text
local-drama-studio/
├── apps/
│   ├── web/
│   └── api/
├── storage/
├── scripts/
├── docs/
├── .env.example
├── .gitignore
├── README.md
└── docker-compose.yml
```

## Prerequisites

- Node.js 20+
- Python 3.11+

On Windows, the Python launcher command `py -3.11` or newer can be used when `python` is not on PATH.

## One Command Development Start

From the repository root:

```powershell
.\scripts\dev.ps1
```

The script starts the API and web dev servers in separate PowerShell windows.

## Backend

```powershell
cd apps\api
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health endpoint:

```text
GET http://127.0.0.1:8000/api/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "local-drama-studio-api"
}
```

## Frontend

```powershell
cd apps\web
npm install
npm run dev
```

Open `http://localhost:5173`.

## Alembic

From `apps/api`:

```powershell
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Sprint 0 has no domain tables yet, but Alembic is configured for future schema changes.

## Tests

Backend:

```powershell
cd apps\api
pytest
```

Frontend:

```powershell
cd apps\web
npm run typecheck
npm run test
```

## Configuration

Copy `.env.example` to `.env` when local overrides are needed. Do not commit `.env`, database files, uploaded assets, or generated output.
