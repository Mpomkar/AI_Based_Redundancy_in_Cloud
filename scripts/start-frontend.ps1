# Start Vite frontend (run after setup.ps1)
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$frontend = Join-Path $Root "frontend"

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "node_modules not found. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force -ErrorAction SilentlyContinue

Write-Host "Starting frontend (Vite dev server)" -ForegroundColor Cyan
Write-Host "Open http://localhost:5173 (or next free port)" -ForegroundColor Gray
Set-Location $frontend

if (Get-Command npm.cmd -ErrorAction SilentlyContinue) {
    npm.cmd run dev
} else {
    npm run dev
}
