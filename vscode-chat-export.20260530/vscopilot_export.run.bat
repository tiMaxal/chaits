@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "WORKSPACE_PATH=%SCRIPT_DIR%"
if "%WORKSPACE_PATH:~-1%"=="\" set "WORKSPACE_PATH=%WORKSPACE_PATH:~0,-1%"
set "PS_SCRIPT=%SCRIPT_DIR%vscopilot_export-chat-sessions.in-workspace.20260530.ps1"

if not exist "%PS_SCRIPT%" (
  echo PowerShell script not found:
  echo %PS_SCRIPT%
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -WorkspacePath "%WORKSPACE_PATH%" %*
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo Done. Exit code: %EXIT_CODE%
pause
exit /b %EXIT_CODE%
