$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$vitePath = Join-Path $projectRoot 'frontend\node_modules\vite\bin\vite.js'
$logRoot = Join-Path $projectRoot '.local'
if (-not (Test-Path -LiteralPath $pythonPath) -or -not (Test-Path -LiteralPath $vitePath)) { throw 'Run .\scripts\setup.ps1 first.' }
if ((Get-NetTCPConnection -State Listen -LocalPort 8000,5173 -ErrorAction SilentlyContinue)) { throw 'Port 8000 or 5173 is already in use. The app may already be running at http://127.0.0.1:5173.' }
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$backendProcess = Start-Process -WindowStyle Hidden -FilePath $pythonPath -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000','--no-access-log') -WorkingDirectory (Join-Path $projectRoot 'backend') -RedirectStandardOutput (Join-Path $logRoot 'backend.out.log') -RedirectStandardError (Join-Path $logRoot 'backend.err.log') -PassThru
try {
    $frontendProcess = Start-Process -WindowStyle Hidden -FilePath (Get-Command node).Source -ArgumentList @(('"' + $vitePath + '"'),'--host','127.0.0.1','--port','5173') -WorkingDirectory (Join-Path $projectRoot 'frontend') -RedirectStandardOutput (Join-Path $logRoot 'frontend.out.log') -RedirectStandardError (Join-Path $logRoot 'frontend.err.log') -PassThru
} catch {
    Stop-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue
    throw
}
@{backend=$backendProcess.Id;frontend=$frontendProcess.Id} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logRoot 'processes.json')
Write-Host 'ScamShield AI: http://127.0.0.1:5173'
Write-Host 'API docs: http://127.0.0.1:8000/docs'
Write-Host 'Logs are in .local. Run .\scripts\stop.ps1 to stop these processes.'
