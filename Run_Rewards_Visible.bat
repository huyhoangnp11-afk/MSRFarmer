@echo off
cd /d "%~dp0"
echo Starting Farmer in VISIBLE mode (for Login or Debug)...
.venv\Scripts\python.exe farm_rewards.py --visible
pause
