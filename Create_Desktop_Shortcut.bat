@echo off
cd /d "%~dp0"
echo ==============================================
echo   CREATE DESKTOP SHORTCUT
echo   MS Rewards Farmer Tray
echo ==============================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1"
if %errorlevel%==0 (
    echo.
    echo [OK] Da tao shortcut tray app tren Desktop.
) else (
    echo.
    echo [LOI] Khong the tao shortcut tu moi truong hien tai.
    echo       Hay chay file nay truc tiep tren Windows cua ban.
)

echo.
pause
