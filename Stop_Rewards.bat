@echo off
cd /d "%~dp0"
echo Stopping all Rewards processes...
taskkill /F /IM python.exe /IM pythonw.exe /IM msedgedriver.exe /IM msedge.exe
echo.
echo All stopped.
pause
