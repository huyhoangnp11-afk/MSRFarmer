@echo off
cd /d "%~dp0"
echo ==============================================
echo   SETUP: MS Rewards Farmer Run On Startup
echo ==============================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_startup.ps1"
if %errorlevel%==0 (
    echo.
    echo [OK] Da cau hinh tray chay cung Windows.
    echo     - Tu khoi dong sau khi dang nhap
    echo     - Delay 2 phut de may on dinh
    echo     - Hien icon o system tray
    echo     - Tu chi farm profile chua xong hom nay
) else (
    echo.
    echo [LOI] Khong the ghi vao Startup folder tu moi truong hien tai.
    echo       Hay tu chay file nay truc tiep tren Windows cua ban.
)

echo.
pause
