#!/usr/bin/env python
import re
import threading
from functools import partial
from pathlib import Path

import os
from PyQt5.QtCore import pyqtSlot, Qt, QDateTime, QObject, QTimer, QTime, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QPushButton, QHBoxLayout,
                             QLabel, QLineEdit, QGridLayout, QFileDialog, QVBoxLayout, QSpinBox, QComboBox,
                             QGroupBox, QCheckBox, QScrollArea, QDateTimeEdit, QMessageBox, QTextEdit)

from pysolo_config import ConfigOptions, MonitoredAreaOptions
from pysolo_video import (MovieFile, CrossingBeamType, TrackingType, process_image_frames, prepare_monitored_areas)


class CommonOptionsFormWidget(QWidget):

    def __init__(self, communication_channels, config, max_monitored_areas=100):
        super(CommonOptionsFormWidget, self).__init__()
        self._communication_channels = communication_channels
        self._config = config
        self._max_monitored_areas = max_monitored_areas
        self._init_ui()
        self._init_event_handlers()

    def _init_ui(self):
        group_layout = QGridLayout()

        current_layout_row = 0
        # source file name widgets
        self._source_filename_txt = QLineEdit()
        self._source_filename_txt.setDisabled(True)
        self._source_filename_btn = QPushButton('Open...')
        self._source_filename_btn.setFixedSize(75, 32)
        # add the source filename control to the layout
        group_layout.addWidget(QLabel('Select source file'), current_layout_row, 0, 1, 2)
        current_layout_row += 1
        group_layout.addWidget(self._source_filename_txt, current_layout_row, 0, 1, 4)
        group_layout.addWidget(self._source_filename_btn, current_layout_row, 4, 1, 1)
        current_layout_row += 1

        # acquisition time
        group_layout.addWidget(QLabel('Acquisition time'), current_layout_row, 0, 1, 2)
        current_layout_row += 1
        self._acq_time_dt = QDateTimeEdit()
        self._acq_time_dt.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
        group_layout.addWidget(self._acq_time_dt, current_layout_row, 0, 1, 2)
        current_layout_row += 1

        # results directory widgets
        self._results_dir_txt = QLineEdit()
        self._results_dir_txt.setDisabled(True)
        self._results_dir_btn = QPushButton('Select...')
        # add the source filename control to the layout
        group_layout.addWidget(QLabel('Select results directory'), current_layout_row, 0, 1, 2)
        current_layout_row += 1
        group_layout.addWidget(self._results_dir_txt, current_layout_row, 0, 1, 4)
        group_layout.addWidget(self._results_dir_btn, current_layout_row, 4, 1, 1)
        current_layout_row += 1
        # size
        group_layout.addWidget(QLabel('Size (Width x Height)'), current_layout_row, 0, 1, 2)
        group_layout.addWidget(QLabel('Monitored Areas Summary'), current_layout_row, 2, 1, 2, alignment=Qt.AlignLeft)
        current_layout_row += 1
        self._width_box = QSpinBox()
        self._width_box.setRange(0, 100000)
        self._height_box = QSpinBox()
        self._height_box.setRange(0, 100000)
        group_layout.addWidget(self._width_box, current_layout_row, 0, 1, 1)
        group_layout.addWidget(self._height_box, current_layout_row, 1, 1, 1)
        group_layout.addWidget(ConfigDisplayWidget(self._communication_channels, self._config), current_layout_row, 2,
                               6, 2)
        current_layout_row += 1

        # number of monitored regions widgets
        self._n_monitored_areas_box = QSpinBox()
        self._n_monitored_areas_box.setMinimum(0)
        self._n_monitored_areas_box.setMaximum(self._max_monitored_areas)
        # add the number of monitored regions control to the layout
        group_layout.addWidget(QLabel('Number of monitored areas'), current_layout_row, 0, 1, 2)
        current_layout_row += 1
        group_layout.addWidget(self._n_monitored_areas_box, current_layout_row, 0, 1, 1)
        current_layout_row += 1
        # current region widgets
        self._selected_area_choice = QComboBox()
        self._selected_area_choice.setDisabled(True)
        # add selected region control to the layout
        group_layout.addWidget(QLabel('Select area'), current_layout_row, 0, 1, 2)
        current_layout_row += 1
        group_layout.addWidget(self._selected_area_choice, current_layout_row, 0)
        current_layout_row += 1
        # set the layout
        groupBox = QGroupBox()
        groupBox.setLayout(group_layout)
        layout = QVBoxLayout()
        layout.addWidget(groupBox)
        self.setLayout(layout)

    def _init_event_handlers(self):
        # source file name event handlers
        self._source_filename_btn.clicked.connect(self._select_source_file)
        self._acq_time_dt.dateTimeChanged.connect(self._update_acq_time)
        # results directory event handlers
        self._results_dir_btn.clicked.connect(self._select_results_dir)
        # image size controls event handlers
        self._width_box.valueChanged.connect(self._update_image_width)
        self._height_box.valueChanged.connect(self._update_image_height)
        # number of monitored areas control event handlers
        self._n_monitored_areas_box.valueChanged.connect(self._update_number_of_areas)
        # current selected area control event handlers
        self._selected_area_choice.currentIndexChanged.connect(self._update_selected_area)
        # update config
        self._communication_channels.config_signal.connect(self._update_config_options)
        self._communication_channels.tracker_running_signal.connect(self.setDisabled)

    def _select_source_file(self):
        options = QFileDialog.Options(QFileDialog.DontUseNativeDialog)
        filename, _ = QFileDialog.getOpenFileName(self, 'Select source file',
                                                  self._source_filename_txt.text(),
                                                  filter='Video files (*.avi *.mpeg *.mp4);;All files (*)',
                                                  options=options)
        if filename:
            movie_file = self._update_source_filename(filename)
            if movie_file:
                # update acquisition time from the file name which should contain the start of the acquisition
                acq_time_group = re.search('SR(\d{8}T\d{6})_movie.*', filename)
                if acq_time_group is not None:
                    self._update_acq_time(QDateTime.fromString(acq_time_group.group(1), 'yyyyMMddTHHmmss'))
                else:
                    movie_file_path = Path(filename)
                    movie_file_ts_millis = movie_file_path.stat().st_mtime * 1000
                    self._update_acq_time(QDateTime.fromMSecsSinceEpoch(int(movie_file_ts_millis)))
                # update image size
                image_size = movie_file.get_size()
                self._update_image_width(image_size[0])
                self._update_image_height(image_size[1])

    def _update_source_filename(self, filename):
        movie_file = None

        if filename:
            movie_file = MovieFile(filename)
            self._source_filename_txt.setText(filename)
            if not movie_file.is_opened():
                QMessageBox.critical(self, 'Movie file error', 'Error opening %s' % filename)

        if movie_file is not None and movie_file.is_opened():
            self._config.set_source(filename)
            movie_file.set_resolution(self._config.get_image_width(), self._config.get_image_height())
            self._communication_channels.video_loaded_signal.emit(movie_file)
            return movie_file
        else:
            self._config.set_source(None)
            self._source_filename_txt.setText('')
            self._communication_channels.clear_video_signal.emit()
            return None

    def _update_acq_time(self, acq_time):
        self._config.set_acq_time_from_str(acq_time.toString('yyyy-MM-dd HH:mm:ss'))
        self._acq_time_dt.setDateTime(acq_time)

    def _select_results_dir(self):
        options = QFileDialog.Options(QFileDialog.DontUseNativeDialog | QFileDialog.ShowDirsOnly)
        results_dir_name = QFileDialog.getExistingDirectory(self, 'Select results directory',
                                                            self._results_dir_txt.text(),
                                                            options=options)
        if results_dir_name:
            self._update_results_dir(results_dir_name)

    def _update_results_dir(self, results_dir_name):
        if results_dir_name:
            self._results_dir_txt.setText(results_dir_name)
            self._config.set_data_folder(results_dir_name)
        else:
            self._results_dir_txt.setText('')
            self._config.set_data_folder(None)

    def _update_image_width(self, val):
        self._config.set_image_width(val)
        self._width_box.setValue(val)
        self._communication_channels.video_image_resolution_signal.emit(self._config.get_image_width(),
                                                                        self._config.get_image_height())

    def _update_image_height(self, val):
        self._config.set_image_height(val)
        self._height_box.setValue(val)
        self._communication_channels.video_image_resolution_signal.emit(self._config.get_image_width(),
                                                                        self._config.get_image_height())

    def _update_number_of_areas(self, new_areas_counter):
        # update the config
        self._config.set_monitored_areas_count(new_areas_counter)
        # update selected region control
        if new_areas_counter == 0:
            n_areas = self._selected_area_choice.count()
            for a in range(n_areas):
                self._selected_area_choice.removeItem(0)
            self._selected_area_choice.setDisabled(True)
            self._communication_channels.selected_area_signal.emit(-1)
        else:
            n_areas = self._selected_area_choice.count()
            if n_areas > new_areas_counter:
                for a in range(new_areas_counter, n_areas):
                    self._selected_area_choice.removeItem(a)
            else:
                for a in range(n_areas, new_areas_counter):
                    self._selected_area_choice.addItem('Area %d' % (a + 1), a)
            self._selected_area_choice.setDisabled(False)
            if n_areas == 0:
                self._communication_channels.selected_area_signal.emit(0)
            elif self._selected_area_choice.currentData() >= new_areas_counter:
                self._communication_channels.selected_area_signal.emit(new_areas_counter - 1)
        self._communication_channels.refresh_display_signal.emit()

    def _update_selected_area(self, area_index):
        selected_monitored_area = None
        if area_index >= 0:
            selected_monitored_area = self._config.get_monitored_area(area_index)
        if selected_monitored_area is not None:
            self._communication_channels.monitored_area_options_signal.emit(selected_monitored_area)
        else:
            self._communication_channels.monitored_area_options_signal.emit(MonitoredAreaOptions())

    @pyqtSlot(ConfigOptions)
    def _update_config_options(self, new_config):
        self._config = new_config
        # update the video source
        self._update_source_filename(self._config.get_source())
        # update acquisition time
        acq_time_as_str = self._config.get_acq_time_as_str()
        if acq_time_as_str:
            self._update_acq_time(QDateTime.fromString(acq_time_as_str, 'yyyy-MM-dd HH:mm:ss'))
        else:
            self._update_acq_time(QDateTime.currentDateTime())
        # update the results folder
        self._update_results_dir(self._config.get_data_folder())
        # update the size
        self._update_image_width(self._config.get_image_width())
        self._update_image_height(self._config.get_image_height())
        # update the number of monitored areas
        # set both the value in the controller and call the event handler in case it's not fired
        self._n_monitored_areas_box.setValue(self._config.get_monitored_areas_count())
        self._update_number_of_areas(self._config.get_monitored_areas_count())
        # update selected area
        # set both the value in the controller and call the event handler in case it's not fired
        self._selected_area_choice.setCurrentIndex(0)
        self._update_selected_area(0)


