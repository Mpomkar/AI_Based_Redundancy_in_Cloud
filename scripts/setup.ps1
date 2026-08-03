# One-time project setup (Windows PowerShell)
# Run from repo root: .\scripts\setup.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Cloud Redundancy AI - One-Time Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Project root: $Root`n"

function Require-Command($name, $hint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: '$name' not found. $hint" -ForegroundColor Red
        exit 1
    }
}

Require-Command "python" "Install Python 3.10+ from https://www.python.org/downloads/"
Require-Command "node" "Install Node.js 18+ from https://nodejs.org/"

$pyVersion = (python -c "import sys; print(str(sys.version_info.major) + '.' + str(sys.version_info.minor))").Trim()
$pyMajor, $pyMinor = $pyVersion.Split(".")
if ([int]$pyMajor -lt 3 -or ([int]$pyMajor -eq 3 -and [int]$pyMinor -lt 10)) {
    Write-Host "ERROR: Python 3.10+ required (found $pyVersion)." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Python $pyVersion"

$nodeVersion = (node -p "process.versions.node").Trim()
Write-Host "[OK] Node.js $nodeVersion"

# Allow npm in PowerShell for this session (common Windows issue)
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force -ErrorAction SilentlyContinue

# --- Backend ---
$backend = Join-Path $Root "backend"
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"
$requirements = Join-Path $Root "requirements.txt"

Write-Host "`n--- Backend (Python) ---" -ForegroundColor Yellow
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment..."
    Push-Location $backend
    python -m venv .venv
    Pop-Location
} else {
    Write-Host "Virtual environment already exists."
}

Write-Host "Installing Python packages (may take a few minutes)..."
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r $requirements

Write-Host "Verifying backend imports..."
Push-Location $backend
& $venvPython -c "from app.main import app; print('Backend imports OK')"
$importOk = $LASTEXITCODE -eq 0
Pop-Location
if (-not $importOk) {
    Write-Host "ERROR: Backend verification failed." -ForegroundColor Red
    exit 1
}

# --- Frontend ---
$frontend = Join-Path $Root "frontend"
Write-Host "`n--- Frontend (Node.js) ---" -ForegroundColor Yellow
Push-Location $frontend
if (Get-Command npm.cmd -ErrorAction SilentlyContinue) {
    npm.cmd install
} else {
    npm install
}
Pop-Location

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Start servers:  .\scripts\start-all.ps1"
Write-Host "  2. Or manually:"
Write-Host "       .\scripts\start-backend.ps1"
Write-Host "       .\scripts\start-frontend.ps1"
Write-Host "  3. Open browser:   http://localhost:5173"
Write-Host "  4. Login:          admin / ADMIN123"
Write-Host ""
Write-Host "Full guide: SETUP_GUIDE.md or docs\SETUP_GUIDE.html"
