@echo off
setlocal
title NorthStar Property Investment Consulting

cd /d "%~dp0"

echo.
echo ================================================
echo  NorthStar Property Investment Consulting
echo ================================================
echo.
echo Project folder:
echo %CD%
echo.

set "PYTHON_CMD=python"
python --version >nul 2>&1
if errorlevel 1 (
    py -3 --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python was not found.
        echo Install Python 3.11 or newer, then run this file again.
        echo.
        pause
        exit /b 1
    )
    set "PYTHON_CMD=py -3"
)

if exist ".venv" (
    if not exist ".venv\Scripts\python.exe" (
        echo The .venv folder exists but looks incomplete or corrupted - rebuilding it...
        rmdir /s /q ".venv"
    ) else if not exist ".venv\pyvenv.cfg" (
        echo The .venv folder exists but is missing pyvenv.cfg - rebuilding it...
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating local virtual environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo.
        echo ERROR: Could not create the virtual environment.
        pause
        exit /b 1
    )
    if not exist ".venv\pyvenv.cfg" (
        echo.
        echo ERROR: The virtual environment was created but still looks incomplete.
        echo Delete the .venv folder by hand and run this file again.
        pause
        exit /b 1
    )
)

echo.
echo Installing required packages...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo.
    echo ERROR: Could not update pip.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Could not install the required packages.
    echo Check your internet connection, then run this file again.
    pause
    exit /b 1
)

echo.
echo Running quick tests...
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 (
    echo.
    echo ERROR: Tests failed. The app will not start until the issue is fixed.
    pause
    exit /b 1
)

echo.
echo Checking port 8000 for an old NorthStar server...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ids = @(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); if ($ids.Count -eq 0) { Write-Host '  Port 8000 is free.'; exit }; $stopped = 0; foreach ($id in $ids) { $p = Get-Process -Id $id -ErrorAction SilentlyContinue; if ($p -and $p.ProcessName -like 'python*') { Write-Host ('  Stopping old server: PID ' + $p.Id + ' (started ' + $p.StartTime + ')'); Stop-Process -Id $p.Id -Force; $stopped = $stopped + 1 } elseif ($p) { Write-Host ('  WARNING: port 8000 is used by ' + $p.ProcessName + ' (PID ' + $p.Id + '), which is not a NorthStar server. Close it manually.') } }; if ($stopped -gt 0) { Start-Sleep -Seconds 2; Write-Host '  Old server stopped.' }"

echo.
echo Starting NorthStar at http://127.0.0.1:8000
echo Keep this window open while using the app.
echo Press Ctrl+C in this window to stop the server.
echo.

start "" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:8000'"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

echo.
echo NorthStar server stopped.
pause
