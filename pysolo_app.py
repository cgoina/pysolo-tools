#!/usr/bin/env python

import sys

from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QMainWindow, QHBoxLayout,
                             QLabel, QLineEdit, QGridLayout, QFileDialog)


class PySoloMainAppWindow(QMainWindow):
    def __init__(self, parent=None):
        super(PySoloMainAppWindow, self).__init__(parent)
        self._monitor_widget = MonitorWidget(self)
        self._form_widget = FormWidget(self)
        mainWidget = QWidget()
        layout = QHBoxLayout(mainWidget)
        layout.addWidget(self._monitor_widget)
        layout.addWidget(self._form_widget)
        self.setCentralWidget(mainWidget)


class MonitorWidget(QWidget):
    def __init__(self, parent):
        super(MonitorWidget, self).__init__(parent)
        self._initUI()

    def _initUI(self):
        self.resize(700, 300)


class FormWidget(QWidget):
    def __init__(self, parent):
        super(FormWidget, self).__init__(parent)
        self._initUI()

    def _initUI(self):
        self.__controls()
        self.__layout()

    def __controls(self):
        self._source_filename_txt = QLineEdit()
        self._source_filename_txt.setDisabled(True)
        self._n_monitored_areas_txt = QLineEdit()

    def __layout(self):
        formLayout = QGridLayout()
        source_filename_lbl = QLabel("Select source file")
        source_filename_btn = QPushButton("Open...")
        formLayout.addWidget(source_filename_lbl, 0, 0)
        formLayout.addWidget(self._source_filename_txt, 0, 1, 1, 2)
        formLayout.addWidget(source_filename_btn, 0, 3, 1, 2)
        source_filename_btn.clicked.connect(self._select_source_filename)

        n_monitored_areas_lbl = QLabel("Number of monitors")
        formLayout.addWidget(n_monitored_areas_lbl, 1, 0)
        formLayout.addWidget(self._n_monitored_areas_txt, 1, 1, 1, 2)

        self.setLayout(formLayout)

    def _select_source_filename(self):
        options = QFileDialog.Options(QFileDialog.DontUseNativeDialog)
        fileName, _ = QFileDialog.getOpenFileName(self, "Select source file",
                                                  self._source_filename_txt.text(),
                                                  filter='Video files (*.avi *.mpeg *.mp4);;All files (*)',
                                                  options=options)
        if fileName:
            self._source_filename_txt.setText(fileName)


def main():
    app = QApplication(sys.argv)
    config_app = PySoloMainAppWindow()
    config_app.show()
    app.exec_()

if __name__ == '__main__':
    sys.exit(main())