class ConfigDisplayWidget(QWidget):

    def __init__(self, communication_channels, config):
        super(ConfigDisplayWidget, self).__init__()
        self._communication_channels = communication_channels
        self._config = config
        self._init_ui()
        self._init_event_handlers()

    def _init_ui(self):
        layout = QVBoxLayout()

        self._monitored_areas_summary = QTextEdit()
        self._monitored_areas_summary.setReadOnly(True)
        layout.addWidget(self._monitored_areas_summary)

        self.setLayout(layout)

    def _init_event_handlers(self):
        # update config
        self._communication_channels.config_signal.connect(self._update_config_options)
        self._communication_channels.refresh_display_signal.connect(self._refresh_display)

    @pyqtSlot(ConfigOptions)
    def _update_config_options(self, new_config):
        self._config = new_config
        self._refresh_display()

    def _refresh_display(self):
        buffer = ''
        for ma_index, ma in enumerate(self._config.get_monitored_areas()):
            buffer += 'Area ' + str(ma_index + 1) + ':\n'
            buffer += self._indent('Mask: ' + self._get_maskfile(ma) + '\n')
            buffer += self._indent('Track type: ' + self._get_track_type_desc(ma) + '\n')
            buffer += self._indent(
                'Aggregation interval: %d %s\n' % (ma.get_aggregation_interval(), ma.get_aggregation_interval_units())
            )
            buffer += self._indent('ROI filter: ' + ma.get_rois_filter_as_str() + '\n')
        self._monitored_areas_summary.setPlainText(buffer)

    def _indent(self, text):
        return '    ' + text

    def _get_maskfile(self, ma):
        if ma.get_maskfile():
            return os.path.basename(ma.get_maskfile())
        else:
            return '?????'

    def _get_track_type_desc(self, ma):
        if ma.get_track_flag():
            if ma.get_track_type() == 0:
                return 'distance'
            elif ma.get_track_type() == 1:
                return 'crossings'
            elif ma.get_track_type() == 2:
                return 'position'
            else:
                raise ValueError('Invalid track type option: %d' % ma.get_track_type())
        else:
            return 'disabled'


