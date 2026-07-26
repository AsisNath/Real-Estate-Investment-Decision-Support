@echo off
setlocal
title NorthStar - Clean Generated Files

cd /d "%~dp0"

echo.
echo ================================================
echo  NorthStar - Clean Generated Files
echo ================================================
echo.
echo Project folder:
echo %CD%
echo.
echo This removes files NorthStar regenerates automatically:
echo   - Python cache folders (__pycache__, .pytest_cache)
echo   - Analysis trail logs (knowledge_bank\...\_analysis-log.md)
echo.
echo It will NEVER delete your policy notes, PDFs, or any other
echo file you added yourself (knowledge_bank\researched, knowledge_bank\user,
echo or anything else you placed in knowledge_bank).
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$targets = @();" ^
    "$targets += Get-ChildItem -Path '.' -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue;" ^
    "if (Test-Path '.pytest_cache') { $targets += Get-Item '.pytest_cache' };" ^
    "$logs = @(); if (Test-Path 'knowledge_bank') { $logs = Get-ChildItem -Path 'knowledge_bank' -Recurse -Filter '_analysis-log.md' -File -ErrorAction SilentlyContinue };" ^
    "$dirBytes = ($targets | ForEach-Object { (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum } | Measure-Object -Sum).Sum;" ^
    "$logBytes = ($logs | Measure-Object Length -Sum).Sum;" ^
    "$totalMB = [math]::Round((($dirBytes + $logBytes)) / 1MB, 2);" ^
    "Write-Host ('  Cache folders found : ' + $targets.Count);" ^
    "Write-Host ('  Trail logs found    : ' + $logs.Count);" ^
    "Write-Host ('  Space to free       : ' + $totalMB + ' MB');" ^
    "Write-Host '';" ^
    "if ($targets.Count -eq 0 -and $logs.Count -eq 0) { Write-Host '  Nothing to clean up right now.' }" ^
    < NUL

echo.
set /p CONFIRM="Delete these files now? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo.
    echo Cancelled. Nothing was deleted.
    echo.
    pause
    exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Get-ChildItem -Path '.' -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue;" ^
    "Remove-Item -Recurse -Force '.pytest_cache' -ErrorAction SilentlyContinue;" ^
    "if (Test-Path 'knowledge_bank') { Get-ChildItem -Path 'knowledge_bank' -Recurse -Filter '_analysis-log.md' -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue }" ^
    < NUL

echo.
echo Done. Cache folders and trail logs have been removed.
echo Your policy notes and any files you added are untouched.
echo.

echo ------------------------------------------------------------
echo Optional: also remove the Python virtual environment (.venv)?
echo.
echo This is normally the SINGLE LARGEST folder in the project
echo (60+ MB), but it is not "generated data" from using the app -
echo it is installed once by Run_NorthStar.bat. Removing it is safe;
echo Run_NorthStar.bat will simply reinstall it the next time you
echo run it, which needs internet access and takes a minute or two.
echo ------------------------------------------------------------
echo.
set /p CONFIRM2="Remove .venv too? (Y/N): "
if /i "%CONFIRM2%"=="Y" (
    if exist ".venv" (
        rmdir /s /q ".venv"
        echo .venv removed. Run Run_NorthStar.bat to reinstall it.
    ) else (
        echo No .venv folder found - nothing to remove.
    )
) else (
    echo Keeping .venv.
)

echo.
pause
