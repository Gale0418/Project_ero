# start_webui.ps1
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\..\.." | Select-Object -ExpandProperty Path
$WebUIRoot = "$PSScriptRoot\webui"
$HostAddress = if ($env:PROJECT_ERO_HOST) { $env:PROJECT_ERO_HOST } else { "127.0.0.1" }
$Port = if ($env:PROJECT_ERO_PORT) { $env:PROJECT_ERO_PORT } else { "8000" }

Write-Host "Starting Project Ero WebUI Backend Server..." -ForegroundColor Cyan
Write-Host "Server will be available at http://$HostAddress`:$Port" -ForegroundColor Green

# Use uvicorn to start the app
Set-Location -Path $WebUIRoot
python -m uvicorn app:app --host $HostAddress --port $Port --reload
