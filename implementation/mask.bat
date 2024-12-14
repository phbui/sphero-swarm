@echo off
echo Starting Python servers with virtual environments...

:: Change directory to the Python server folder, activate venv, and run receiver.py
start cmd /k "python mask_finder.py"

:: Change directory to the Python server folder, activate venv, and run receiver.py
start cmd /k "cd /d %~dp0controller-server && venv\Scripts\activate && python receiver.py"

echo Servers are running in separate windows.