class MonitoredAreaFormWidget(QWidget):

    def __init__(self, communication_channels):
        super(MonitoredAreaFormWidget, self).__init__()
        self._communication_channels = communication_channels
        self._monitored_area = MonitoredAreaOptions()
        self._init_ui()
        self._init_event_handlers()

    def _init_ui(self):
        group_layout = QGridLayout()

        current_layout_row = 0
        # source file name widgets
        self._mask_filename_txt = QLineEdit()
        self._mask_filename_txt.setDisabled(True)
        self._mask_filename_btn = QPushButton('Open...')
        # add the mask filename control to the layout
        group_layout.addWidget(QLabel('Select mask file'), current_layout_row, 0, 1, 1)
        current_layout_row += 1
        group_layout.addWidget(self._mask_filename_txt, current_layout_row, 0, 1, 4)
        group_layout.addWidget(self._mask_filename_btn, current_layout_row, 4, 1, 1)
        current_layout_row += 1

        # track type
        self._track_type_choice = QComboBox()
        self._track_type_choice.addItem('Distance', TrackingType.distance)
        self._track_type_choice.addItem('Crossover', TrackingType.beam_crossings)
        self._track_type_choice.addItem('Position', TrackingType.position)

        # add track type control to the layout
        group_layout.addWidget(QLabel('Select Track Type'), current_layout_row, 0, 1, 1)
        current_layout_row += 1
        group_layout.addWidget(self._track_type_choice, current_layout_row, 0, 1, 1)
        current_layout_row += 1

        # track flag
        self._track_check = QCheckBox()
        track_flag_widget = QWidget()
        track_flag_layout = QHBoxLayout(track_flag_widget)
        track_flag_layout.addWidget(self._track_check)
        track_flag_layout.addWidget(QLabel('Monitor area'), Qt.AlignLeft)
        group_layout.addWidget(track_flag_widget, current_layout_row, 0, 1, 1)

        # sleep deprivation flag
        self._sleep_deprivation_check = QCheckBox()
        sleep_deprivationwidget = QWidget()
        sleep_deprivation_layout = QHBoxLayout(sleep_deprivationwidget)
        sleep_deprivation_layout.addWidget(self._sleep_deprivation_check)
        sleep_deprivation_layout.addWidget(QLabel('Sleep deprivation'), Qt.AlignLeft)
        group_layout.addWidget(sleep_deprivationwidget, current_layout_row, 1, 1, 1)
        current_layout_row += 1

        # Aggregation interval
        group_layout.addWidget(QLabel('Aggregation interval'), current_layout_row, 0)
        current_layout_row += 1
        self._aggregation_interval_box = QSpinBox()
        self._aggregation_interval_box.setRange(1, 10000000)
        self._aggregation_interval_units_choice = QComboBox()
        self._aggregation_interval_units_choice.addItem('frames', 'frames')
        self._aggregation_interval_units_choice.addItem('seconds', 'sec')
        self._aggregation_interval_units_choice.addItem('minutes', 'min')
        group_layout.addWidget(self._aggregation_interval_box, current_layout_row, 0, 1, 1)
        group_layout.addWidget(self._aggregation_interval_units_choice, current_layout_row, 1, 1, 1)
        current_layout_row += 1
        # ROI filter
        group_layout.addWidget(QLabel('ROI filter (comma delimitted)'), current_layout_row, 0, 1, 3)
        current_layout_row += 1
        self._roi_filter_txt = QLineEdit()
        group_layout.addWidget(self._roi_filter_txt, current_layout_row, 0, 1, 2)
        current_layout_row += 1
        # set the layout
        groupBox = QGroupBox()
        groupBox.setLayout(group_layout)
        layout = QVBoxLayout()
        layout.addWidget(groupBox)
        self.setLayout(layout)

    def _init_event_handlers(self):
        # source file name event handlers
        self._mask_filename_btn.clicked.connect(self._select_mask_file)
        # track type
        self._track_type_choice.currentIndexChanged.connect(self._update_track_type)
        # track checkbox
        self._track_check.stateChanged.connect(self._update_track_flag)
        # sleep deprivation checkbox
        self._sleep_deprivation_check.stateChanged.connect(self._update_sleep_deprivation_flag)
        # aggregation interval
        self._aggregation_interval_box.valueChanged.connect(self._update_aggregation_interval)
        # aggregation interval units
        self._aggregation_interval_units_choice.currentIndexChanged.connect(self._update_aggregation_interval_units)
        # roi filter
        self._roi_filter_txt.textChanged.connect(self._update_roi_filter)
        # selected area
        self._communication_channels.selected_area_signal.connect(self._update_selected_area)
        # update monitored area
        self._communication_channels.monitored_area_options_signal.connect(self._update_monitored_area)
        self._communication_channels.tracker_running_signal.connect(self.setDisabled)
        # refresh mask
        self._communication_channels.toggle_mask_signal.connect(self._refresh_mask)

    def _select_mask_file(self):
        options = QFileDialog.Options(QFileDialog.DontUseNativeDialog)
        fileName, _ = QFileDialog.getOpenFileName(self, 'Select mask file',
                                                  self._mask_filename_txt.text(),
                                                  filter='Mask files (*.msk);;All files (*)',
                                                  options=options)
        if fileName:
            self._update_mask_filename(fileName)

    def _update_mask_filename(self, filename):
        if filename:
            self._monitored_area.set_maskfile(filename)
            self._mask_filename_txt.setText(filename)
        else:
            self._monitored_area.set_maskfile(None)
            self._mask_filename_txt.setText('')

    @pyqtSlot(bool)
    def _refresh_mask(self, display_mask):
        if self._monitored_area.get_maskfile() and display_mask:
            if CrossingBeamType.is_crossing_beam_needed(self._monitored_area.get_track_type(),
                                                        CrossingBeamType.based_on_roi_coord):
                crossing_line = CrossingBeamType.based_on_roi_coord
            else:
                crossing_line = CrossingBeamType.no_crossing_beam
            self._communication_channels.maskfile_signal.emit(self._monitored_area.get_maskfile(), crossing_line)
        else:
            self._communication_channels.maskfile_signal.emit('', CrossingBeamType.no_crossing_beam)
        self._communication_channels.refresh_display_signal.emit()

    def _update_track_type(self, index):
        self._track_type_choice.setCurrentIndex(index)
        self._monitored_area.set_track_type(self._track_type_choice.itemData(index).value)
        self._communication_channels.refresh_display_signal.emit()

    def _update_track_flag(self, val):
        self._track_check.setCheckState(val)
        if val == Qt.Checked:
            self._monitored_area.set_track_flag(True)
            self._track_type_choice.setDisabled(False)
        else:
            self._monitored_area.set_track_flag(False)
            self._track_type_choice.setDisabled(True)
        self._communication_channels.refresh_display_signal.emit()

    def _update_sleep_deprivation_flag(self, val):
        self._sleep_deprivation_check.setCheckState(val)
        if val == Qt.Checked:
            self._monitored_area.set_sleep_deprived_flag(True)
        else:
            self._monitored_area.set_sleep_deprived_flag(False)
        self._communication_channels.refresh_display_signal.emit()

    def _update_aggregation_interval(self, val):
        self._monitored_area.set_aggregation_interval(val)
        self._aggregation_interval_box.setValue(val)
        self._communication_channels.refresh_display_signal.emit()

    def _update_aggregation_interval_units(self, index, units=None):
        if index == 0:
            self._monitored_area.set_aggregation_interval_units('frames')
        elif index == 1:
            self._monitored_area.set_aggregation_interval_units('sec')
        elif index == 2:
            self._monitored_area.set_aggregation_interval_units('min')
        elif units is None:
            index = 0
            self._monitored_area.set_aggregation_interval_units('frames')
        elif units == 'sec':
            index = 1
            self._monitored_area.set_aggregation_interval_units('sec')
        elif units == 'min':
            index = 2
            self._monitored_area.set_aggregation_interval_units('min')
        else:
            index = 0
            self._monitored_area.set_aggregation_interval_units('frames')
        self._aggregation_interval_units_choice.setCurrentIndex(index)
        self._communication_channels.refresh_display_signal.emit()

    def _update_roi_filter(self, roi_filter_str):
        if roi_filter_str:
            self._roi_filter_txt.setText(roi_filter_str)
        else:
            self._roi_filter_txt.setText('')
        self._monitored_area.set_rois_filter_as_str(roi_filter_str)
        self._communication_channels.refresh_display_signal.emit()

    @pyqtSlot(int)
    def _update_selected_area(self, area_index):
        if area_index < 0:
            self.setDisabled(True)
        else:
            self.setDisabled(False)

    @pyqtSlot(MonitoredAreaOptions)
    def _update_monitored_area(self, ma):
        self._monitored_area = ma
        # update mask filename control
        self._update_mask_filename(self._monitored_area.get_maskfile())
        self._update_track_type(self._monitored_area.get_track_type())
        self._update_track_flag(Qt.Checked if self._monitored_area.get_track_flag() else Qt.Unchecked)
        self._update_sleep_deprivation_flag(
            Qt.Checked if self._monitored_area.get_sleep_deprived_flag() else Qt.Unchecked)
        self._update_aggregation_interval(self._monitored_area.get_aggregation_interval())
        self._update_aggregation_interval_units(-1, units=self._monitored_area.get_aggregation_interval_units())
        self._update_roi_filter(self._monitored_area.get_rois_filter_as_str())
        self._communication_channels.refresh_display_signal.emit()


