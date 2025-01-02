@echo off
echo Installing requirements for Python servers with virtual environments...

:: Change directory to the Python server folder, activate venv, and run receiver.py
start cmd /k "cd /d %~dp0brain-server && venv\Scripts\activate && pip install -r requirements.txt"

:: Change directory to the Python server folder, activate venv, and run receiver.py
start cmd /k "cd /d %~dp0controller-server && venv\Scripts\activate && pip install -r requirements.txt"

echo Installation complete!