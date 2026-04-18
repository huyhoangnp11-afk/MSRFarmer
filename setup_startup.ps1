param(
    [string]$ShortcutName = "MS Rewards Farmer Background.lnk"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$startupScript = Join-Path $scriptDir "startup_hidden.vbs"

if (-not (Test-Path $startupScript)) {
    throw "Khong tim thay file startup_hidden.vbs trong: $scriptDir"
}

$ws = New-Object -ComObject WScript.Shell
$startupDir = [Environment]::GetFolderPath([Environment+SpecialFolder]::Startup)
$shortcutPath = Join-Path $startupDir $ShortcutName

$shortcut = $ws.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = "`"$startupScript`""
$shortcut.WorkingDirectory = $scriptDir
$shortcut.IconLocation = "C:\Windows\System32\shell32.dll,13"
$shortcut.Description = "MS Rewards Farmer tray - chay cung Windows"
$shortcut.Save()

Write-Host "Startup shortcut created: $shortcutPath"
Write-Host "MS Rewards Farmer tray se tu chay sau khi dang nhap Windows."
