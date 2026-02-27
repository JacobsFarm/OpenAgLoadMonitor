@echo off
title openAgloadMonitor
REM Configuration - modify these variables as needed
REM To see version conda in anaconda prompt = echo %CONDA_PREFIX%
set PROJECT_DRIVE=Cd \
set PROJECT_FOLDER=openagloadmonitor
set SCRIPT=run.py

REM Navigate to project directory
%PROJECT_DRIVE%
cd %PROJECT_FOLDER%

REM Launch script
echo Starting %SCRIPT%...
start "Script run" cmd /k python %SCRIPT%

REM Show current location and keep main window open
echo Script started in: %cd%
cmd /k
