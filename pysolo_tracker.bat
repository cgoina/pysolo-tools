@echo off

rem for miniforge3 installed with default option for all users,
rem use the path below
rem otherwise set it to your miniconda install directory
set CONDA_DIR=C:\ProgramData\miniforge3

set PATH=%CONDA_DIR%;%CONDA_DIR%\Scripts;%CONDA_DIR%\lib;%PATH%

call activate pysolo-tools

call python pysolo_tracker.py %*

call conda.bat deactivate
