#!/usr/bin/env python

import cv2
import sys

from functools import partial

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QPoint, QRect, Qt, QObject, QRegExp
from PyQt5.QtGui import QImage, QPainter, QPixmap, QIcon, QRegExpValidator
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QMainWindow, QHBoxLayout,
                             QLabel, QLineEdit, QGridLayout, QFileDialog, QScrollArea, QVBoxLayout, QSpinBox, QComboBox,
                             QGroupBox, QCheckBox, QAction, QMenu, qApp, QDialog)

from pysolo_maskmaker import create_mask, get_mask_params
from pysolo_video import MovieFile


class PySoloMainAppWindow(QMainWindow):

    def __init__(self, parent=None):
        super(PySoloMainAppWindow, self).__init__(parent)
        self._communication_channels = WidgetCommunicationChannels()
        self._config_filename = None
        self._initUI()

    def _initUI(self):
        self._init_widgets()
        self._init_menus()
        self.setWindowTitle('Fly Tracker')

    def _init_menus(self):
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('File')

        loadConfigAct = QAction('&Open', self)
        loadConfigAct.triggered.connect(self._open_config)

        saveConfigAct = QAction('&Save', self)
        saveConfigAct.triggered.connect(partial(self._save_config, self._config_filename))

        saveConfigAsAct = QAction('Save &As', self)
        saveConfigAct.triggered.connect(partial(self._save_config, None))

        newMaskAct = QAction('New &mask', self)
        newMaskAct.triggered.connect(self._open_new_mask_dlg)

        exitAct = QAction('E&xit', self)
        exitAct.setShortcut('Ctrl+Q')
        exitAct.triggered.connect(self.close)

        fileMenu.addAction(loadConfigAct)
        fileMenu.addAction(saveConfigAct)
        fileMenu.addAction(saveConfigAsAct)
        fileMenu.addSeparator()
        fileMenu.addAction(newMaskAct)
        fileMenu.addAction(exitAct)

    def _init_widgets(self):
        self._monitor_widget = MonitorWidget(self, self._communication_channels)
        self._form_widget = FormWidget(self, self._communication_channels)
        mainWidget = QWidget()
        layout = QHBoxLayout(mainWidget)
        layout.addWidget(self._monitor_widget)
        layout.addWidget(self._form_widget)
        self.setCentralWidget(mainWidget)

    def _open_new_mask_dlg(self):
        mask_editor = CreateMaskDlgWidget(self)
        mask_editor.exec_()

    def _open_config(self):
        options = QFileDialog.Options(QFileDialog.DontUseNativeDialog)
        config_filename, _ = QFileDialog.getOpenFileName(self, 'Select config file',
                                                         self._source_filename_txt.text(),
                                                         filter='Config files (*.cfg);;All files (*)',
                                                         options=options)
        if config_filename:
            self._config_filename = config_filename

        print('!!!!! OPEN CONFIG', self._config_filename)

    def _save_config(self, config_filename):
        if config_filename is None:
            # open file save dialog
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            config_fileName, _ = QFileDialog.getSaveFileName(self, 'Save config file', '',
                                                             'Config Files (*.cfg);;All Files (*)', options=options)

        if config_filename:
            self._config_filename = config_filename

        print('!!!! SAVE CONFIG', config_filename)


class WidgetCommunicationChannels(QObject):
    video_loaded_signal = pyqtSignal(MovieFile)
    region_selected_signal = pyqtSignal(int)


