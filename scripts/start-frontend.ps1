# Start Vite frontend (run after setup.ps1)
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$frontend = Join-Path $Root "frontend"

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "node_modules not found. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force -ErrorAction SilentlyContinue

$lanIp = $null
try {
    $lanIp = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
        Select-Object -ExpandProperty IPAddress -First 1
} catch { }

Write-Host "Starting frontend (Vite — reachable on LAN)" -ForegroundColor Cyan
Write-Host "  Local: http://localhost:5173" -ForegroundColor Gray
if ($lanIp) {
    Write-Host "  LAN:   http://${lanIp}:5173  <-- open this on other PCs to share data" -ForegroundColor Green
}
Write-Host "Data is shared when all browsers talk to the SAME backend on this PC." -ForegroundColor Yellow

Set-Location $frontend

if (Get-Command npm.cmd -ErrorAction SilentlyContinue) {
    npm.cmd run dev -- --host
} else {
    npm run dev -- --host
}
