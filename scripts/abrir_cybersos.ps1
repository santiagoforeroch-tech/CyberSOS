param([switch]$SkipBrowser)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$backendRoot = Join-Path $projectRoot "backend"
$frontendRoot = Join-Path $projectRoot "frontend"
$pythonPath = Join-Path $backendRoot ".venv\Scripts\python.exe"
$vitePath = Join-Path $frontendRoot "node_modules\vite\bin\vite.js"
$runtimeRoot = Join-Path $projectRoot ".runtime"
$statePath = Join-Path $runtimeRoot "processes.json"
$initDbPath = Join-Path $backendRoot "scripts\init_dev_db.py"
$apiPort = 8001
$frontendPort = 4174
$localDatabaseUrl = "sqlite:///" + ((Join-Path $backendRoot "cybersos-dev.db") -replace "\\", "/")

function Find-NodeExecutable {
    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($nodeCommand) { return $nodeCommand.Source }

    $bundledNode = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
    if (Test-Path -LiteralPath $bundledNode) { return $bundledNode }

    throw "No se encontró Node.js. Abre el proyecto con Codex para reparar las dependencias."
}

function Test-LocalUrl([string]$url) {
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch {
        return $false
    }
}

function Test-LocalDevelopmentApi {
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:$apiPort/api/health" -TimeoutSec 2
        return $response.status -eq "ok" -and $response.database -eq "sqlite"
    } catch {
        return $false
    }
}

function Get-RegisteredProcess([string]$name) {
    if (-not (Test-Path -LiteralPath $statePath)) { return $null }
    try {
        $entry = @(Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json | Where-Object { $_.Name -eq $name }) | Select-Object -First 1
        if (-not $entry) { return $null }
        $process = Get-Process -Id $entry.Id -ErrorAction SilentlyContinue
        if ($process -and $process.Path -eq $entry.Executable) { return [pscustomobject]@{ Entry = $entry; Process = $process } }
    } catch { }
    return $null
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Falta el entorno Python del backend."
}
if (-not (Test-Path -LiteralPath $vitePath)) {
    throw "Faltan las dependencias del frontend."
}

$nodePath = Find-NodeExecutable
New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
$startedProcesses = @()
$activeProcesses = @()
$previousDatabaseUrl = $env:DATABASE_URL
$previousViteApiUrl = $env:VITE_API_URL

try {
    # El acceso de doble clic siempre funciona con datos ficticios locales. El despliegue
    # conserva DATABASE_URL en las variables del servidor y usa Supabase normalmente.
    $env:DATABASE_URL = $localDatabaseUrl
    # Evita conectar el frontend a otra aplicación que use el puerto 8000.
    $env:VITE_API_URL = "http://127.0.0.1:$apiPort/api"

    # Para SQLite local, crea las tablas de desarrollo antes de iniciar FastAPI.
    & $pythonPath $initDbPath | Out-Null

    $apiRegistration = Get-RegisteredProcess "api"
    if ((Test-LocalUrl "http://127.0.0.1:$apiPort/api/health") -and -not (Test-LocalDevelopmentApi)) {
        if (-not $apiRegistration) {
            throw "El puerto 8000 está ocupado por otra API. Ciérrala antes de iniciar CyberSOS."
        }
        Stop-Process -Id $apiRegistration.Process.Id
        Start-Sleep -Milliseconds 500
    }

    if (-not (Test-LocalDevelopmentApi)) {
        $apiProcess = Start-Process -FilePath $pythonPath -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$apiPort") -WorkingDirectory $backendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeRoot "api.out.log") -RedirectStandardError (Join-Path $runtimeRoot "api.err.log") -PassThru
        $startedProcesses += [pscustomobject]@{ Name = "api"; Id = $apiProcess.Id; Executable = $pythonPath }
        $activeProcesses += $startedProcesses[-1]
    } elseif ($apiRegistration) {
        $activeProcesses += $apiRegistration.Entry
    }

    $frontendRegistration = Get-RegisteredProcess "frontend"
    if (-not (Test-LocalUrl "http://127.0.0.1:$frontendPort/")) {
        $frontendProcess = Start-Process -FilePath $nodePath -ArgumentList @("`"$vitePath`"", "--host", "127.0.0.1", "--port", "$frontendPort") -WorkingDirectory $frontendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeRoot "frontend.out.log") -RedirectStandardError (Join-Path $runtimeRoot "frontend.err.log") -PassThru
        $startedProcesses += [pscustomobject]@{ Name = "frontend"; Id = $frontendProcess.Id; Executable = $nodePath }
        $activeProcesses += $startedProcesses[-1]
    } elseif ($frontendRegistration) {
        $activeProcesses += $frontendRegistration.Entry
    }

    ConvertTo-Json -InputObject $activeProcesses | Set-Content -LiteralPath $statePath -Encoding UTF8
    $deadline = (Get-Date).AddSeconds(30)
    do {
        $apiReady = Test-LocalDevelopmentApi
        $frontendReady = Test-LocalUrl "http://127.0.0.1:$frontendPort/"
        if ($apiReady -and $frontendReady) { break }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)

    if (-not ($apiReady -and $frontendReady)) {
        throw "CyberSOS no inició a tiempo. Revisa los archivos de .runtime."
    }

    if (-not $SkipBrowser) {
        Start-Process "http://localhost:$frontendPort/"
    }

    Write-Host "CyberSOS está disponible en http://localhost:$frontendPort/"
} finally {
    if ($null -eq $previousDatabaseUrl) { Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue } else { $env:DATABASE_URL = $previousDatabaseUrl }
    if ($null -eq $previousViteApiUrl) { Remove-Item Env:VITE_API_URL -ErrorAction SilentlyContinue } else { $env:VITE_API_URL = $previousViteApiUrl }
}
