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
echo   - Python cache folders (app\__pycache__, tests\__pycache__, .pytest_cache)
echo   - Analysis trail logs (knowledge_bank\...\_analysis-log.md)
echo.
echo It will NEVER delete your policy notes, PDFs, or any other
echo file you added yourself (knowledge_bank\researched, knowledge_bank\user,
echo or anything else you placed in knowledge_bank). It also never touches
echo app\*.py, static\, templates\, or anything else Run_NorthStar.bat needs.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$targets = @();" ^
    "foreach ($p in @('app\__pycache__','tests\__pycache__','.pytest_cache')) { if (Test-Path $p) { $targets += Get-Item $p } };" ^
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

for %%D in ("app\__pycache__" "tests\__pycache__" ".pytest_cache") do (
    if exist %%D rmdir /s /q %%D
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
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
echo it is installed once by Run_NorthStar.bat. Removing it is safe
echo AS LONG AS IT FULLY SUCCEEDS: close any other terminal, editor,
echo or running NorthStar server that might be using files inside
echo .venv before choosing Y, or Windows may only partially delete
echo it and leave a broken environment behind.
echo ------------------------------------------------------------
echo.
set /p CONFIRM2="Remove .venv too? (Y/N): "
if /i "%CONFIRM2%"=="Y" (
    if exist ".venv" (
        rmdir /s /q ".venv" 2>nul
        if exist ".venv" (
            echo.
            echo WARNING: .venv could not be fully removed - some files are
            echo probably in use by another program ^(a terminal, an editor,
            echo or a running NorthStar server^). It has been left as-is so it
            echo does not end up in a broken, half-deleted state.
            echo.
            echo Close anything that might be using the project folder, then
            echo run this file again if you still want to remove it. Do NOT
            echo run Run_NorthStar.bat until .venv is either fully removed or
            echo fully intact - Run_NorthStar.bat now detects and repairs a
            echo broken .venv automatically, but it is safer to finish this
            echo removal cleanly first.
        ) else (
            echo .venv removed. Run Run_NorthStar.bat to reinstall it.
        )
    ) else (
        echo No .venv folder found - nothing to remove.
    )
) else (
    echo Keeping .venv.
)

echo.
pause
