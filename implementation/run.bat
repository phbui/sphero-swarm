@echo off
echo Starting Node server and Python servers with virtual environments...

:: Start brain-server
start cmd /k "cd /d %~dp0brain-server && venv\Scripts\python receiver.py"

:: Start controller-server
start cmd /k "cd /d %~dp0controller-server && venv\Scripts\python receiver.py"

:: Start Node server
start cmd /k "cd /d %~dp0web-socket-server && node server.js"

echo Servers are running in separate windows.