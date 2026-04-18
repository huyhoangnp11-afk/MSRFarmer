@echo off
:: Tạo Desktop Shortcut cho Farm Menu
set SCRIPT_PATH=e:\MSrequat\farm_menu.pyw
set SHORTCUT_NAME=MS Rewards Menu.lnk
set DESKTOP=%USERPROFILE%\Desktop

echo Đang tạo shortcut Menu trên Desktop...

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP%\%SHORTCUT_NAME%'); $Shortcut.TargetPath = 'pythonw.exe'; $Shortcut.Arguments = '\"%SCRIPT_PATH%\"'; $Shortcut.WorkingDirectory = 'e:\MSrequat'; $Shortcut.Description = 'MS Rewards Farm Menu'; $Shortcut.Save()"

if exist "%DESKTOP%\%SHORTCUT_NAME%" (
    echo ✅ Đã tạo shortcut Menu thành công!
) else (
    echo ❌ Không thể tạo shortcut.
)

timeout /t 2 >nul
