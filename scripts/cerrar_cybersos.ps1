$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$runtimeRoot = Join-Path $projectRoot ".runtime"
$statePath = Join-Path $runtimeRoot "processes.json"

if (-not (Test-Path -LiteralPath $statePath)) {
    Write-Host "CyberSOS ya estaba detenido."
    exit 0
}

$entries = @(Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json)
foreach ($entry in $entries) {
    $process = Get-Process -Id $entry.Id -ErrorAction SilentlyContinue
    if (-not $process) { continue }
    try {
        if ($process.Path -eq $entry.Executable) {
            Stop-Process -Id $entry.Id
        }
    } catch {
        Write-Warning "No se pudo detener $($entry.Name)."
    }
}

Remove-Item -LiteralPath $statePath -Force
Write-Host "CyberSOS fue detenido correctamente."
