@echo off
chcp 65001 >nul
cd /d "%~dp0"
if "%PROJECT_ERO_HOST%"=="" set "PROJECT_ERO_HOST=127.0.0.1"
if "%PROJECT_ERO_PORT%"=="" set "PROJECT_ERO_PORT=8000"
set "PROJECT_ERO_BROWSER_HOST=%PROJECT_ERO_HOST%"
if "%PROJECT_ERO_BROWSER_HOST%"=="0.0.0.0" set "PROJECT_ERO_BROWSER_HOST=localhost"

echo ===================================================
echo     PROJECT ERO WEBUI LAUNCHER
echo ===================================================
echo.
echo Starting Backend Server...
echo The browser will open automatically in a few seconds.
echo.

:: Use a background PowerShell process to wait 3 seconds and then open the browser
start /B powershell -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://%PROJECT_ERO_BROWSER_HOST%:%PROJECT_ERO_PORT%'"

:: Navigate to the webui folder and start uvicorn
cd webui
python -m uvicorn app:app --host %PROJECT_ERO_HOST% --port %PROJECT_ERO_PORT% --reload

echo.
echo ==========================================
echo Server closed or crashed!
echo Please check the error message above.
echo ==========================================
pause
