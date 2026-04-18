@echo off
cd /d "%~dp0"
set "PYTHONW=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%PYTHONW%" set "PYTHONW=pythonw"
set "SOURCE=auto"
if exist "%~dp0profiles\" (
    for /d %%D in ("%~dp0profiles\*") do (
        if /I not "%%~nxD"=="zalo_web_agent" set "SOURCE=local"
    )
)
echo ==============================================
echo   MICROSOFT REWARDS FARMER (Hidden Mode)
echo ==============================================
echo.
echo [1] Starting Farmer in Background...
echo     (Clone mode - Khong can dong Edge)
echo     Source: %SOURCE%
start "" "%PYTHONW%" "%~dp0farm_rewards.py" --source %SOURCE%

echo [2] Done! Script is running silently.
echo     Use 'View_Logs.bat' to see progress.
echo     Use 'Stop_Rewards.bat' to stop.
echo.
timeout /t 5
