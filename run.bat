@echo off
title openagloadmonitor
REM Configuration - modify these variables as needed
REM To see version conda in anaconda prompt = echo %CONDA_PREFIX%
set CONDA_PATH="C:\ProgramData\anaconda3\Scripts\activate.bat" 
set PROJECT_DRIVE=C:
set PROJECT_FOLDER=openagloadmonitor
set SCRIPT_NAME=run.py

REM Navigate to project directory and activate environment
call %CONDA_PATH%
%PROJECT_DRIVE%
cd %PROJECT_FOLDER%
python %SCRIPT_NAME%

REM Show current location and open interactive command prompt
echo Anaconda environment activated in %cd%
cmd /k
