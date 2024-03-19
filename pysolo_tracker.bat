@echo off

rem for miniconda3 installed in the default user's directory use the path below
rem otherwise set it to your miniconda install directory
set CONDA_DIR=%HOMEPATH%\miniconda3

set PATH=%CONDA_DIR%;%CONDA_DIR%\Scripts;%CONDA_DIR%\lib;%PATH%

call activate pysolo-tools

call python pysolo_tracker.py %*

call conda.bat deactivate
