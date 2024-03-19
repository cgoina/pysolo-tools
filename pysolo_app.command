#!/bin/bash

CONDA_HOME=/usr/local/Caskroom/miniconda/base
. ${CONDA_HOME}/etc/profile.d/conda.sh

conda activate pysolo-tools
python pysolo_app.py
