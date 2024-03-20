### Dev Environment

* Download Miniforge installers from [github](https://github.com/conda-forge/miniforge) or conda if you prefer conda. For the conda installation you can find instructions [here](https://docs.conda.io/projects/conda/en/stable/). 

* Initialize conda. Before running conda you must run `conda init` for windows or `source $CONDA_DIR/base/etc/profile.d/conda.sh` on unix like systems, where CONDA_DIR points to the location of the conda install directory.

* Create/Update a conda environment. 

    * If this is a new environment use:
```
conda env create -n pysolo-tools -f conda-env.yml
```

    * If the environment already exists because you either created it manually or the above failed to install all packages use:
```
conda env update -n pysolo-tools -f conda-env.yml
```

* If the environment was created successfully activate it:
```
conda activate pysolo-tools
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
