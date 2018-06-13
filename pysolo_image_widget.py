#!/usr/bin/env python
from datetime import timedelta

import cv2
import numpy as np

from functools import partial

from PyQt5.QtCore import pyqtSlot, Qt, QThread, QObject, pyqtSignal, QRect, QDateTime
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QSlider, QHBoxLayout, QGridLayout, QSpacerItem, QSizePolicy)

from pysolo_video import MovieFile, MonitoredArea, CrossingBeamType


class ImageWidget(QWidget):

    def __init__(self, communication_channels, image_width=640, image_height=640):
        super(ImageWidget, self).__init__()
        self._communication_channels = communication_channels
        self._image_width = image_width
        self._image_height = image_height
        self._movie_file = None
        self._image_frame = None
        self._image_scale = None
        self._movie_acq_time = None
        self._ratio = image_width / image_height
        self._image_update_thread = QThread()
        self._image_update_worker = ImageWidgetUpdateWorker(self._update_image_pixels, self._communication_channels)
        self._opencv_thread = QThread()
        self._opencv_worker = OpenCVWorker(self._draw_lines_on_image, self._communication_channels)
        self._init_ui()
        self._init_event_handlers()
        self._opencv_thread.start()
        self._image_update_thread.start()

    def _init_ui(self):
        self._video_frame = QLabel()
        layout = QVBoxLayout()
        self._video_frame.setMinimumHeight(self._image_height)
        self._video_frame.setMinimumWidth(self._image_width)
        layout.addWidget(self._video_frame)

        self._frame_value_widget = QWidget()
        frame_value_layout = QGridLayout(self._frame_value_widget)
        frame_value_layout.setVerticalSpacing(1)

        current_frame_lbl = QLabel('Current frame:')
        self._current_frame_value_lbl = QLabel('0')
        frame_value_layout.addWidget(current_frame_lbl, 0, 0)
        frame_value_layout.addWidget(self._current_frame_value_lbl, 0, 1)

        frame_acq_lbl = QLabel('Current frame acquisition time:')
        self._current_frame_acq_value_lbl = QLabel('')
        frame_value_layout.addWidget(frame_acq_lbl, 1, 0)
        frame_value_layout.addWidget(self._current_frame_acq_value_lbl, 1, 1)

        self._frame_sld = QSlider(Qt.Horizontal, self)
        frame_value_layout.addWidget(self._frame_sld, 2, 0, 1, 2)
        vertical_spacer = QSpacerItem(10, 1, QSizePolicy.Minimum, QSizePolicy.Expanding)
        frame_value_layout.addItem(vertical_spacer, 3, 0, 1, 2)

        self._frame_value_widget.setVisible(False)
        layout.addWidget(self._frame_value_widget)

        self.setLayout(layout)

    def _init_event_handlers(self):
        self._frame_sld.valueChanged[int].connect(self._update_frame_sld_pos)
        self._communication_channels.video_frame_signal.connect(self._update_frame)
        self._communication_channels.video_frame_time_signal.connect(self._update_frame_sld_pos)
        self._communication_channels.video_loaded_signal.connect(self._set_movie)
        self._communication_channels.clear_video_signal.connect(partial(self._set_movie, None))
        self._communication_channels.maskfile_signal.connect(self._load_and_display_rois)
        self._communication_channels.monitored_area_rois_signal.connect(self._display_rois)
        self._communication_channels.all_monitored_areas_rois_signal.connect(self._display_all_monitored_areas_rois, Qt.QueuedConnection)
        self._communication_channels.tracker_running_signal.connect(self._frame_sld.setDisabled)
        self._communication_channels.fly_coord_pos_signal.connect(self._draw_fly_pos, Qt.QueuedConnection)
        self._communication_channels.video_image_resolution_signal.connect(self._set_movie_resolution)
        self._communication_channels.video_acq_time_signal.connect(self._set_movie_acq_time)

    def _update_frame_sld_pos(self, value, frame_index_param=None, update_frame_image=True):
        self._frame_sld.setValue(value)

        # display frame index
        if frame_index_param is not None:
            frame_index = frame_index_param
        else:
            frame_index = int(value * self._movie_file.get_fps())
        self._current_frame_value_lbl.setText(str(frame_index))

        # display frame acquisition time
        if self._movie_acq_time is not None:
            frame_acq_time = self._movie_acq_time.toPyDateTime() + timedelta(seconds=value)
            self._current_frame_acq_value_lbl.setText(frame_acq_time.strftime('%d-%b-%y %H:%M:%S'))
        elif value > 0:
            hours = (value / 3600)
            mins = (value / 60) % 60
            secs = value % 60
            self._current_frame_acq_value_lbl.setText('%dh:%dm:%ds' % (hours, mins, secs))
        else:
            self._current_frame_acq_value_lbl.setText('')

        if update_frame_image: # check the flag in order to avoid redundant calls
            image_exist, _, frame_image = self._movie_file.update_frame_index(frame_index)
            if image_exist:
                self._set_image(frame_image)

    @pyqtSlot(int, float, np.ndarray)
    def _update_frame(self, frame_index, frame_time_in_seconds, frame_image):
        self._update_frame_sld_pos(frame_time_in_seconds, frame_index_param=frame_index, update_frame_image=False)
        self._set_image(frame_image)

    @pyqtSlot(MovieFile)
    def _set_movie(self, movie_file):
        if movie_file is not None and movie_file.is_opened():
            self._movie_file = movie_file
            self._frame_value_widget.setVisible(True)
            self._frame_sld.setTickPosition(QSlider.TicksBelow)
            self._frame_sld.setTickInterval(self._movie_file.get_end_time_in_seconds() / self._image_width * 10)
            self._frame_sld.setMinimum(0)
            self._frame_sld.setMaximum(int(self._movie_file.get_end_time_in_seconds()))
            self._image_scale = self._movie_file.get_scale()
            self._update_frame_sld_pos(0, update_frame_image=True)
        else:
            self._movie_file = None
            self._frame_value_widget.setVisible(False)
            self._image_frame = None
            self._video_frame.setPixmap(QPixmap.fromImage(QImage()))

    def _set_image(self, image):
        self._image_frame = image
        self._communication_channels.mask_on_signal.emit(False)
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

    @pyqtSlot(QDateTime)
    def _set_movie_acq_time(self, acq_time):
        self._movie_acq_time = acq_time

    @pyqtSlot(str, CrossingBeamType)
    def _load_and_display_rois(self, rois_mask_file, crossing_line):
        if rois_mask_file:
            # toggle the ROIs
            monitored_area = MonitoredArea()
            monitored_area.load_rois(rois_mask_file)
            self._display_rois(monitored_area, crossing_line)
        else:
            self._display_rois(None, None)

    @pyqtSlot(MonitoredArea, CrossingBeamType)
    def _display_rois(self, monitored_area, crossing_line):
        if self._movie_file is None:
            return  # do nothing
        roi_image = self._image_frame.copy()
        if monitored_area:
            color = [0, 255, 100]
            for roi_index, roi in enumerate(monitored_area.ROIS):
                if monitored_area.is_roi_trackable(roi_index):
                    roi_array = np.array(monitored_area.roi_to_poly(roi, self._image_scale))
                    cv2.polylines(roi_image, [roi_array], isClosed=True, color=color)
                    if CrossingBeamType.is_crossing_beam_needed(monitored_area.get_track_type(), crossing_line):
                        mid1, mid2 = monitored_area.get_midline(roi, self._image_scale, conv=int, midline_type=crossing_line)
                        cv2.line(roi_image, mid1, mid2, color=color)
            self._communication_channels.mask_on_signal.emit(True)
        else:
            self._communication_channels.mask_on_signal.emit(False)

        self._update_image_pixels_async(roi_image)

    @pyqtSlot(list, CrossingBeamType)
    def _display_all_monitored_areas_rois(self, monitored_areas, crossing_line):
        if self._movie_file is None:
            return  # do nothing
        roi_image = self._image_frame.copy()
        polys_list = []
        point_pairs_list = []
        color = (0, 255, 100)
        line_thickness = 1

        for monitored_area in monitored_areas:
            for roi_index, roi in enumerate(monitored_area.ROIS):
                if monitored_area.is_roi_trackable(roi_index):
                    roi_array = np.array(monitored_area.roi_to_poly(roi, self._image_scale))
                    polys_list.append(roi_array)
                    if CrossingBeamType.is_crossing_beam_needed(monitored_area.get_track_type(), crossing_line):
                        mid1, mid2 = monitored_area.get_midline(roi, self._image_scale, conv=int, midline_type=crossing_line)
                        point_pairs_list.append((mid1, mid2))

        self._draw_lines_on_image_async(roi_image, polys_list, point_pairs_list, color, line_thickness, None)

        self._communication_channels.mask_on_signal.emit(True)
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
            polys_list = []
            point_pairs_list = []
            color = (255, 10, 0)
            line_thickness = 1
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
                point_pairs_list.append((a, b))
                point_pairs_list.append((c, d))

            self._draw_lines_on_image_async(image_frame, polys_list, point_pairs_list, color, line_thickness, line_type)
            self._update_image_pixels_async(image_frame)

    def _draw_lines_on_image(self, image, polys_list, point_pairs_list, color, thickness, line_type):
        for poly in polys_list:
            cv2.polylines(image, [poly], isClosed=True, color=color)
        for point_pair in point_pairs_list:
            cv2.line(image, point_pair[0], point_pair[1], color=color, thickness=thickness, lineType=line_type)

    def _draw_lines_on_image_async(self, image, polys_list, point_pairs_list, color, thickness, line_type):
        self._opencv_worker.moveToThread(self._opencv_thread)
        self._opencv_worker.start.emit(image, polys_list, point_pairs_list, color, thickness, line_type)


class ImageWidgetUpdateWorker(QObject):

    start = pyqtSignal(np.ndarray)

    def __init__(self, function, communication_channels):
        super(ImageWidgetUpdateWorker, self).__init__()
        self._function = function
        self._communication_channels = communication_channels
        self.start.connect(self.run)

    @pyqtSlot(np.ndarray)
    def run(self, image):
        self._communication_channels.lock.blockSignals(True)
        self._function(image)
        self._communication_channels.lock.blockSignals(False)


class OpenCVWorker(QObject):

    start = pyqtSignal(np.ndarray, list, list, tuple, int, int)

    def __init__(self, function, communication_channels):
        super(OpenCVWorker, self).__init__()
        self._function = function
        self._communication_channels = communication_channels
        self.start.connect(self.run)

    @pyqtSlot(np.ndarray, list, list, tuple, int, int)
    def run(self, image, polys_list, point_pairs_list, color, thickness, line_type):
        self._communication_channels.lock.blockSignals(True)
        self._function(image, polys_list, point_pairs_list, color, thickness, line_type)
        self._communication_channels.lock.blockSignals(False)