class TrackerWidget(QWidget):
    _stop_timer_signal = pyqtSignal()

    def __init__(self, communication_channels, config):
        super(TrackerWidget, self).__init__()
        self._communication_channels = communication_channels
        self._config = config
        self._start_frame_msecs = -1
        self._end_frame_msecs = -1
        self._refresh_interval = 10
        self._gaussian_kernel_size = 3
        self._init_ui()
        self._init_event_handlers()

    def _init_ui(self):
        group_layout = QGridLayout()

        current_layout_row = 0

        self._timer_lbl = QLabel('')
        self._timer = QTimer()
        group_layout.addWidget(self._timer_lbl, current_layout_row, 0)
        current_layout_row += 1

        start_frame_lbl = QLabel('Start frame (in seconds)')
        self._start_seconds_box = QSpinBox()
        self._start_seconds_box.setRange(0, 1000000000)
        self._start_seconds_box.setSpecialValueText(' ')
        self._start_seconds_box.setCorrectionMode(QSpinBox.CorrectToNearestValue)

        end_frame_lbl = QLabel('End frame (in seconds)')
        self._end_seconds_box = QSpinBox()
        self._end_seconds_box.setRange(0, 1000000000)
        self._end_seconds_box.setSpecialValueText(' ')
        self._end_seconds_box.setCorrectionMode(QSpinBox.CorrectToNearestValue)

        group_layout.addWidget(start_frame_lbl, current_layout_row, 0)
        group_layout.addWidget(self._start_seconds_box, current_layout_row + 1, 0)

        group_layout.addWidget(end_frame_lbl, current_layout_row, 1)
        group_layout.addWidget(self._end_seconds_box, current_layout_row + 1, 1)

        current_layout_row += 2

        self._refresh_interval_box = QSpinBox()
        self._refresh_interval_box.setRange(0, 1000)
        self._refresh_interval_box.setValue(self._refresh_interval)

        self._show_rois_during_tracking = QCheckBox()

        group_layout.addWidget(QLabel('Refresh frame rate'), current_layout_row, 0)
        group_layout.addWidget(self._refresh_interval_box, current_layout_row + 1, 0)

        group_layout.addWidget(QLabel('Show ROIs during tracking'), current_layout_row, 1)
        group_layout.addWidget(self._show_rois_during_tracking, current_layout_row + 1, 1)

        current_layout_row += 2

        self._gaussian_kernel_size_box = QSpinBox()
        self._gaussian_kernel_size_box.setRange(0, 99)
        self._gaussian_kernel_size_box.setValue(self._gaussian_kernel_size)

        group_layout.addWidget(QLabel('Smoothing filter size (must be odd or 0)'), current_layout_row, 0)
        group_layout.addWidget(self._gaussian_kernel_size_box, current_layout_row + 1, 0)

        current_layout_row += 2

        self._start_btn = QPushButton('Start')
        self._cancel_btn = QPushButton('Cancel')

        group_layout.addWidget(self._start_btn, current_layout_row, 0)
        group_layout.addWidget(self._cancel_btn, current_layout_row, 1)
        current_layout_row += 1

        # set the layout
        groupBox = QGroupBox()
        groupBox.setLayout(group_layout)
        layout = QVBoxLayout()
        layout.addWidget(groupBox)
        self.setLayout(layout)

    def _init_event_handlers(self):
        self._start_seconds_box.valueChanged[int].connect(self._update_start_time_in_secs)
        self._end_seconds_box.valueChanged[int].connect(self._update_end_time_in_secs)
        self._refresh_interval_box.valueChanged.connect(self._update_refresh_rate)
        self._gaussian_kernel_size_box.valueChanged.connect(self._update_gaussian_kernel_size)
        # update config
        self._communication_channels.config_signal.connect(self._update_config_options)
        # update video file
        self._communication_channels.video_loaded_signal.connect(partial(self._update_movie, True))
        self._communication_channels.clear_video_signal.connect(partial(self._update_movie, False))
        # update timer
        self._timer.timeout.connect(self._update_tracker_runtime)
        self._stop_timer_signal.connect(self._stop_timer)
        # start/stop tracker
        self._start_btn.clicked.connect(self._start_tracker)
        self._cancel_btn.clicked.connect(self._stop_tracker)

    def _update_start_time_in_secs(self, val: int):
        if val:
            self._start_frame_msecs = val * 1000
            self._communication_channels.video_frame_time_signal.emit(val)
            if self._show_rois_during_tracking.checkState():
                monitored_areas = prepare_monitored_areas(self._config)
                self._communication_channels.all_monitored_areas_rois_signal.emit(monitored_areas,
                                                                                  CrossingBeamType.based_on_roi_coord)
        else:
            self._start_frame_msecs = -1
            self._communication_channels.video_frame_time_signal.emit(0)

    def _update_end_time_in_secs(self, val: int):
        if val:
            self._end_frame_msecs = val * 1000
        else:
            self._end_frame_msecs = -1

    def _update_refresh_rate(self, value):
        self._refresh_interval = value

    def _update_gaussian_kernel_size(self, value):
        self._gaussian_kernel_size = value

    @pyqtSlot(ConfigOptions)
    def _update_config_options(self, new_config):
        self._config = new_config
        config_errors = self._config.validate()
        if len(config_errors) == 0:
            self.setDisabled(False)
            self._start_btn.setDisabled(False)
            self._cancel_btn.setDisabled(True)
        else:
            self.setDisabled(True)

    @pyqtSlot(bool)
    def _update_movie(self, flag):
        if not flag:
            self.setDisabled(True)
        else:
            self.setDisabled(False)
            self._start_btn.setDisabled(False)
            self._cancel_btn.setDisabled(True)

    def _update_tracker_runtime(self):
        secs = self._start_time.elapsed() / 1000
        mins = (secs / 60) % 60
        hours = (secs / 3600)
        secs = secs % 60
        self._timer_lbl.setText('Running for: %dh:%dm:%ds' % (hours, mins, secs))

    def _start_tracker(self):
        self._start_btn.setDisabled(True)
        self._cancel_btn.setDisabled(False)
        self._communication_channels.tracker_running_signal.emit(True)
        self._start_time = QTime()
        self._start_time.start()
        self._timer.setInterval(500)
        self._timer.start()

        def update_frame_image(frame_index, frame_time_in_seconds, frame_image, fly_coords, monitored_areas=None):
            if not self._communication_channels.lock.signalsBlocked() and frame_image is not None:
                if self._refresh_interval > 0 and frame_index % self._refresh_interval == 0:
                    self._communication_channels.video_frame_signal.emit(frame_index, frame_time_in_seconds, frame_image)
                    self._communication_channels.fly_coord_pos_signal.emit(fly_coords)
                if monitored_areas is not None and self._show_rois_during_tracking.checkState():
                    self._communication_channels.all_monitored_areas_rois_signal.emit(monitored_areas, CrossingBeamType.based_on_roi_coord)

        def process_frames(tracker_status):
            image_source = MovieFile(self._config.get_source(),
                                     start_msecs=self._start_frame_msecs,
                                     end_msecs=self._end_frame_msecs,
                                     resolution=self._config.get_image_size())
            start_frame_time = image_source.get_current_frame_time_in_seconds()
            self._communication_channels.video_frame_time_signal.emit(0 if start_frame_time is None else start_frame_time)

            if not image_source.is_opened():
                QMessageBox.critical(self, 'Configuration errors', 'Error opening %s' % self._config.get_source())
            else:
                monitored_areas = prepare_monitored_areas(self._config, fps=image_source.get_fps())
                process_image_frames(image_source, monitored_areas,
                                     cancel_callback=tracker_status.is_running,
                                     frame_callback=partial(update_frame_image, monitored_areas=monitored_areas),
                                     gaussian_filter_size=(self._gaussian_kernel_size, self._gaussian_kernel_size),
                                     gaussian_sigma=0)
                image_source.close()

            self._stop_tracker()

        # before starting the tracker check if the config is valid
        config_errors = self._config.validate()
        if self._gaussian_kernel_size != 0 and self._gaussian_kernel_size % 2 == 0:
            config_errors.append('Gaussian kernel must be odd or 0 if not needed')
        if len(config_errors) == 0 and self._config.get_config_filename() is None:
            # no errors but the config file has not been saved
            config_errors.append('You must save the current configuration before starting the analysis')

        if len(config_errors) == 0:
            ok_to_start = True

            if self._config.has_changed():
                answer = QMessageBox.question(self,
                                              'Unsaved changes',
                                              'You have unsaved changes - Do you want to continue?',
                                              QMessageBox.Yes, QMessageBox.No)
                if answer == QMessageBox.No:
                    ok_to_start = False

            if ok_to_start:
                tracker_status = TrackerStatus(self._communication_channels, True)
                t = threading.Thread(target=process_frames, args=(tracker_status,))
                t.setDaemon(True)
                t.start()
            else:
                self._stop_tracker()

        else:
            self._stop_tracker()
            QMessageBox.critical(self, 'Configuration errors', '\n'.join(config_errors))

    def _stop_tracker(self):
        self._communication_channels.tracker_running_signal.emit(False)
        self._start_btn.setDisabled(False)
        self._cancel_btn.setDisabled(True)
        self._stop_timer_signal.emit()

    def _stop_timer(self):
        self._timer.stop()


