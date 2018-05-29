#!/usr/bin/env python
import cv2
import numpy as np

from functools import partial

from PyQt5.QtCore import pyqtSlot, Qt, QThread, QObject, pyqtSignal, QRect
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QSlider, QHBoxLayout)

from pysolo_video import MovieFile, MonitoredArea


class ImageWidget(QWidget):

    def __init__(self, communication_channels, image_width=640, image_height=640):
        super(ImageWidget, self).__init__()
        self._communication_channels = communication_channels
        self._image_width = image_width
        self._image_height = image_height
        self._movie_file = None
        self._image_frame = None
        self._image_scale = None
        self._show_rois = False
        self._ratio = image_width / image_height
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

        self._frame_sld_widget = QWidget()

        frame_value_widget = QWidget()
        frame_value_layout = QHBoxLayout(frame_value_widget)

        current_frame_lbl = QLabel('Current frame:')

        self._current_frame_value_lbl = QLabel('0')

        frame_value_layout.addWidget(current_frame_lbl)
        frame_value_layout.addWidget(self._current_frame_value_lbl)

        frame_sld_layout = QVBoxLayout(self._frame_sld_widget)

        self._frame_sld = QSlider(Qt.Horizontal, self)

        frame_sld_layout.addWidget(frame_value_widget)
        frame_sld_layout.addWidget(self._frame_sld)

        self._frame_sld_widget.setVisible(False)
        layout.addWidget(self._frame_sld_widget)

        self.setLayout(layout)

    def _init_event_handlers(self):
        self._frame_sld.valueChanged[int].connect(self._update_frame_sld_pos)
        self._communication_channels.video_frame_pos_signal.connect(self._update_frame_pos_in_secs)
        self._communication_channels.video_loaded_signal.connect(self._set_movie)
        self._communication_channels.clear_video_signal.connect(partial(self._set_movie, None))
        self._communication_channels.maskfile_signal.connect(self._load_and_display_rois)
        self._communication_channels.monitored_area_rois_signal.connect(self._display_rois)
        self._communication_channels.all_monitored_areas_rois_signal.connect(self._display_all_monitored_areas_rois)
        self._communication_channels.tracker_running_signal.connect(self._frame_sld.setDisabled)
        self._communication_channels.fly_coord_pos_signal.connect(self._draw_fly_pos)
        self._communication_channels.video_image_resolution_signal.connect(self._set_movie_resolution)

    def _update_frame_sld_pos(self, value, update_frame=True):
        self._frame_sld.setValue(value)
        if update_frame: # check the flag in order to avoid recursion
            self._update_frame_pos_in_secs(value)

    @pyqtSlot(float, str)
    def _update_frame_pos_in_secs(self, frame_pos, unit='seconds'):
        if self._movie_file is not None:
            if unit == 'frames':
                frame = frame_pos
                sld_pos = int(self._movie_file.get_frame_time(frame_pos))
            else:
                # treat is seconds
                frame = int(frame_pos * self._movie_file.get_fps())
                sld_pos = frame_pos
            self._update_frame_sld_pos(sld_pos, update_frame=False)
            image_exist, _, image = self._movie_file.update_frame_index(frame)
            if image_exist:
                self._current_frame_value_lbl.setText(str(sld_pos))
                self._set_image(image)

    @pyqtSlot(MovieFile)
    def _set_movie(self, movie_file):
        if movie_file is not None and movie_file.is_opened():
            self._movie_file = movie_file
            self._frame_sld_widget.setVisible(True)
            self._frame_sld.setTickPosition(QSlider.TicksBelow)
            self._frame_sld.setTickInterval(self._movie_file.get_end_time_in_seconds() / self._image_width * 10)
            self._frame_sld.setMinimum(0)
            self._frame_sld.setMaximum(int(self._movie_file.get_end_time_in_seconds()))
            self._image_scale = self._movie_file.get_scale()
            image_found, _, image = self._movie_file.get_image()
            if image_found:
                self._set_image(image)
        else:
            self._movie_file = None
            self._frame_sld_widget.setVisible(False)
            self._image_frame = None
            self._video_frame.setPixmap(QPixmap.fromImage(QImage()))
        self._communication_channels.video_frame_pos_signal.emit(0, 'frames')

    def _set_image(self, image):
        self._image_frame = image
        self._show_rois = False
        self._update_image_pixels_async(self._image_frame)

    def _update_image_pixels(self, image):
        color_swapped_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        vert_scalef = self._image_height / image.shape[0]
        horz_scalef = self._image_width / image.shape[1]
        image_ratio = image.shape[1] / image.shape[0]
        color_swapped_image = cv2.resize(color_swapped_image,
                                         (int(color_swapped_image.shape[1] * horz_scalef * self._ratio),
                                          int(color_swapped_image.shape[0] * vert_scalef * self._ratio / image_ratio)),
                                         interpolation=cv2.INTER_AREA)
        image = QImage(color_swapped_image,
                             color_swapped_image.shape[1],
                             color_swapped_image.shape[0],
                             QImage.Format_RGB888)
        self._video_frame.setPixmap(QPixmap.fromImage(image))

    def _update_image_pixels_async(self, image):
        self._image_update_worker.moveToThread(self._image_update_thread)
        self._image_update_worker.start.emit(image)

    @pyqtSlot(int, int)
    def _set_movie_resolution(self, width, height):
        if self._movie_file is not None:
            self._movie_file.set_resolution(width, height)
            self._image_scale = self._movie_file.get_scale()

    @pyqtSlot(str)
    def _load_and_display_rois(self, rois_mask_file):
        if rois_mask_file and not self._show_rois:
            monitored_area = MonitoredArea()
            monitored_area.load_rois(rois_mask_file)
            self._display_rois(monitored_area)
        else:
            self._display_rois(None)

    @pyqtSlot(MonitoredArea)
    def _display_rois(self, monitored_area):
        if self._movie_file is None:
            return  # do nothing
        roi_image = self._image_frame.copy()
        if monitored_area:
            color = [255, 0, 0]
            for roi_index, roi in enumerate(monitored_area.ROIS):
                if monitored_area.is_roi_trackable(roi_index):
                    roi_array = np.array(monitored_area.roi_to_poly(roi, self._image_scale))
                    cv2.polylines(roi_image, [roi_array], isClosed=True, color=color)
                    mid1, mid2 = monitored_area.get_midline(roi, self._image_scale, conv=int)
                    cv2.line(roi_image, mid1, mid2, color=color)
            self._show_rois = True
        else:
            self._show_rois = False
        self._update_image_pixels_async(roi_image)

    @pyqtSlot(list)
    def _display_all_monitored_areas_rois(self, monitored_areas):
        if self._movie_file is None:
            return  # do nothing
        roi_image = self._image_frame.copy()
        color = [255, 0, 0]
        for monitored_area in monitored_areas:
            for roi_index, roi in enumerate(monitored_area.ROIS):
                if monitored_area.is_roi_trackable(roi_index):
                    roi_array = np.array(monitored_area.roi_to_poly(roi, self._image_scale))
                    cv2.polylines(roi_image, [roi_array], isClosed=True, color=color)
                    mid1, mid2 = monitored_area.get_midline(roi, self._image_scale, conv=int)
                    cv2.line(roi_image, mid1, mid2, color=color)
        self._show_rois = True
        self._update_image_pixels_async(roi_image)

    @pyqtSlot(list)
    def _draw_fly_pos(self, fly_coords):
        """
        Draws a cross at each position from the fly_coords list
        :param fly_coords: list of fly coordinates
        :return:
        """
        if self._image_frame is not None:
            image_frame = self._image_frame
            color = (255, 0, 0)
            width = 1
            line_type = cv2.LINE_AA

            scalef = self._image_height / image_frame.shape[1]
            image_ratio = image_frame.shape[0] / image_frame.shape[1]
            delta_x = 3 / scalef / self._ratio
            delta_y = 3 / scalef / self._ratio * image_ratio

            for fly_coord in fly_coords:
                # draw the position of the fly
                x = fly_coord[0]
                y = fly_coord[1]
                a = (int(x), int(y - delta_y))
                b = (int(x), int(y + delta_y))
                c = (int(x - delta_x), int(y))
                d = (int(x + delta_x), int(y))
                cv2.line(image_frame, a, b, color, width, line_type, 0)
                cv2.line(image_frame, c, d, color, width, line_type, 0)

            self._update_image_pixels_async(image_frame)


class ImageWidgetUpdateWorker(QObject):

    start = pyqtSignal(np.ndarray)

    def __init__(self, function):
        super(ImageWidgetUpdateWorker, self).__init__()
        self._function = function
        self.start.connect(self.run)

    @pyqtSlot(np.ndarray)
    def run(self, image):
        self._function(image)
