param(
    [string]$TaskName = "MS Rewards Farmer Daily",
    [string]$RunTime = "08:00"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runScript = Join-Path $scriptDir "run_hidden.vbs"

if (-not (Test-Path $runScript)) {
    throw "Khong tim thay file run_hidden.vbs trong: $scriptDir"
}

$ws = New-Object -ComObject WScript.Shell
$desktop = [System.Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "MS Rewards Farmer.lnk"

$shortcut = $ws.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = "`"$runScript`""
$shortcut.WorkingDirectory = $scriptDir
$shortcut.IconLocation = "C:\Windows\System32\shell32.dll,13"
$shortcut.Description = "MS Rewards Farmer - Chay an moi ngay"
try {
    $shortcut.Save()
    Write-Host "Desktop shortcut created: $shortcutPath"
} catch {
    Write-Warning "Khong the tao shortcut Desktop: $($_.Exception.Message)"
}

$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$runScript`"" -WorkingDirectory $scriptDir
$dailyTrigger = New-ScheduledTaskTrigger -Daily -At $RunTime
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn
$logonTrigger.Delay = "PT2M"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger @($dailyTrigger, $logonTrigger) `
    -Settings $settings `
    -Principal $principal `
    -Description "Tu dong farm MS Rewards moi ngay luc $RunTime" `
    -Force | Out-Null

Write-Host "Task Scheduler da duoc tao/cap nhat: $TaskName"
Write-Host "Lich chay hang ngay: $RunTime"
