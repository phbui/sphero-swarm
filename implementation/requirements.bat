@echo off
echo Ensuring pip and installing requirements for all servers...

:: Brain-server setup
echo Setting up brain-server...
cd /d %~dp0brain-server
if not exist venv (
    echo Creating virtual environment for brain-server...
    python -m venv venv
)
venv\Scripts\python -m ensurepip --upgrade
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install --no-cache-dir -r requirements.txt

:: Controller-server setup
echo Setting up controller-server...
cd /d %~dp0controller-server
if not exist venv (
    echo Creating virtual environment for controller-server...
    python -m venv venv
)
venv\Scripts\python -m ensurepip --upgrade
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install --no-cache-dir -r requirements.txt

echo Virtual environments and dependencies are ready.