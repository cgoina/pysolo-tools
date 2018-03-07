#!/usr/bin/env python

import sys

import cv2
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QPoint
from PyQt5.QtGui import QImage, QPainter, QPixmap
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QMainWindow, QHBoxLayout,
                             QLabel, QLineEdit, QGridLayout, QFileDialog, QScrollArea, QVBoxLayout)

from pysolo_video import MovieFile


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
        self._form_widget._video_signal.connect(self._monitor_widget.set_image)


class MonitorWidget(QWidget):
    def __init__(self, parent):
        super(MonitorWidget, self).__init__(parent)
        self._image = QImage()
        self._initUI()

    def _initUI(self):
        self.video_frame = QLabel()
        layout = QVBoxLayout()
        layout.addWidget(self.video_frame)
        self.setLayout(layout)

    @pyqtSlot(QImage)
    def set_image(self, image):
        self._image = image
        pixmap = QPixmap.fromImage(image)
        self.video_frame.setPixmap(pixmap)


class FormWidget(QWidget):
    _video_signal = pyqtSignal(QImage)

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
            self._movie_file = MovieFile(fileName)
            _, _, image = self._movie_file.get_image()
            color_swapped_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            color_swapped_image = cv2.resize(color_swapped_image, (640, 640), interpolation=cv2.INTER_AREA)

            monitored_image = QImage(color_swapped_image,
                                     color_swapped_image.shape[0],
                                     color_swapped_image.shape[1],
                                     QImage.Format_RGB888)
            self._video_signal.emit(monitored_image)


def main():
    app = QApplication(sys.argv)
    config_app = PySoloMainAppWindow()
    config_app.show()
    app.exec_()

if __name__ == '__main__':
    sys.exit(main())
