$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$apiPath = Join-Path $root "apps\api"
$webPath = Join-Path $root "apps\web"
$alembicPath = Join-Path $apiPath ".venv\Scripts\alembic.exe"
$pythonPath = Join-Path $apiPath ".venv\Scripts\python.exe"
$npmPath = (Get-Command npm.cmd -ErrorAction Stop).Source

if (-not (Test-Path $alembicPath)) {
  throw "Alembic executable was not found: $alembicPath. Install API dependencies first."
}

Push-Location $apiPath
try {
  & $alembicPath upgrade head
  if ($LASTEXITCODE -ne 0) {
    throw "Database migration failed. Development servers were not started."
  }
}
finally {
  Pop-Location
}

Start-Process -FilePath $pythonPath -WorkingDirectory $apiPath -WindowStyle Hidden -ArgumentList @(
  "-m",
  "uvicorn",
  "app.main:app",
  "--reload",
  "--host",
  "127.0.0.1",
  "--port",
  "8000"
)

Start-Process -FilePath $npmPath -WorkingDirectory $webPath -WindowStyle Hidden -ArgumentList @(
  "run",
  "dev"
)
