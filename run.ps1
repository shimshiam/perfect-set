<#
.SYNOPSIS
  Launch the Perfect Set backend and frontend in a single terminal.
.DESCRIPTION
  PowerShell equivalent of run.sh.  Activates the Python 3.12 venv,
  starts the FastAPI/Uvicorn backend, waits for the /health endpoint,
  then starts the Vite dev server.  Ctrl-C tears down both processes.
#>

$ErrorActionPreference = 'Stop'

# ── paths ──────────────────────────────────────────────────
$RootDir      = $PSScriptRoot
$AppDir       = Join-Path $RootDir 'health-form-tracker'
$BackendDir   = Join-Path $AppDir  'backend'
$FrontendDir  = Join-Path $AppDir  'frontend'

# Try repo-root venv first, then app-level venv
$VenvDir = Join-Path $RootDir '.venv'
if (-not (Test-Path (Join-Path $VenvDir 'Scripts\Activate.ps1'))) {
    $VenvDir = Join-Path $AppDir '.venv'
}

# ── configurable defaults ─────────────────────────────────
$BackendHost  = if ($env:BACKEND_HOST)  { $env:BACKEND_HOST }  else { '127.0.0.1' }
$BackendPort  = if ($env:BACKEND_PORT)  { [int]$env:BACKEND_PORT }  else { 8000 }
$FrontendHost = if ($env:FRONTEND_HOST) { $env:FRONTEND_HOST } else { '127.0.0.1' }
$FrontendPort = if ($env:FRONTEND_PORT) { [int]$env:FRONTEND_PORT } else { 5173 }
$BackendReload = $env:BACKEND_RELOAD -eq '1'

# ── helper functions ──────────────────────────────────────
function Test-PortInUse ([int]$Port) {
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $connections -and $connections.Count -gt 0
}

function Find-AvailablePort ([int]$Start) {
    $port = $Start
    while (Test-PortInUse $port) { $port++ }
    return $port
}

function Test-BackendHealthy ([int]$Port) {
    try {
        $r = Invoke-WebRequest -Uri "http://${BackendHost}:${Port}/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        return $r.StatusCode -eq 200
    } catch {
        return $false
    }
}

# ── pre-flight checks ────────────────────────────────────
$activateScript = Join-Path $VenvDir 'Scripts\Activate.ps1'
if (-not (Test-Path $activateScript)) {
    Write-Host "Missing virtual environment at $VenvDir" -ForegroundColor Red
    Write-Host "Create it first:  python3.12 -m venv $VenvDir" -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path (Join-Path $BackendDir 'server.py'))) {
    Write-Host "Missing backend server: $BackendDir\server.py" -ForegroundColor Red; exit 1
}
if (-not (Test-Path (Join-Path $FrontendDir 'package.json'))) {
    Write-Host "Missing frontend package.json: $FrontendDir\package.json" -ForegroundColor Red; exit 1
}
if (-not (Test-Path (Join-Path $FrontendDir 'node_modules'))) {
    Write-Host "Missing frontend dependencies. Run:  cd $FrontendDir; npm install" -ForegroundColor Red; exit 1
}

# ── activate venv ─────────────────────────────────────────
& $activateScript

# ── start backend ─────────────────────────────────────────
$startBackend = $true
if (Test-PortInUse $BackendPort) {
    if (Test-BackendHealthy $BackendPort) {
        $startBackend = $false
        Write-Host "Reusing backend at http://${BackendHost}:${BackendPort}" -ForegroundColor Cyan
    } else {
        $BackendPort = Find-AvailablePort ($BackendPort + 1)
    }
}

$backendJob = $null
if ($startBackend) {
    $reloadFlag = if ($BackendReload) { '--reload' } else { '' }
    $backendJob = Start-Process -NoNewWindow -PassThru -FilePath 'python' `
        -ArgumentList "-m uvicorn server:app --host $BackendHost --port $BackendPort $reloadFlag".Trim() `
        -WorkingDirectory $BackendDir
    Write-Host "Starting backend (PID $($backendJob.Id))..." -ForegroundColor DarkGray
}

# ── wait for backend health ───────────────────────────────
$attempts = 240
while (-not (Test-BackendHealthy $BackendPort)) {
    if ($backendJob -and $backendJob.HasExited) {
        Write-Host "Backend failed to start." -ForegroundColor Red; exit 1
    }
    $attempts--
    if ($attempts -le 0) {
        Write-Host "Backend did not become healthy at http://${BackendHost}:${BackendPort}/health" -ForegroundColor Red
        exit 1
    }
    Start-Sleep -Milliseconds 250
}
Write-Host "Backend healthy." -ForegroundColor Green

# ── find available frontend port ──────────────────────────
$FrontendPort = Find-AvailablePort $FrontendPort

# ── start frontend ────────────────────────────────────────
$env:VITE_WS_BASE_URL = "ws://${BackendHost}:${BackendPort}/ws"
$frontendJob = Start-Process -NoNewWindow -PassThru -FilePath 'npm' `
    -ArgumentList "run dev -- --host $FrontendHost --port $FrontendPort --strictPort" `
    -WorkingDirectory $FrontendDir

Write-Host ""
Write-Host "  Backend:  http://${BackendHost}:${BackendPort}"  -ForegroundColor Cyan
Write-Host "  Frontend: http://${FrontendHost}:${FrontendPort}" -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to stop both servers." -ForegroundColor DarkGray
Write-Host ""

# ── wait & cleanup on exit ────────────────────────────────
try {
    # Block until Ctrl+C
    while ($true) {
        if ($backendJob -and $backendJob.HasExited) {
            Write-Host "Backend exited unexpectedly." -ForegroundColor Red; break
        }
        if ($frontendJob.HasExited) {
            Write-Host "Frontend exited unexpectedly." -ForegroundColor Red; break
        }
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "`nShutting down..." -ForegroundColor Yellow
    if ($frontendJob -and -not $frontendJob.HasExited) {
        Stop-Process -Id $frontendJob.Id -Force -ErrorAction SilentlyContinue
        # Also kill any node children spawned by npm
        Get-Process -Name node -ErrorAction SilentlyContinue |
            Where-Object { $_.StartTime -ge $frontendJob.StartTime } |
            Stop-Process -Force -ErrorAction SilentlyContinue
    }
    if ($backendJob -and -not $backendJob.HasExited) {
        Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Done." -ForegroundColor Green
}
