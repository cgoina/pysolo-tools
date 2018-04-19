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

It is possible to analyze multiple frame intervals in parallel by specifying the number of processes, using the '--nprocesses' flag.
If multiple frames are analyzed in parallel the results are output in a file, whose name is suffixed with the corresponding interval
in seconds. For example if the movie length is 40000s and I want to run 4 processes to analyze the number of crossings in one area,
the results will be in:
- 'Monitor01-crossings-0-10000.txt'
- 'Monitor01-crossings-10000-20000.txt'
- 'Monitor01-crossings-20000-30000.txt'
- 'Monitor01-crossings-30000-40000.txt'

The downside with running multiple intervals in parallel is that for each interval the first frame will not generate accurate results
and also if you want all results in a single file the sub-result files will have to be concatenated together.
