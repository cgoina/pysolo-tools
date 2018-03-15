#!/usr/bin/env python

import sys

from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QHBoxLayout,
                             QLabel, QLineEdit, QGridLayout, QFileDialog, QVBoxLayout, QSpinBox, QComboBox,
                             QGroupBox, QCheckBox)

from pysolo_video import MovieFile


class CommonOptionsFormWidget(QWidget):

    def __init__(self, parent, communication_channels, config, max_monitored_areas=64):
        super(CommonOptionsFormWidget, self).__init__(parent)
        self._communication_channels = communication_channels
        self._config = config
        self._max_monitored_areas = max_monitored_areas
        self._initUI()
        self._communication_channels.monitored_areas_count_signal.connect(self._config.set_monitored_areas_count)

    def _initUI(self):
        group_layout = QGridLayout()

        current_layout_row = 0
        # source file name widgets
        self._source_filename_txt = QLineEdit()
        self._source_filename_txt.setDisabled(True)
        source_filename_lbl = QLabel('Select source file')
        source_filename_btn = QPushButton('Open...')
        # add the source filename control to the layout
        group_layout.addWidget(source_filename_lbl, current_layout_row, 0)
        current_layout_row += 1
        group_layout.addWidget(self._source_filename_txt, current_layout_row, 0)
        group_layout.addWidget(source_filename_btn, current_layout_row, 1)
        current_layout_row += 1
        # source file name event handlers
        source_filename_btn.clicked.connect(self._select_source_file)

        # results directory widgets
        self._results_dir_txt = QLineEdit()
        self._results_dir_txt.setDisabled(True)
        results_dir_lbl = QLabel('Select results directory')
        results_dir_btn = QPushButton('Select...')
        # add the source filename control to the layout
        group_layout.addWidget(results_dir_lbl, current_layout_row, 0)
        current_layout_row += 1
        group_layout.addWidget(self._results_dir_txt, current_layout_row, 0)
        group_layout.addWidget(results_dir_btn, current_layout_row, 1)
        current_layout_row += 1
        # results directory event handlers
        results_dir_btn.clicked.connect(self._select_results_dir)

        # size
        size_lbl = QLabel('Size')
        group_layout.addWidget(size_lbl, current_layout_row, 0)
        current_layout_row += 1
        size_widget = QWidget()
        self._min_width_box = QSpinBox()
        self._min_width_box.setMinimum(1)
        self._max_width_box = QSpinBox()
        self._max_width_box.setMinimum(1)
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
        # number of monitored regions event handlers
        self._n_monitored_areas_box.valueChanged.connect(self._update_number_of_regions)

        # current region widgets
        self._selected_region_choice = QComboBox()
        self._selected_region_choice.setDisabled(True)
        selected_region_lbl = QLabel('Select region')
        # add selected region control to the layout
        group_layout.addWidget(selected_region_lbl, current_layout_row, 0)
        current_layout_row += 1
        group_layout.addWidget(self._selected_region_choice, current_layout_row, 0)
        current_layout_row += 1
        # current region event handlers
        self._selected_region_choice.currentIndexChanged.connect(self._update_selected_region)

        # set the layout
        groupBox = QGroupBox()
        groupBox.setLayout(group_layout)
        layout = QVBoxLayout()
        layout.addWidget(groupBox)
        self.setLayout(layout)

    def _select_source_file(self):
        options = QFileDialog.Options(QFileDialog.DontUseNativeDialog)
        filename, _ = QFileDialog.getOpenFileName(self, 'Select source file',
                                                  self._source_filename_txt.text(),
                                                  filter='Video files (*.avi *.mpeg *.mp4);;All files (*)',
                                                  options=options)
        if filename:
            self._source_filename_txt.setText(filename)
            self._communication_channels.video_loaded_signal.emit(MovieFile(filename))

    def _select_results_dir(self):
        options = QFileDialog.Options(QFileDialog.DontUseNativeDialog | QFileDialog.ShowDirsOnly)
        resultsDirName = QFileDialog.getExistingDirectory(self, 'Select results directory',
                                                          self._results_dir_txt.text(),
                                                          options=options)
        if resultsDirName:
            self._results_dir_txt.setText(resultsDirName)

    def _update_number_of_regions(self):
        new_regions_counter = self._n_monitored_areas_box.value()
        # update selected region control
        if new_regions_counter == 0:
            n_regions = self._selected_region_choice.count()
            for r in range(n_regions):
                self._selected_region_choice.removeItem(r)
            self._selected_region_choice.setDisabled(True)
            self._communication_channels.selected_area_signal.emit(new_regions_counter)
        else:
            n_regions = self._selected_region_choice.count()
            for r in range(new_regions_counter, n_regions):
                self._selected_region_choice.removeItem(r)
            for r in range(n_regions, new_regions_counter):
                self._selected_region_choice.addItem('Region %d' % (r + 1), r)
            self._selected_region_choice.setDisabled(False)
            if n_regions == 0:
                self._communication_channels.selected_area_signal.emit(1)
            elif self._selected_region_choice.currentData() >= new_regions_counter:
                self._communication_channels.selected_area_signal.emit(new_regions_counter)
        # send the message that the UI updated the number of monitored regions
        self._communication_channels.monitored_areas_count_signal.emit(new_regions_counter)

    def _update_selected_region(self):
        if self._selected_region_choice.currentData() is not None:
            self._communication_channels.selected_area_signal.emit(self._selected_region_choice.currentData() + 1)


