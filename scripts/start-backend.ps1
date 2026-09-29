# Start FastAPI backend (run after setup.ps1)
# Listens on all interfaces so other PCs on the LAN can share the same DB/files.
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$backend = Join-Path $Root "backend"
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Virtual environment not found. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

$hostName = "0.0.0.0"
$port = 8000

# Best-effort LAN IP for teammates
$lanIp = $null
try {
    $lanIp = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
        Select-Object -ExpandProperty IPAddress -First 1
} catch { }

Write-Host "Starting backend (shared SQLite + uploads on THIS PC)" -ForegroundColor Cyan
Write-Host "  Local:  http://127.0.0.1:$port" -ForegroundColor Gray
Write-Host "  Docs:   http://127.0.0.1:$port/docs" -ForegroundColor Gray
if ($lanIp) {
    Write-Host "  LAN:    http://${lanIp}:$port   <-- other PCs use this (or open frontend LAN URL)" -ForegroundColor Green
}
# Resolve storage path the same way the app does
try {
    $stor = & $venvPython -c "from app.config import settings; print(settings.storage_dir)"
    Write-Host "  Files:  $stor" -ForegroundColor Green
} catch {
    Write-Host "  Files:  Desktop\Uploaded Files (default)" -ForegroundColor Green
}
Write-Host "Other systems must use THIS backend to see the same admin files." -ForegroundColor Yellow

Set-Location $backend
& $venvPython -m uvicorn app.main:app --reload --host $hostName --port $port
