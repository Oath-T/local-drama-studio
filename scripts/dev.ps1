$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$apiPath = Join-Path $root "apps\api"
$webPath = Join-Path $root "apps\web"

Start-Process powershell -WindowStyle Normal -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd `"$apiPath`"; if (Test-Path .\.venv\Scripts\Activate.ps1) { . .\.venv\Scripts\Activate.ps1 }; python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
)

Start-Process powershell -WindowStyle Normal -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd `"$webPath`"; npm run dev"
)
