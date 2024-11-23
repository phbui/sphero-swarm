@echo off
echo Starting Node server and Python server...

:: Change directory to the Python server folder and run receiver.py
start cmd /k "cd /d %~dp0brain-server && python receiver.py"

:: Change directory to the Python server folder and run receiver.py
start cmd /k "cd /d %~dp0controller-server && python receiver.py"

:: Change directory to the Node server folder and run server.js
start cmd /k "cd /d %~dp0web-socket-server && node server.js"

echo Servers are running in separate windows.
