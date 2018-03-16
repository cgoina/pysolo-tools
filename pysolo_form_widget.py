#!/usr/bin/env python

from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtWidgets import (QWidget, QPushButton, QHBoxLayout,
                             QLabel, QLineEdit, QGridLayout, QFileDialog, QVBoxLayout, QSpinBox, QComboBox,
                             QGroupBox, QCheckBox)

from pysolo_config import ConfigOptions, MonitoredAreaOptions
from pysolo_video import MovieFile


class CommonOptionsFormWidget(QWidget):

    def __init__(self, parent, communication_channels, config, max_monitored_areas=64):
        super(CommonOptionsFormWidget, self).__init__(parent)
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
        source_filename_lbl = QLabel('Select source file')
        self._source_filename_btn = QPushButton('Open...')
        # add the source filename control to the layout
        group_layout.addWidget(source_filename_lbl, current_layout_row, 0)
        current_layout_row += 1
        group_layout.addWidget(self._source_filename_txt, current_layout_row, 0)
        group_layout.addWidget(self._source_filename_btn, current_layout_row, 1)
        current_layout_row += 1

        # results directory widgets
        self._results_dir_txt = QLineEdit()
        self._results_dir_txt.setDisabled(True)
        results_dir_lbl = QLabel('Select results directory')
        self._results_dir_btn = QPushButton('Select...')
        # add the source filename control to the layout
        group_layout.addWidget(results_dir_lbl, current_layout_row, 0)
        current_layout_row += 1
        group_layout.addWidget(self._results_dir_txt, current_layout_row, 0)
        group_layout.addWidget(self._results_dir_btn, current_layout_row, 1)
        current_layout_row += 1

        # size
        size_lbl = QLabel('Size')
        group_layout.addWidget(size_lbl, current_layout_row, 0)
        current_layout_row += 1
        size_widget = QWidget()
        self._min_width_box = QSpinBox()
        self._min_width_box.setRange(0, 100000)
        self._max_width_box = QSpinBox()
        self._max_width_box.setRange(0, 100000)
        size_layout = QHBoxLayout(size_widget)
        size_layout.addWidget(self._min_width_box, Qt.AlignLeft)
        size_layout.addWidget(self._max_width_box, Qt.AlignLeft)
        group_layout.addWidget(size_widget, current_layout_row, 0)
        current_layout_row += 1

        # number of monitored regions widgets
        self._n_monitored_areas_box = QSpinBox()
        self._n_monitored_areas_box.setMinimum(0)
        self._n_monitored_areas_box.setMaximum(self._max_monitored_areas)
        n_monitored_areas_lbl = QLabel('Number of monitored regions')
        # add the number of monitored regions control to the layout
        group_layout.addWidget(n_monitored_areas_lbl, current_layout_row, 0)
        current_layout_row += 1
        group_layout.addWidget(self._n_monitored_areas_box, current_layout_row, 0)
        current_layout_row += 1

        # current region widgets
        self._selected_area_choice = QComboBox()
        self._selected_area_choice.setDisabled(True)
        selected_region_lbl = QLabel('Select region')
        # add selected region control to the layout
        group_layout.addWidget(selected_region_lbl, current_layout_row, 0)
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
        # results directory event handlers
        self._results_dir_btn.clicked.connect(self._select_results_dir)
        # image size controls event handlers
        self._min_width_box.valueChanged.connect(self._update_image_width)
        self._max_width_box.valueChanged.connect(self._update_image_height)
        # number of monitored areas control event handlers
        self._n_monitored_areas_box.valueChanged.connect(self._update_number_of_areas)
        # current selected area control event handlers
        self._selected_area_choice.currentIndexChanged.connect(self._update_selected_area)
        # update config
        self._communication_channels.config_signal.connect(self._update_config)
        
    def _select_source_file(self):
        options = QFileDialog.Options(QFileDialog.DontUseNativeDialog)
        filename, _ = QFileDialog.getOpenFileName(self, 'Select source file',
                                                  self._source_filename_txt.text(),
                                                  filter='Video files (*.avi *.mpeg *.mp4);;All files (*)',
                                                  options=options)
        if filename:
            self._update_source_filename(filename)

    def _update_source_filename(self, filename):
        if filename:
            self._config.source = filename
            self._source_filename_txt.setText(filename)
            self._communication_channels.video_loaded_signal.emit(MovieFile(filename))
        else:
            self._config.source = None
            self._source_filename_txt.setText('')
            self._communication_channels.clear_video_signal.emit()

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
            self._config.data_folder = results_dir_name
        else:
            self._results_dir_txt.setText('')
            self._config.data_folder = None

    def _update_image_width(self, val):
        self._config.set_image_width(val)
        self._min_width_box.setValue(val)

    def _update_image_height(self, val):
        self._config.set_image_height(val)
        self._max_width_box.setValue(val)

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
                    self._selected_area_choice.addItem('Region %d' % (a + 1), a)
            self._selected_area_choice.setDisabled(False)
            if n_areas == 0:
                self._communication_channels.selected_area_signal.emit(0)
            elif self._selected_area_choice.currentData() >= new_areas_counter:
                self._communication_channels.selected_area_signal.emit(new_areas_counter - 1)

    def _update_selected_area(self, area_index):
        selected_monitored_area = None
        if area_index >= 0:
            selected_monitored_area = self._config.get_monitored_area(area_index)
        if selected_monitored_area is not None:
            self._communication_channels.monitored_area_signal.emit(selected_monitored_area)
        else:
            self._communication_channels.monitored_area_signal.emit(MonitoredAreaOptions())

    @pyqtSlot(ConfigOptions)
    def _update_config(self, new_config):
        self._config = new_config
        # update the video source
        self._update_source_filename(self._config.source)
        # update the results folder
        self._update_results_dir(self._config.data_folder)
        # update the size
        self._update_image_width(self._config.get_image_width())
        self._update_image_height(self._config.get_image_height())
        # update the number of monitored areas
        self._n_monitored_areas_box.setValue(self._config.monitored_areas_count)


