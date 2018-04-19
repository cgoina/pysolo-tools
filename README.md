### Dev Environment

```
brew install caskroom/cask/miniconda
conda create -n pysolo-tools python=3.6
conda activate pysolo-tools
conda install opencv
conda install pyqt
pip install multiprocess
```

### Running the application
Before running the application the log directory must exist - python logger doesn't create
directories.
`mkdir logs`

```
python pysolo_app.py
```

### Running the headless tracker
```
python pysolo_tracker.py -c path-to-cfg-file
```

In headless mode the user has the option to specify the number of threads in the thread pool to use for analyzing the ROIs
but unfortunately python will not execute more than one thread at a time anyway so what I found was
that using multiple threads really doesn't help to speed up the analysis.