class MonitoredAreaFormWidget(QWidget):

    def __init__(self, parent, communication_channels, config):
        super(MonitoredAreaFormWidget, self).__init__(parent)
        self._communication_channels = communication_channels
        self._config = config
        self._initUI()
        communication_channels.selected_area_signal.connect(self._update_selected_area)

    def _initUI(self):
        group_layout = QGridLayout()

        current_layout_row = 0
        # source file name widgets
        self._mask_filename_txt = QLineEdit()
        self._mask_filename_txt.setDisabled(True)
        mask_filename_lbl = QLabel('Select mask file')
        mask_filename_btn = QPushButton('Open...')
        # add the mask filename control to the layout
        group_layout.addWidget(mask_filename_lbl, current_layout_row, 0)
        current_layout_row += 1
        group_layout.addWidget(self._mask_filename_txt, current_layout_row, 0)
        group_layout.addWidget(mask_filename_btn, current_layout_row, 1)
        current_layout_row += 1
        # source file name event handlers
        mask_filename_btn.clicked.connect(self._select_mask_file)

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
        self._track_flag = QCheckBox()
        track_flag_lbl = QLabel('Monitor area')
        track_flag_widget = QWidget()
        track_flag_layout = QHBoxLayout(track_flag_widget)
        track_flag_layout.addWidget(self._track_flag)
        track_flag_layout.addWidget(track_flag_lbl, Qt.AlignLeft)
        group_layout.addWidget(track_flag_widget, current_layout_row, 0)

        current_layout_row += 1

        # sleep deprivation flag
        self._sleep_deprivation_flag = QCheckBox()
        sleep_deprivation_lbl = QLabel('Sleep deprivation')
        sleep_deprivationwidget = QWidget()
        sleep_deprivation_layout = QHBoxLayout(sleep_deprivationwidget)
        sleep_deprivation_layout.addWidget(self._sleep_deprivation_flag)
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
        self._aggregation_interval_units = QComboBox()
        self._aggregation_interval_units.addItems(['frames', 'seconds', 'minutes'])
        aggregation_interval_layout = QHBoxLayout(aggregation_interval_widget)
        aggregation_interval_layout.addWidget(self._aggregation_interval_box, Qt.AlignLeft)
        aggregation_interval_layout.addWidget(self._aggregation_interval_units, Qt.AlignLeft)
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

    def _select_mask_file(self):
        options = QFileDialog.Options(QFileDialog.DontUseNativeDialog)
        fileName, _ = QFileDialog.getOpenFileName(self, 'Select mask file',
                                                  self._mask_filename_txt.text(),
                                                  filter='All files (*)',
                                                  options=options)
        if fileName:
            self._mask_filename_txt.setText(fileName)

    @pyqtSlot(int)
    def _update_selected_area(self, area_index):
        if area_index == 0:
            self.setDisabled(True)
        else:
            self.setDisabled(False)


class FormWidget(QWidget):

    def __init__(self, parent, communication_channels, config):
        super(FormWidget, self).__init__(parent)
        self._initUI(communication_channels, config)

    def _initUI(self, communication_channels, config):
        layout = QGridLayout()
        commonOptionsFormWidget = CommonOptionsFormWidget(self, communication_channels, config)
        monitoredAreaFormWidget = MonitoredAreaFormWidget(self, communication_channels, config)
        monitoredAreaFormWidget.setDisabled(True)
        layout.addWidget(commonOptionsFormWidget, 0, 0)
        layout.addWidget(monitoredAreaFormWidget, 1, 0)
        self.setLayout(layout)