class MonitoredAreaFormWidget(QWidget):

    def __init__(self, parent, communication_channels, config):
        super(MonitoredAreaFormWidget, self).__init__(parent)
        self._config = config
        self._monitored_area = MonitoredAreaOptions()
        self._init_ui()
        self._init_event_handlers(communication_channels)

    def _init_ui(self):
        group_layout = QGridLayout()

        current_layout_row = 0
        # source file name widgets
        self._mask_filename_txt = QLineEdit()
        self._mask_filename_txt.setDisabled(True)
        mask_filename_lbl = QLabel('Select mask file')
        self._mask_filename_btn = QPushButton('Open...')
        # add the mask filename control to the layout
        group_layout.addWidget(mask_filename_lbl, current_layout_row, 0)
        current_layout_row += 1
        group_layout.addWidget(self._mask_filename_txt, current_layout_row, 0)
        group_layout.addWidget(self._mask_filename_btn, current_layout_row, 1)
        current_layout_row += 1

        # track type
        self._track_type_choice = QComboBox()
        self._track_type_choice.addItem('Distance', 0)
        self._track_type_choice.addItem('Crossover', 1)
        self._track_type_choice.addItem('Position', 2)

        track_type_lbl = QLabel('Select Track Type')
        # add track type control to the layout
        group_layout.addWidget(track_type_lbl, current_layout_row, 0)
        current_layout_row += 1
        group_layout.addWidget(self._track_type_choice, current_layout_row, 0)
        current_layout_row += 1

        # track flag
        self._track_check = QCheckBox()
        track_flag_lbl = QLabel('Monitor area')
        track_flag_widget = QWidget()
        track_flag_layout = QHBoxLayout(track_flag_widget)
        track_flag_layout.addWidget(self._track_check)
        track_flag_layout.addWidget(track_flag_lbl, Qt.AlignLeft)
        group_layout.addWidget(track_flag_widget, current_layout_row, 0)

        current_layout_row += 1

        # sleep deprivation flag
        self._sleep_deprivation_check = QCheckBox()
        sleep_deprivation_lbl = QLabel('Sleep deprivation')
        sleep_deprivationwidget = QWidget()
        sleep_deprivation_layout = QHBoxLayout(sleep_deprivationwidget)
        sleep_deprivation_layout.addWidget(self._sleep_deprivation_check)
        sleep_deprivation_layout.addWidget(sleep_deprivation_lbl, Qt.AlignLeft)
        group_layout.addWidget(sleep_deprivationwidget, current_layout_row, 0)
        current_layout_row += 1

        # Aggregation interval
        aggregation_interval_lbl = QLabel('Aggregation interval')
        group_layout.addWidget(aggregation_interval_lbl, current_layout_row, 0)
        current_layout_row += 1
        aggregation_interval_widget = QWidget()
        self._aggregation_interval_box = QSpinBox()
        self._aggregation_interval_box.setMinimum(1)
        self._aggregation_interval_units_choice = QComboBox()
        self._aggregation_interval_units_choice.addItem('frames', 'frames')
        self._aggregation_interval_units_choice.addItem('seconds', 'sec')
        self._aggregation_interval_units_choice.addItem('minutes', 'min')
        aggregation_interval_layout = QHBoxLayout(aggregation_interval_widget)
        aggregation_interval_layout.addWidget(self._aggregation_interval_box, Qt.AlignLeft)
        aggregation_interval_layout.addWidget(self._aggregation_interval_units_choice, Qt.AlignLeft)
        group_layout.addWidget(aggregation_interval_widget, current_layout_row, 0)
        current_layout_row += 1

        # ROI filter
        roi_filter_lbl = QLabel('ROI filter (comma delimitted)')
        group_layout.addWidget(roi_filter_lbl, current_layout_row, 0)
        current_layout_row += 1
        self._roi_filter_txt = QLineEdit()
        group_layout.addWidget(self._roi_filter_txt, current_layout_row, 0)
        current_layout_row += 1

        # set the layout
        groupBox = QGroupBox()
        groupBox.setLayout(group_layout)
        layout = QVBoxLayout()
        layout.addWidget(groupBox)
        self.setLayout(layout)

    def _init_event_handlers(self, communication_channels):
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
        communication_channels.selected_area_signal.connect(self._update_selected_area)
        # update config
        communication_channels.config_signal.connect(self._update_monitored_area_config)
        # update monitored area
        communication_channels.monitored_area_signal.connect(self._update_monitored_area)

    def _select_mask_file(self):
        options = QFileDialog.Options(QFileDialog.DontUseNativeDialog)
        fileName, _ = QFileDialog.getOpenFileName(self, 'Select mask file',
                                                  self._mask_filename_txt.text(),
                                                  filter='All files (*)',
                                                  options=options)
        if fileName:
            self._update_mask_filename(fileName)

    def _update_mask_filename(self, filename):
        if filename:
            self._monitored_area.maskfile = filename
            self._mask_filename_txt.setText(filename)
        else:
            self._monitored_area.maskfile = None
            self._mask_filename_txt.setText('')

    def _update_track_type(self, index):
        self._monitored_area.track_type = index
        self._track_type_choice.setCurrentIndex(index)

    def _update_track_flag(self, val):
        self._track_check.setCheckState(val)
        if val == Qt.Checked:
            self._monitored_area.track_flag = True
            self._track_type_choice.setDisabled(False)
        else:
            self._monitored_area.track_flag = False
            self._track_type_choice.setDisabled(True)

    def _update_sleep_deprivation_flag(self, val):
        self._sleep_deprivation_check.setCheckState(val)
        self._monitored_area.sleep_deprived_flag = True if val == Qt.Checked else False

    def _update_aggregation_interval(self, val):
        self._monitored_area.aggregation_interval = val
        self._aggregation_interval_box.setValue(val)

    def _update_aggregation_interval_units(self, index, units=None):
        if index == 0:
            self._monitored_area.aggregation_interval_units = 'frames'
        elif index == 1:
            self._monitored_area.aggregation_interval_units = 'sec'
        elif index == 2:
            self._monitored_area.aggregation_interval_units = 'min'
        elif units is None:
            index = 0
            self._monitored_area.aggregation_interval_units = 'frames'
        elif units == 'sec':
            index = 1
            self._monitored_area.aggregation_interval_units = 'sec'
        elif units == 'min':
            index = 2
            self._monitored_area.aggregation_interval_units = 'min'
        else:
            index = 0
            self._monitored_area.aggregation_interval_units = 'frames'
        self._aggregation_interval_units_choice.setCurrentIndex(index)

    def _update_roi_filter(self, roi_filter_str):
        if roi_filter_str:
            self._roi_filter_txt.setText(roi_filter_str)
        else:
            self._roi_filter_txt.setText('')
        self._monitored_area.set_rois_filter_as_str(roi_filter_str)

    @pyqtSlot(int)
    def _update_selected_area(self, area_index):
        if area_index < 0:
            self.setDisabled(True)
        else:
            self.setDisabled(False)

    @pyqtSlot(ConfigOptions)
    def _update_monitored_area_config(self, new_config):
        self._config = new_config

    @pyqtSlot(MonitoredAreaOptions)
    def _update_monitored_area(self, ma):
        self._monitored_area = ma
        # update mask filename control
        self._update_mask_filename(self._monitored_area.maskfile)
        self._update_track_type(self._monitored_area.track_type)
        self._update_track_flag(Qt.Checked if self._monitored_area.track_flag else Qt.Unchecked)
        self._update_sleep_deprivation_flag(Qt.Checked if self._monitored_area.sleep_deprived_flag else Qt.Unchecked)
        self._update_aggregation_interval(self._monitored_area.aggregation_interval)
        self._update_aggregation_interval_units(-1, units=self._monitored_area.aggregation_interval_units)
        self._update_roi_filter(self._monitored_area.get_rois_filter_as_str())


class FormWidget(QWidget):

    def __init__(self, parent, communication_channels, config):
        super(FormWidget, self).__init__(parent)
        self._init_ui(communication_channels, config)

    def _init_ui(self, communication_channels, config):
        layout = QGridLayout()
        commonOptionsFormWidget = CommonOptionsFormWidget(self, communication_channels, config)
        monitoredAreaFormWidget = MonitoredAreaFormWidget(self, communication_channels, config)
        monitoredAreaFormWidget.setDisabled(True)
        layout.addWidget(commonOptionsFormWidget, 0, 0)
        layout.addWidget(monitoredAreaFormWidget, 1, 0)
        self.setLayout(layout)
