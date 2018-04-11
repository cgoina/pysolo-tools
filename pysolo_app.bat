@echo off

call conda activate pysolo-tools
pythonw pysolo_app.py %*
