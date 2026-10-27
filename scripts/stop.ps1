$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$statePath = Join-Path $projectRoot '.local\processes.json'
if (-not (Test-Path -LiteralPath $statePath)) { Write-Host 'No managed development processes recorded.'; return }
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
function Stop-ManagedTree([int] $managedId) {
    # Windows virtualenv launchers may have a separate interpreter child.
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $managedId" -ErrorAction SilentlyContinue)
    foreach ($child in $children) { Stop-ManagedTree -managedId $child.ProcessId }
    Stop-Process -Id $managedId -ErrorAction SilentlyContinue
}
foreach ($processId in @($state.backend,$state.frontend)) {
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    if ($processInfo -and ($processInfo.ExecutablePath.StartsWith($projectRoot, [System.StringComparison]::OrdinalIgnoreCase) -or $processInfo.CommandLine.Contains($projectRoot))) {
        Stop-ManagedTree -managedId $processId
    }
}
Remove-Item -LiteralPath $statePath
Write-Host 'Managed development processes stopped.'
