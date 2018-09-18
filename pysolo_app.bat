@echo off

rem for miniconda3 installed in the default user's directory use the path below
rem otherwise set it to your miniconda install directory
set MINICONDA_DIR=%HOMEPATH%\AppData\Local\Continuum\miniconda3

set PATH=%MINICONDA_DIR%;%MINICONDA_DIR%\Scripts;%MINICONDA_DIR%\lib;%PATH%

call activate pysolo-tools

python pysolo_app.py %*
