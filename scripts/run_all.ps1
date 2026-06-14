<#
Run this script from the project root in PowerShell to:
  1) activate the venv
  2) run `alembic upgrade head`
  3) start the FastAPI app (uvicorn) in background
  4) wait for a COM port and start the serial bridge in background

Usage:
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned; .\scripts\run_all.ps1 -ComPort COM5
#>
param(
    [string]$ComPort = "COM5",
    [int]$PortWaitSeconds = 30
)

Write-Host "Running helper: migrations → backend → serial bridge"

# Activate venv by using the venv python directly for commands
$venvPython = Join-Path $PSScriptRoot "..\venv\Scripts\python.exe" | Resolve-Path -ErrorAction SilentlyContinue
if (-not $venvPython) {
    Write-Error "Could not find venv Python at ..\venv\Scripts\python.exe. Activate your virtualenv first or adjust path.";
    exit 1
}
$venvPython = $venvPython.Path

# Step 1: Alembic upgrade
Write-Host "Running alembic upgrade head..."
$alembicExe = "alembic"
# Call via python -m alembic if alembic CLI isn't on PATH
$alembicCmd = & $venvPython -m alembic current 2>&1
Write-Host $alembicCmd
$upgradeResult = & $venvPython -m alembic upgrade head 2>&1
Write-Host $upgradeResult

# Step 2: Start uvicorn in background and capture output to log
$uvicornLog = Join-Path $PSScriptRoot "..\logs\uvicorn.log"
New-Item -ItemType Directory -Path (Split-Path $uvicornLog) -Force | Out-Null
Write-Host "Starting uvicorn (background). Logs -> $uvicornLog"
Start-Process -FilePath $venvPython -ArgumentList "-m uvicorn main:app --reload" -RedirectStandardOutput $uvicornLog -RedirectStandardError $uvicornLog -WindowStyle Hidden

# Step 3: Wait a short while for the backend to boot
Start-Sleep -Seconds 3

# Step 4: Wait for COM port to appear
Write-Host "Waiting up to $PortWaitSeconds seconds for COM port $ComPort to be available..."
$found = $false
$endTime = (Get-Date).AddSeconds($PortWaitSeconds)
while ((Get-Date) -lt $endTime) {
    try {
        $portsOut = & $venvPython -c "import serial.tools.list_ports as p; print([c.device for c in p.comports()])" 2>$null
        if ($portsOut -match $ComPort) { $found = $true; break }
    } catch {
        # ignore
    }
    Start-Sleep -Seconds 1
}

if (-not $found) {
    Write-Warning "COM port $ComPort not found. You can plug the device now and then run the serial bridge manually:"
    Write-Host "  $env:COMSPEC /c powershell -NoProfile -Command \"$env:SERIAL_PORT='$ComPort'; python scripts/serial_bridge.py\""
    exit 0
}

# Step 5: Start serial bridge in background
$bridgeLog = Join-Path $PSScriptRoot "..\logs\serial_bridge.log"
Write-Host "Starting serial_bridge.py (background). Logs -> $bridgeLog"
Start-Process -FilePath $venvPython -ArgumentList "scripts/serial_bridge.py" -RedirectStandardOutput $bridgeLog -RedirectStandardError $bridgeLog -WindowStyle Hidden

Write-Host "All background processes started. Check logs in the 'logs' directory."