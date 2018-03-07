#!/usr/bin/env python

import numpy as np
import sys

import cv2
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QPoint, QRect
from PyQt5.QtGui import QImage, QPainter, QPixmap
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QMainWindow, QHBoxLayout,
                             QLabel, QLineEdit, QGridLayout, QFileDialog, QScrollArea, QVBoxLayout, QSpinBox, QComboBox)

from pysolo_video import MovieFile


class PySoloMainAppWindow(QMainWindow):
    video_loaded_signal = pyqtSignal(MovieFile)

    def __init__(self, parent=None):
        super(PySoloMainAppWindow, self).__init__(parent)
        self._monitor_widget = MonitorWidget(self)
        self._form_widget = FormWidget(self, self.video_loaded_signal)
        mainWidget = QWidget()
        layout = QHBoxLayout(mainWidget)
        layout.addWidget(self._monitor_widget)
        layout.addWidget(self._form_widget)
        self.setCentralWidget(mainWidget)
        self.video_loaded_signal.connect(self._monitor_widget.set_movie)


class MonitorWidget(QWidget):

    def __init__(self, parent, image_width=640, image_height=480):
        super(MonitorWidget, self).__init__(parent)
        self._image_width = image_width
        self._image_height = image_height
        self._ratio = image_width / image_height
        self._image = QImage()
        self._initUI()

    def _initUI(self):
        self.video_frame = QLabel()
        layout = QVBoxLayout()
        self.video_frame.setMinimumHeight(self._image_height)
        self.video_frame.setMinimumWidth(self._image_width)
        layout.addWidget(self.video_frame)
        layout.setGeometry(QRect(0, 0, self._image_width, self._image_height))
        self.setLayout(layout)

    @pyqtSlot(MovieFile)
    def set_movie(self, movie_file):
        self._movie_file = movie_file
        _, _, image = self._movie_file.get_image()
        self.update_image(image)

    def update_image(self, image):
        color_swapped_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        scalef = self._image_height / image.shape[1]
        image_ratio = image.shape[0] / image.shape[1]
        color_swapped_image = cv2.resize(color_swapped_image,
                                         (int(color_swapped_image.shape[0] * scalef * self._ratio),
                                          int(color_swapped_image.shape[1] * scalef * self._ratio / image_ratio)),
                                         interpolation=cv2.INTER_AREA)
        self._image = QImage(color_swapped_image,
                             color_swapped_image.shape[0],
                             color_swapped_image.shape[1],
                             QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(self._image)
        self.video_frame.setPixmap(pixmap)


class CommonOptionsFormWidget(QWidget):

    def __init__(self, parent, video_loaded_signal, max_monitored_areas=64):
        super(CommonOptionsFormWidget, self).__init__(parent)
        self.video_loaded_signal = video_loaded_signal
        self._max_monitored_areas = max_monitored_areas
        self._initUI()

    def _initUI(self):
        layout = QGridLayout()

        current_layout_row = 0
        # source file name widgets
        self._source_filename_txt = QLineEdit()
        self._source_filename_txt.setDisabled(True)
        source_filename_lbl = QLabel("Select source file")
        source_filename_btn = QPushButton("Open...")
        # add the source filename control to the layout
        layout.addWidget(source_filename_lbl, current_layout_row, 0)
        current_layout_row += 1
        layout.addWidget(self._source_filename_txt, current_layout_row, 0)
        layout.addWidget(source_filename_btn, current_layout_row, 1)
        current_layout_row += 1
        # source file name event handlers
        source_filename_btn.clicked.connect(self._select_source_file)

        # results directory widgets
        self._results_dir_txt = QLineEdit()
        self._results_dir_txt.setDisabled(True)
        results_dir_lbl = QLabel("Select results directory")
        results_dir_btn = QPushButton("Select...")
        # add the source filename control to the layout
        layout.addWidget(results_dir_lbl, current_layout_row, 0)
        current_layout_row += 1
        layout.addWidget(self._results_dir_txt, current_layout_row, 0)
        layout.addWidget(results_dir_btn, current_layout_row, 1)
        current_layout_row += 1
        # results directory event handlers
        results_dir_btn.clicked.connect(self._select_results_dir)

        # number of monitored regions widgets
        self._n_monitored_areas_spinner = QSpinBox()
        self._n_monitored_areas_spinner.setMinimum(0)
        self._n_monitored_areas_spinner.setMaximum(self._max_monitored_areas)
        n_monitored_areas_lbl = QLabel("Number of monitored regions")
        # add the number of monitored regions control to the layout
        layout.addWidget(n_monitored_areas_lbl, current_layout_row, 0)
        current_layout_row += 1
        layout.addWidget(self._n_monitored_areas_spinner, current_layout_row, 0)
        current_layout_row += 1
        # number of monitored regions event handlers
        self._n_monitored_areas_spinner.valueChanged.connect(self._update_number_of_regions)

        # current region widgets
        self.selected_region = QComboBox()
        self.selected_region.setDisabled(True)
        selected_region_lbl = QLabel("Select region")
        # add selected region control to the layout
        layout.addWidget(selected_region_lbl, current_layout_row, 0)
        current_layout_row += 1
        layout.addWidget(self.selected_region, current_layout_row, 0)
        current_layout_row += 1
        # current region event handlers
        self.selected_region.currentIndexChanged.connect(self._update_selected_region)
        # set the layout
        self.setLayout(layout)

    def _select_source_file(self):
        options = QFileDialog.Options(QFileDialog.DontUseNativeDialog)
        fileName, _ = QFileDialog.getOpenFileName(self, "Select source file",
                                                  self._source_filename_txt.text(),
                                                  filter='Video files (*.avi *.mpeg *.mp4);;All files (*)',
                                                  options=options)
        if fileName:
            self._source_filename_txt.setText(fileName)
            self.video_loaded_signal.emit(MovieFile(fileName))

    def _select_results_dir(self):
        options = QFileDialog.Options(QFileDialog.DontUseNativeDialog | QFileDialog.ShowDirsOnly)
        resultsDirName = QFileDialog.getExistingDirectory(self, "Select results directory",
                                                          self._results_dir_txt.text(),
                                                          options=options)
        if resultsDirName:
            self._results_dir_txt.setText(resultsDirName)

    def _update_number_of_regions(self):
        new_regions_counter = self._n_monitored_areas_spinner.value()
        # update selected region control
        if new_regions_counter == 0:
            n_regions = self.selected_region.count()
            for r in range(n_regions):
                self.selected_region.removeItem(r)
            self.selected_region.setDisabled(True)
        else:
            n_regions = self.selected_region.count()
            for r in range(new_regions_counter, n_regions):
                self.selected_region.removeItem(r)
            for r in range(n_regions, new_regions_counter):
                self.selected_region.addItem('Region %d' % (r + 1), r)
            self.selected_region.setDisabled(False)

    def _update_selected_region(self):
        pass


class FormWidget(QWidget):

    def __init__(self, parent, video_loaded_signal):
        super(FormWidget, self).__init__(parent)
        self._initUI(video_loaded_signal)

    def _initUI(self, video_loaded_signal):
        layout = QGridLayout()
        commonOptionsWidget = CommonOptionsFormWidget(self, video_loaded_signal)
        layout.addWidget(commonOptionsWidget, 0, 0)
        self.setLayout(layout)


def main():
    app = QApplication(sys.argv)
    config_app = PySoloMainAppWindow()
    config_app.show()
    app.exec_()

if __name__ == '__main__':
    sys.exit(main())
