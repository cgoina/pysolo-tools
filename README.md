### Dev Environment

```
brew install caskroom/cask/miniconda
conda create -n pysolo-tools python=3.6
conda activate pysolo-tools
conda install opencv
conda install pyqt
```

### Running the application
Before running the application the log directory must exist - python logger doesn't create
directories.
`mkdir logs`

```
python pysolo_app.py
```
