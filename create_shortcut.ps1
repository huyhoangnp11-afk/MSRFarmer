$ErrorActionPreference = "Stop"

$ws = New-Object -ComObject WScript.Shell
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktop = [Environment]::GetFolderPath("Desktop")
$lnkPath = Join-Path $desktop "MS Rewards Farmer Tray.lnk"
$pythonwPath = Join-Path $scriptDir ".venv\Scripts\pythonw.exe"
$trayAppPath = Join-Path $scriptDir "tray_app.py"
$iconPath = Join-Path $scriptDir "farm_icon.png"
$obsoleteShortcuts = @(
    "MS Rewards Farmer.lnk",
    "MS Rewards Farm.lnk",
    "launcher_gui - Shortcut.lnk"
)

if (-not (Test-Path $trayAppPath)) {
    throw "Khong tim thay tray_app.py trong: $scriptDir"
}

if (-not (Test-Path $pythonwPath)) {
    throw "Khong tim thay pythonw.exe trong .venv. Hay kiem tra lai moi truong ao."
}

foreach ($name in $obsoleteShortcuts) {
    Remove-Item (Join-Path $desktop $name) -Force -ErrorAction SilentlyContinue
}

Remove-Item $lnkPath -Force -ErrorAction SilentlyContinue

$shortcut = $ws.CreateShortcut($lnkPath)
$shortcut.TargetPath = $pythonwPath
$shortcut.Arguments = "`"$trayAppPath`""
$shortcut.WorkingDirectory = $scriptDir
$shortcut.Description = "MS Rewards Farmer tray app"
$shortcut.WindowStyle = 7
if (Test-Path $iconPath) {
    $shortcut.IconLocation = $iconPath
} else {
    $shortcut.IconLocation = "C:\Windows\System32\shell32.dll,13"
}
$shortcut.Save()

Write-Host "Done! Shortcut -> $lnkPath"
Write-Host "Old desktop shortcuts cleaned up."
