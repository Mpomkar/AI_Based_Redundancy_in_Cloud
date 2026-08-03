# Start FastAPI backend (run after setup.ps1)
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$backend = Join-Path $Root "backend"
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Virtual environment not found. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "Starting backend at http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "API docs: http://127.0.0.1:8000/docs" -ForegroundColor Gray
Set-Location $backend
& $venvPython -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
