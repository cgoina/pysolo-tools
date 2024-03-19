#!/bin/bash

CONDA_HOME=/opt/homebrew/Caskroom/mambaforge/base
. ${CONDA_HOME}/etc/profile.d/conda.sh

conda activate pysolo-tools
python pysolo_app.py
