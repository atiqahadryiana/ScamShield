$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        & python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Unable to create Python environment.' }
    }
    & '.\.venv\Scripts\python.exe' -m pip install -r backend\requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Backend installation failed.' }
    Push-Location -LiteralPath (Join-Path $projectRoot 'backend')
    try {
        & '..\.venv\Scripts\python.exe' -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
        & '..\.venv\Scripts\python.exe' -m app.cli seed
        if ($LASTEXITCODE -ne 0) { throw 'Database initialization failed.' }
    } finally { Pop-Location }
    Push-Location -LiteralPath (Join-Path $projectRoot 'frontend')
    try {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed.' }
    } finally { Pop-Location }
    Write-Host 'Setup complete. Run .\scripts\dev.ps1 to start the application.'
} finally { Pop-Location }