class MonitorWidget(QWidget):

    def __init__(self, parent, communication_channels, image_width=640, image_height=480):
        super(MonitorWidget, self).__init__(parent)
        self._image_width = image_width
        self._image_height = image_height
        self._ratio = image_width / image_height
        self._image = QImage()
        self._initUI()
        communication_channels.video_loaded_signal.connect(self.set_movie)

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

    def __init__(self, parent, communication_channels, max_monitored_areas=64):
        super(CommonOptionsFormWidget, self).__init__(parent)
        self._communication_channels = communication_channels
        self._max_monitored_areas = max_monitored_areas
        self._initUI()

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
            self._communication_channels.region_selected_signal.emit(new_regions_counter)
        else:
            n_regions = self._selected_region_choice.count()
            for r in range(new_regions_counter, n_regions):
                self._selected_region_choice.removeItem(r)
            for r in range(n_regions, new_regions_counter):
                self._selected_region_choice.addItem('Region %d' % (r + 1), r)
            self._selected_region_choice.setDisabled(False)
            if n_regions == 0:
                self._communication_channels.region_selected_signal.emit(1)
            elif self._selected_region_choice.currentData() >= new_regions_counter:
                self._communication_channels.region_selected_signal.emit(new_regions_counter)

    def _update_selected_region(self):
        if self._selected_region_choice.currentData() is not None:
            self._communication_channels.region_selected_signal.emit(self._selected_region_choice.currentData() + 1)


class MonitoredAreaFormWidget(QWidget):

    def __init__(self, parent, communication_channels):
        super(MonitoredAreaFormWidget, self).__init__(parent)
        self._communication_channels = communication_channels
        self._initUI()
        communication_channels.region_selected_signal.connect(self._update_selected_region)

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
    def _update_selected_region(self, region):
        if region == 0:
            self.setDisabled(True)
        else:
            self.setDisabled(False)


class FormWidget(QWidget):

    def __init__(self, parent, communication_channels):
        super(FormWidget, self).__init__(parent)
        self._communication_channels = communication_channels
        self._initUI()

    def _initUI(self):
        layout = QGridLayout()
        commonOptionsFormWidget = CommonOptionsFormWidget(self, self._communication_channels)
        monitoredAreaFormWidget = MonitoredAreaFormWidget(self, self._communication_channels)
        monitoredAreaFormWidget.setDisabled(True)
        layout.addWidget(commonOptionsFormWidget, 0, 0)
        layout.addWidget(monitoredAreaFormWidget, 1, 0)
        self.setLayout(layout)


