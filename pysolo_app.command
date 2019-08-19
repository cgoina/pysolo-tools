#!/bin/bash

CONDA_HOME=~/Tools/miniconda3
. ${CONDA_HOME}/etc/profile.d/conda.sh

conda activate pysolo-tools
python pysolo_app.py
