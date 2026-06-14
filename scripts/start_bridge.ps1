# SafeHelm — Serial Bridge Launcher
# Run this script to start the bridge without setting env vars manually
# Usage: Right-click → Run with PowerShell  OR  just run: .\scripts\start_bridge.ps1

$env:SERIAL_PORT   = "COM3"
$env:LOGIN_EMAIL   = "admin@smarthelmet.com"
$env:LOGIN_PASSWORD= "admin123"
$env:HELMET_UUID   = "8a4d138a-cb36-4d9f-b3df-0cfc396b3f02"
$env:API_BASE      = "http://localhost:8000"

Write-Host "Starting SafeHelm Serial Bridge..." -ForegroundColor Cyan
Write-Host "  Port  : $env:SERIAL_PORT" -ForegroundColor Gray
Write-Host "  Helmet: $env:HELMET_UUID" -ForegroundColor Gray
Write-Host "  API   : $env:API_BASE" -ForegroundColor Gray
Write-Host ""

& ".\venv\Scripts\python.exe" scripts/serial_bridge.py
