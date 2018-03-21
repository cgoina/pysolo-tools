#!/usr/bin/env python
import cv2
import numpy as np

from functools import partial

from PyQt5.QtCore import pyqtSlot, Qt, QThread, QObject, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QSlider)

from pysolo_video import MovieFile, MonitoredArea


class ImageWidget(QWidget):

    def __init__(self, parent, communication_channels, image_width=540, image_height=400):
        super(ImageWidget, self).__init__(parent)
        self._communication_channels = communication_channels
        self._image_width = image_width
        self._image_height = image_height
        self._movie_file = None
        self._image_frame = None
        self._image_scale = None
        self._ratio = image_width / image_height
        self._image = QImage()
        self._image_update_thread = QThread()
        self._image_update_worker = ImageWidgetUpdateWorker(self._update_image_pixels)
        self._init_ui()
        self._init_event_handlers()
        self._image_update_thread.start()

    def _init_ui(self):
        self._video_frame = QLabel()
        layout = QVBoxLayout()
        self._video_frame.setMinimumHeight(self._image_height)
        self._video_frame.setMinimumWidth(self._image_width)
        layout.addWidget(self._video_frame)

        self._frame_sld = QSlider(Qt.Horizontal, self)
        self._frame_sld.setTickPosition(QSlider.TicksBelow)
        self._frame_sld.setTickInterval(5)
        self._frame_sld.setVisible(False)
        layout.addWidget(self._frame_sld)

        self.setLayout(layout)

    def _init_event_handlers(self):
        self._frame_sld.valueChanged[int].connect(partial(self._update_frame_pos_in_secs, unit='seconds'))
        self._communication_channels.video_frame_pos_signal.connect(self._update_frame_pos_in_secs)
        self._communication_channels.video_loaded_signal.connect(self._set_movie)
        self._communication_channels.clear_video_signal.connect(partial(self._set_movie, None))
        self._communication_channels.maskfile_signal.connect(self._load_and_display_rois)
        self._communication_channels.monitored_area_rois_signal.connect(self._display_rois)
        self._communication_channels.tracker_running_signal.connect(self._frame_sld.setDisabled)
        self._communication_channels.fly_coord_pos_signal.connect(self._draw_fly_pos)

    @pyqtSlot(float, str)
    def _update_frame_pos_in_secs(self, frame_pos, unit='seconds'):
        if self._movie_file is not None:
            if unit == 'frames':
                frame = frame_pos
                sld_pos = int(frame_pos / self._movie_file.get_fps())
            else:
                # treat is seconds
                frame = int(frame_pos * self._movie_file.get_fps())
                sld_pos = frame_pos
            self._frame_sld.setValue(sld_pos)
            image_exist, _, image = self._movie_file.update_frame_index(frame)
            if image_exist:
                self._set_image(image)

    @pyqtSlot(MovieFile)
    def _set_movie(self, movie_file):
        self._movie_file = movie_file
        if self._movie_file is not None:
            self._frame_sld.setVisible(True)
            self._image_scale = self._movie_file.get_scale()
            image_found, _, image = self._movie_file.get_image()
            if image_found:
                self._set_image(image)
                self._frame_sld.setMinimum(movie_file.get_start_time_in_seconds())
                self._frame_sld.setMaximum(movie_file.get_end_time_in_seconds())
        else:
            self._frame_sld.setVisible(False)
            self._image_frame = None
            self._image = QImage()
            self._video_frame.setPixmap(QPixmap.fromImage(self._image))

    def _set_image(self, image):
        self._image_frame = image
        self._update_image_pixels_async(self._image_frame)

    def _update_image_pixels(self, image):
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

    def _update_image_pixels_async(self, image):
        self._image_update_worker.moveToThread(self._image_update_thread)
        self._image_update_worker.start.emit(image)

    @pyqtSlot(str)
    def _load_and_display_rois(self, rois_mask_file):
        monitored_area = MonitoredArea()
        monitored_area.load_rois(rois_mask_file)
        self._display_rois(monitored_area)

    @pyqtSlot(MonitoredArea)
    def _display_rois(self, monitored_area_rois):
        if self._movie_file is None:
            return  # do nothing
        roi_image = np.zeros(self._image_frame.shape, np.uint8)
        for roi in monitored_area_rois.ROIS:
            roi_array = np.array(monitored_area_rois.roi_to_poly(roi, self._image_scale))
            cv2.polylines(roi_image, [roi_array], isClosed=True, color=[0, 255, 255])
        overlay = cv2.bitwise_xor(self._image_frame, roi_image)
        self._update_image_pixels_async(overlay)

    @pyqtSlot(float, float)
    def _draw_fly_pos(self, x, y):
        if self._image_frame is not None:
            # draw the position of the fly
            color = (255, 0, 255)
            width = 1
            line_type = cv2.LINE_AA
            scalef = self._image_scale if self._image_scale is not None else (1., 1.)
            a = (int(x), int(y - 3 * scalef[1]))
            b = (int(x), int(y + 3 * scalef[1]))
            c = (int(x - 3 * scalef[0]), int(y))
            d = (int(x + 3 * scalef[0]), int(y))

            cv2.line(self._image_frame, a, b, color, width, line_type, 0)
            cv2.line(self._image_frame, c, d, color, width, line_type, 0)
            self._update_image_pixels_async(self._image_frame)


class ImageWidgetUpdateWorker(QObject):

    start = pyqtSignal(np.ndarray)

    def __init__(self, function):
        super(ImageWidgetUpdateWorker, self).__init__()
        self._function = function
        self.start.connect(self.run)

    @pyqtSlot(np.ndarray)
    def run(self, image):
        self._function(image)
