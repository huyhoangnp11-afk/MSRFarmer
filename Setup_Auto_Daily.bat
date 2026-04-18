@echo off
cd /d "%~dp0"
echo ==============================================
echo   SETUP: MS Rewards Farmer Daily Auto-Run
echo   (Task Scheduler cho user hien tai)
echo ==============================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_daily.ps1"
if %errorlevel%==0 (
    echo.
    echo [OK] Task Scheduler da duoc cap nhat!
    echo     - Chay moi ngay luc 8:00 AM
    echo     - Chay khi dang nhap (sau 2 phut)
    echo     - Chay bu neu bi lo gio
) else (
    echo.
    echo [LOI] Khong the tao task tu dong.
    echo       Mo PowerShell va chay:
    echo       powershell -ExecutionPolicy Bypass -File "%~dp0setup_daily.ps1"
)

echo.
pause
