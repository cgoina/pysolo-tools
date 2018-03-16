#!/usr/bin/env python
from functools import partial

import cv2
from PyQt5.QtCore import pyqtSlot, QRect
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout)

from pysolo_video import MovieFile


class ImageWidget(QWidget):

    def __init__(self, parent, communication_channels, image_width=640, image_height=480):
        super(ImageWidget, self).__init__(parent)
        self._image_width = image_width
        self._image_height = image_height
        self._ratio = image_width / image_height
        self._image = QImage()
        self._init_ui()
        self._init_event_handlers(communication_channels)

    def _init_ui(self):
        self._video_frame = QLabel()
        layout = QVBoxLayout()
        self._video_frame.setMinimumHeight(self._image_height)
        self._video_frame.setMinimumWidth(self._image_width)
        layout.addWidget(self._video_frame)
        layout.setGeometry(QRect(0, 0, self._image_width, self._image_height))
        self.setLayout(layout)

    def _init_event_handlers(self, communication_channels):
        communication_channels.video_loaded_signal.connect(self.set_movie)
        communication_channels.clear_video_signal.connect(partial(self.set_movie, None))

    @pyqtSlot(MovieFile)
    def set_movie(self, movie_file):
        self._movie_file = movie_file
        if self._movie_file is not None:
            _, _, image = self._movie_file.get_image()
            self.update_image(image)
        else:
            self._image = QImage()
            self._video_frame.setPixmap(QPixmap.fromImage(self._image))

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
        self._video_frame.setPixmap(QPixmap.fromImage(self._image))
