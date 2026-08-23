[CmdletBinding()]
param(
    [ValidateSet("start", "check", "verify", "status", "demo", "stop", "restart", "reset")]
    [string]$Command = "start",
    [switch]$NoOpen,
    [switch]$NoBuild,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ExpectedServices = @("postgres", "redis", "backend", "worker", "frontend")
$HealthyServices = @("postgres", "redis", "backend", "frontend")

Set-Location -LiteralPath $ProjectRoot

function Write-Title([string]$Text) {
    Write-Host ""
    Write-Host "ARVA AI - $Text" -ForegroundColor Cyan
    Write-Host ("=" * (10 + $Text.Length)) -ForegroundColor DarkCyan
}

function Write-Step([string]$Text) {
    Write-Host "[ARVA] $Text" -ForegroundColor Cyan
}

function Fail([string]$Message) {
    throw $Message
}

function Require-Command([string]$Name, [string]$InstallHint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Fail "$Name is required. $InstallHint"
    }
}

function Test-DockerEngine {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & docker info *> $null
        return $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Invoke-External([string]$Description, [scriptblock]$Action) {
    Write-Step $Description
    & $Action
    if ($LASTEXITCODE -ne 0) {
        Fail "$Description failed with exit code $LASTEXITCODE."
    }
}

function Ensure-Docker {
    Require-Command "docker" "Install and start Docker Desktop, then run this command again."

    if (-not (Test-DockerEngine)) {
        Write-Step "Docker Desktop is not running; starting it now..."

        $dockerDesktopCandidates = @()
        if ($env:ProgramFiles) {
            $dockerDesktopCandidates += Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
        }
        if (${env:ProgramFiles(x86)}) {
            $dockerDesktopCandidates += Join-Path ${env:ProgramFiles(x86)} "Docker\Docker\Docker Desktop.exe"
        }
        if ($env:LOCALAPPDATA) {
            $dockerDesktopCandidates += Join-Path $env:LOCALAPPDATA "Docker\Docker Desktop.exe"
        }

        $dockerDesktop = $dockerDesktopCandidates |
            Where-Object { Test-Path -LiteralPath $_ } |
            Select-Object -First 1
        if (-not $dockerDesktop) {
            Fail "Docker is installed, but Docker Desktop could not be found. Start Docker Desktop manually, then retry."
        }

        try {
            Start-Process -FilePath $dockerDesktop -WindowStyle Hidden | Out-Null
        }
        catch {
            Fail "Docker Desktop could not be started automatically. Start it manually, then retry."
        }

        $deadline = (Get-Date).AddSeconds(120)
        while ((Get-Date) -lt $deadline) {
            if (Test-DockerEngine) {
                Write-Host "[PASS] Docker Desktop is ready." -ForegroundColor Green
                break
            }
            Start-Sleep -Seconds 3
        }

        if (-not (Test-DockerEngine)) {
            Fail "Docker Desktop did not become ready within 2 minutes. Open Docker Desktop, resolve any startup message, then retry."
        }
    }

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & docker compose version *> $null
        $composeAvailable = $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    if (-not $composeAvailable) {
        Fail "Docker Compose v2 is required."
    }
    if (-not (Test-Path -LiteralPath ".env")) {
        Copy-Item -LiteralPath ".env.example" -Destination ".env"
        Write-Step "Created .env from the safe development template."
    }
}

function Get-ServiceState([string]$Service) {
    $containerId = (& docker compose ps -q $Service 2>$null | Out-String).Trim()
    if (-not $containerId) {
        return [pscustomobject]@{ Running = $false; Health = "missing" }
    }
    $running = (& docker inspect --format "{{.State.Running}}" $containerId 2>$null | Out-String).Trim()
    $health = (& docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" $containerId 2>$null | Out-String).Trim()
    return [pscustomobject]@{
        Running = $running -eq "true"
        Health = $health
    }
}

function Wait-ForStack([int]$TimeoutSeconds = 180) {
    Write-Step "Waiting for all five services to become ready..."
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $allReady = $true
        foreach ($service in $ExpectedServices) {
            $state = Get-ServiceState $service
            if (-not $state.Running) {
                $allReady = $false
                break
            }
            if ($HealthyServices -contains $service -and $state.Health -ne "healthy") {
                $allReady = $false
                break
            }
        }
        if ($allReady) {
            Write-Host "[PASS] Docker services are ready." -ForegroundColor Green
            return
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)

    & docker compose ps
    & docker compose logs --tail 80 backend frontend worker
    Fail "The stack did not become healthy within $TimeoutSeconds seconds."
}

function Start-Stack([bool]$Build = $true) {
    Ensure-Docker
    Invoke-External "Validating the Docker Compose configuration..." {
        & docker compose config --quiet
    }
    $arguments = @("compose", "up", "-d")
    if ($Build) {
        $arguments += "--build"
    }
    Invoke-External "Starting the complete Docker stack..." { & docker @arguments }
    Wait-ForStack
}

function Ensure-Stack {
    Ensure-Docker
    $missing = $false
    foreach ($service in $ExpectedServices) {
        if (-not (Get-ServiceState $service).Running) {
            $missing = $true
            break
        }
    }
    if ($missing) {
        Write-Step "The stack is not running; starting it now."
        Start-Stack (-not $NoBuild)
    } else {
        Wait-ForStack
    }
}

function Invoke-RuntimeVerification([bool]$ReadOnly) {
    $mode = if ($ReadOnly) { "--read-only" } else { "" }
    $verificationScript = Get-Content -LiteralPath "scripts\verify_runtime.mjs" -Raw
    Write-Step $(if ($ReadOnly) { "Running the read-only application check..." } else { "Running the full live-event and reset check..." })
    if ($ReadOnly) {
        $verificationScript | & docker compose exec -T `
            -e ARVA_API_URL=http://backend:8000 `
            -e ARVA_FRONTEND_URL=http://frontend:3000 `
            frontend node --input-type=module - $mode
    } else {
        $verificationScript | & docker compose exec -T `
            -e ARVA_API_URL=http://backend:8000 `
            -e ARVA_FRONTEND_URL=http://frontend:3000 `
            frontend node --input-type=module -
    }
    if ($LASTEXITCODE -ne 0) {
        Fail "Runtime verification failed."
    }
}

function Invoke-SourceVerification {
    Require-Command "python" "Install Python 3.12 or newer."
    Require-Command "npm.cmd" "Install Node.js 22 or newer."

    $pythonVersion = & python -c "import sys; print(sys.version_info.major * 100 + sys.version_info.minor)"
    if ([int]$pythonVersion -lt 312) {
        Fail "Python 3.12 or newer is required for full verification."
    }
    $nodeMajor = & node -p "Number(process.versions.node.split('.')[0])"
    if ([int]$nodeMajor -lt 22) {
        Fail "Node.js 22 or newer is required for full verification."
    }

    & python -c "import pytest, ruff" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Invoke-External "Installing Python verification dependencies..." {
            & python -m pip install -e ".[dev]"
        }
    }
    if (-not (Test-Path -LiteralPath "frontend\node_modules")) {
        Invoke-External "Installing frontend verification dependencies..." {
            & npm.cmd --prefix frontend install
        }
    }

    Invoke-External "Linting backend and scripts..." {
        & python -m ruff check backend scripts
    }
    Invoke-External "Running backend tests..." {
        & python -m pytest
    }
    Invoke-External "Auditing frontend dependencies..." {
        & npm.cmd --prefix frontend audit
    }
    Invoke-External "Linting the frontend..." {
        & npm.cmd --prefix frontend run lint
    }
    Invoke-External "Running frontend tests..." {
        & npm.cmd --prefix frontend test
    }
    Invoke-External "Building the production frontend..." {
        & npm.cmd --prefix frontend run build
    }

    Push-Location -LiteralPath "frontend"
    try {
        Invoke-External "Type-checking the frontend..." {
            & npx.cmd tsc --noEmit
        }
    } finally {
        Pop-Location
    }
}

function Show-Handoff {
    Write-Host ""
    Write-Host "ARVA AI is ready." -ForegroundColor Green
    Write-Host "  App:      http://localhost:3000"
    Write-Host "  API docs: http://localhost:8000/docs"
    Write-Host "  Email:    admin@arva.local"
    Write-Host "  Password: ArvaDemo!2026"
    Write-Host ""
}

try {
    switch ($Command) {
        "start" {
            Write-Title "START"
            Start-Stack (-not $NoBuild)
            Invoke-RuntimeVerification $true
            Show-Handoff
            if (-not $NoOpen) {
                Start-Process "http://localhost:3000"
            }
        }
        "check" {
            Write-Title "QUICK CHECK"
            Ensure-Stack
            Invoke-RuntimeVerification $true
            Show-Handoff
        }
        "verify" {
            Write-Title "FULL VERIFICATION"
            Write-Host "This deep check advances the twin once and resets it to the canonical baseline." -ForegroundColor Yellow
            Start-Stack (-not $NoBuild)
            Invoke-SourceVerification
            Invoke-RuntimeVerification $false
            Write-Host "[PASS] ARVA AI passed every configured verification gate." -ForegroundColor Green
            Show-Handoff
        }
        "status" {
            Write-Title "STATUS"
            Ensure-Docker
            & docker compose ps
        }
        "demo" {
            Write-Title "MEASURED DEMO"
            Ensure-Stack
            Invoke-External "Running the measured scheduler and recovery demo..." {
                & docker compose exec -T backend python scripts/run_demo.py
            }
        }
        "stop" {
            Write-Title "STOP"
            Ensure-Docker
            Invoke-External "Stopping ARVA AI..." { & docker compose down }
        }
        "restart" {
            Write-Title "RESTART"
            Ensure-Docker
            Invoke-External "Restarting ARVA AI..." { & docker compose restart }
            Wait-ForStack
            Invoke-RuntimeVerification $true
            Show-Handoff
        }
        "reset" {
            Write-Title "FACTORY RESET"
            if (-not $Force) {
                $confirmation = Read-Host "This removes local PostgreSQL and Redis volumes. Type RESET to continue"
                if ($confirmation -ne "RESET") {
                    Write-Host "Reset cancelled."
                    exit 0
                }
            }
            Ensure-Docker
            Invoke-External "Removing local data volumes..." { & docker compose down -v }
            Start-Stack $true
            Invoke-RuntimeVerification $true
            Show-Handoff
        }
    }
    exit 0
} catch {
    Write-Host ""
    Write-Host "[FAIL] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Run '.\arva.ps1 status' and 'docker compose logs --tail 100' for details." -ForegroundColor Yellow
    exit 1
}