class CreateMaskDlgWidget(QDialog):

    def __init__(self, parent):
        super(CreateMaskDlgWidget, self).__init__(parent)
        self.setWindowTitle('MAsk Editor')
        self._initUI()

    def _initUI(self):
        layout = QGridLayout()

        area_location_lbl = QLabel('Area Location')
        self._area_location_choice = QComboBox()
        self._area_location_choice.addItem('Upper Left', 'upper_left')
        self._area_location_choice.addItem('Upper Right', 'upper_right')
        self._area_location_choice.addItem('Lower Left', 'lower_left')
        self._area_location_choice.addItem('Lower Right', 'lower_right')

        current_widget_row = 0
        layout.addWidget(area_location_lbl, current_widget_row, 0)
        layout.addWidget(self._area_location_choice, current_widget_row, 1)
        current_widget_row += 1

        rows_lbl = QLabel('Rows')
        self._rows_box = QSpinBox()
        cols_lbl = QLabel('Cols')
        self._cols_box = QSpinBox()

        layout.addWidget(rows_lbl, current_widget_row, 0)
        layout.addWidget(cols_lbl, current_widget_row, 1)
        current_widget_row += 1

        layout.addWidget(self._rows_box, current_widget_row, 0)
        layout.addWidget(self._cols_box, current_widget_row, 1)
        current_widget_row += 1

        reg_ex = QRegExp('[0-9]+.?[0-9]{,2}')
        mask_param_validator = QRegExpValidator(reg_ex)

        x1_lbl = QLabel('x1')
        self.x1_txt = QLineEdit()
        self.x1_txt.setValidator(mask_param_validator)
        x_span_lbl = QLabel('x span')
        self.x_span_txt = QLineEdit()
        self.x_span_txt.setValidator(mask_param_validator)
        x_gap_lbl = QLabel('x gap')
        self.x_gap_txt = QLineEdit()
        self.x_gap_txt.setValidator(mask_param_validator)
        x_tilt_lbl = QLabel('x tilt')
        self.x_tilt_txt = QLineEdit()
        self.x_tilt_txt.setValidator(mask_param_validator)

        y1_lbl = QLabel('y1')
        self.y1_txt = QLineEdit()
        self.y1_txt.setValidator(mask_param_validator)
        y_len_lbl = QLabel('y span')
        self.y_len_txt = QLineEdit()
        self.y_len_txt.setValidator(mask_param_validator)
        y_sep_lbl = QLabel('y gap')
        self.y_sep_txt = QLineEdit()
        self.y_sep_txt.setValidator(mask_param_validator)
        y_tilt_lbl = QLabel('y tilt')
        self.y_tilt_txt = QLineEdit()
        self.y_tilt_txt.setValidator(mask_param_validator)

        layout.addWidget(x1_lbl, current_widget_row, 0)
        layout.addWidget(y1_lbl, current_widget_row, 1)
        current_widget_row += 1
        layout.addWidget(self.x1_txt, current_widget_row, 0)
        layout.addWidget(self.y1_txt, current_widget_row, 1)
        current_widget_row += 1

        layout.addWidget(x_span_lbl, current_widget_row, 0)
        layout.addWidget(y_len_lbl, current_widget_row, 1)
        current_widget_row += 1
        layout.addWidget(self.x_span_txt, current_widget_row, 0)
        layout.addWidget(self.y_len_txt, current_widget_row, 1)
        current_widget_row += 1

        layout.addWidget(x_gap_lbl, current_widget_row, 0)
        layout.addWidget(y_sep_lbl, current_widget_row, 1)
        current_widget_row += 1
        layout.addWidget(self.x_gap_txt, current_widget_row, 0)
        layout.addWidget(self.y_sep_txt, current_widget_row, 1)
        current_widget_row += 1

        layout.addWidget(x_tilt_lbl, current_widget_row, 0)
        layout.addWidget(y_tilt_lbl, current_widget_row, 1)
        current_widget_row += 1
        layout.addWidget(self.x_tilt_txt, current_widget_row, 0)
        layout.addWidget(self.y_tilt_txt, current_widget_row, 1)

        current_widget_row += 2

        cancel_btn = QPushButton('Cancel')
        save_btn = QPushButton('Save...')
        layout.addWidget(cancel_btn, current_widget_row, 0)
        layout.addWidget(save_btn, current_widget_row, 1)

        self._update_mask_params()
        self._area_location_choice.currentIndexChanged.connect(self._update_mask_params)

        cancel_btn.clicked.connect(self.close)
        save_btn.clicked.connect(self._save_mask)

        self.setLayout(layout)


    def _update_mask_params(self):
        mask_params = get_mask_params(self._area_location_choice.currentData())
        self.x1_txt.setText(str(mask_params['x1']))
        self.x_span_txt.setText(str(mask_params['x_span']))
        self.x_gap_txt.setText(str(mask_params['x_gap']))
        self.x_tilt_txt.setText(str(mask_params['x_tilt']))

        self.y1_txt.setText(str(mask_params['y1']))
        self.y_len_txt.setText(str(mask_params['y_len']))
        self.y_sep_txt.setText(str(mask_params['y_sep']))
        self.y_tilt_txt.setText(str(mask_params['y_tilt']))

    def _save_mask(self):
        # open the file dialog and save the mask
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        mask_fileName, _ = QFileDialog.getSaveFileName(self, 'Save mask file', '', 'All Files (*);;Mask Files (*.msk)',
                                                       options=options)
        if mask_fileName:
            # save mask to mask_fileName
            mask_params = {
                'x1': float(self.x1_txt.text()),
                'x_span': float(self.x_span_txt.text()),
                'x_gap': float(self.x_gap_txt.text()),
                'x_tilt': float(self.x_tilt_txt.text()),

                'y1': float(self.y1_txt.text()),
                'y_len': float(self.y_len_txt.text()),
                'y_sep': float(self.y_sep_txt.text()),
                'y_tilt': float(self.y_tilt_txt.text()),
            }
            n_rows = self._rows_box.value()
            n_cols = self._cols_box.value()
            create_mask(n_rows, n_cols, mask_params, mask_fileName)
            self.close() # close if everything went well


def main():
    app = QApplication(sys.argv)
    config_app = PySoloMainAppWindow()
    config_app.show()
    app.exec_()


if __name__ == '__main__':
    sys.exit(main())
