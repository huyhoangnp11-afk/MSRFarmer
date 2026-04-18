@echo off
cd /d "%~dp0"
echo Waiting for logs...
powershell -Command "$latest = Get-ChildItem logs/farm_log_*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1; if ($latest) { Write-Host 'Reading: ' $latest.Name -ForegroundColor Green; Get-Content $latest.FullName -Wait -Tail 50 } else { Write-Host 'No logs found yet.' -ForegroundColor Red }"
pause
