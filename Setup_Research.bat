@echo off
REM ============================================================================
REM  NorthStar - turn on automatic policy research
REM
REM  Creates the .env file the app reads at startup and opens it in Notepad so
REM  you can paste your Anthropic API key. Nothing is sent anywhere: .env stays
REM  on this machine and is git-ignored, so the key never reaches GitHub.
REM
REM  After this, every analysis of an address with no policy note researches it
REM  automatically and saves the result under knowledge_bank\researched\zips\.
REM ============================================================================

setlocal
cd /d "%~dp0"

echo.
echo  NorthStar - Automatic Policy Research Setup
echo  ==========================================
echo.

if exist ".env" (
    echo  A .env file already exists. Opening it so you can check or update the key.
    echo.
    goto :open
)

if not exist ".env.example" (
    echo  ERROR: .env.example is missing, so there is no template to copy.
    echo  Re-download the project or create .env by hand with this one line:
    echo.
    echo      ANTHROPIC_API_KEY=your-key-here
    echo.
    pause
    exit /b 1
)

copy /y ".env.example" ".env" >nul
if errorlevel 1 (
    echo  ERROR: could not create .env in this folder.
    pause
    exit /b 1
)
echo  Created .env from the template.
echo.

:open
echo  Next steps:
echo.
echo    1. Get a key at  https://console.anthropic.com/settings/keys
echo    2. Paste it after ANTHROPIC_API_KEY=  in the file that just opened
echo    3. Save the file and close Notepad
echo    4. Run Run_NorthStar.bat
echo.
echo  Cost: roughly one request per NEW address. A researched note is saved and
echo  reused, so the same ZIP is never charged twice.
echo.
echo  Opening .env in Notepad...
start "" notepad ".env"
echo.
echo  Done. Close this window once you have saved your key.
pause
endlocal