class TrackerStatus(QObject):

    def __init__(self, communication_channels, running_flag):
        super(TrackerStatus, self).__init__()
        self._communication_channels = communication_channels
        self._running_flag = running_flag
        self._communication_channels.tracker_running_signal.connect(self._set_running_flag, Qt.QueuedConnection)

    @pyqtSlot(bool)
    def _set_running_flag(self, flag):
        self._running_flag = flag

    def is_running(self):
        return self._running_flag


class FormWidget(QWidget):

    def __init__(self, communication_channels, config):
        super(FormWidget, self).__init__()
        self._init_ui(communication_channels, config)

    def _init_ui(self, communication_channels, config):
        grid_layout = QGridLayout()
        commonOptionsFormWidget = CommonOptionsFormWidget(communication_channels, config)
        monitoredAreaFormWidget = MonitoredAreaFormWidget(communication_channels)
        trackerWidget = TrackerWidget(communication_channels, config)
        monitoredAreaFormWidget.setDisabled(True)
        trackerWidget._update_config_options(config)
        grid_layout.addWidget(commonOptionsFormWidget, 0, 0)
        grid_layout.addWidget(monitoredAreaFormWidget, 1, 0)
        grid_layout.addWidget(trackerWidget, 2, 0)

        # setup the scroll area
        scroll_area = QScrollArea()
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setWidgetResizable(True)
        scroll_area.setEnabled(True)

        scroll_area_widget = QWidget()
        scroll_area_widget.setMinimumWidth(800)
        scroll_area_widget.setLayout(grid_layout)
        scroll_area.setWidget(scroll_area_widget)

        form_layout = QVBoxLayout()
        form_layout.addWidget(scroll_area)

        self.setLayout(form_layout)
