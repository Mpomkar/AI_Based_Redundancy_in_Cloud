# Open backend and frontend in separate PowerShell windows
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$setupScript = Join-Path $Root "scripts\setup.ps1"

if (-not (Test-Path (Join-Path $Root "backend\.venv\Scripts\python.exe"))) {
    Write-Host "First-time setup required. Running setup.ps1 ..." -ForegroundColor Yellow
    & $setupScript
}

$backendScript = Join-Path $Root "scripts\start-backend.ps1"
$frontendScript = Join-Path $Root "scripts\start-frontend.ps1"

Write-Host "Opening backend and frontend in new windows..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $backendScript
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $frontendScript

Write-Host ""
Write-Host "Servers starting in separate windows." -ForegroundColor Green
Write-Host "  App:    http://localhost:5173"
Write-Host "  API:    http://127.0.0.1:8000"
Write-Host "  Login:  admin / ADMIN123"
