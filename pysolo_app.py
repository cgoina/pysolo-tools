#!/usr/bin/env python

import logging.config
import sys
from argparse import ArgumentParser

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import (QApplication, QWidget, QMainWindow, QHBoxLayout,
                             QFileDialog, QAction, QMessageBox)

from pysolo_config import load_config, ConfigOptions, save_config, MonitoredAreaOptions
from pysolo_form_widget import FormWidget
from pysolo_image_widget import ImageWidget
from pysolo_mask_widget import CreateMaskDlgWidget
from pysolo_video import MovieFile, MonitoredArea


class PySoloMainAppWindow(QMainWindow):

    def __init__(self, parent=None):
        super(PySoloMainAppWindow, self).__init__(parent)
        self._communication_channels = WidgetCommunicationChannels()
        self._config_filename = None
        self._config = ConfigOptions()
        self._init_ui()

    def _init_ui(self):
        self._init_widgets()
        self._init_menus()
        self._init_event_handlers()
        self.setWindowTitle('Fly Tracker')

    def _init_menus(self):
        main_menu = self.menuBar()
        file_menu = main_menu.addMenu('File')

        self._load_config_act = QAction('&Open', self)
        self._load_config_act.triggered.connect(self._open_config)

        save_config_act = QAction('&Save', self)
        save_config_act.triggered.connect(self._save_current_config)

        save_config_as_act = QAction('Save &As', self)
        save_config_as_act.triggered.connect(self._save_config)

        self._clear_config_act = QAction('&Clear config', self)
        self._clear_config_act.triggered.connect(self._clear_config)

        new_mask_act = QAction('New &mask', self)
        new_mask_act.triggered.connect(self._open_new_mask_dlg)

        exit_act = QAction('E&xit', self)
        exit_act.setShortcut('Ctrl+Q')
        exit_act.triggered.connect(self.close)

        file_menu.addAction(self._load_config_act)
        file_menu.addAction(save_config_act)
        file_menu.addAction(save_config_as_act)
        file_menu.addSeparator()
        file_menu.addAction(self._clear_config_act)
        file_menu.addSeparator()
        file_menu.addAction(new_mask_act)
        file_menu.addAction(exit_act)

    def _init_widgets(self):
        image_widget = ImageWidget(self, self._communication_channels)
        form_widget = FormWidget(self, self._communication_channels, self._config)
        main_widget = QWidget()
        main_widget.setMinimumWidth(1200)
        main_widget.setMinimumHeight(800)
        layout = QHBoxLayout(main_widget)
        layout.addWidget(image_widget)
        layout.addWidget(form_widget)
        self.setCentralWidget(main_widget)

    def _init_event_handlers(self):
        self._communication_channels.tracker_running_signal.connect(self._tracker_running_handler)

    def _tracker_running_handler(self, flag):
        self._load_config_act.setDisabled(flag)
        self._clear_config_act.setDisabled(flag)

    def _open_new_mask_dlg(self):
        mask_editor = CreateMaskDlgWidget(self, self._communication_channels)
        mask_editor.exec_()

    def _open_config(self):
        options = QFileDialog.Options(QFileDialog.DontUseNativeDialog)
        config_filename, _ = QFileDialog.getOpenFileName(self, 'Select config file',
                                                         '',
                                                         filter='Config files (*.cfg);;All files (*)',
                                                         options=options)
        if config_filename:
            config, errors = load_config(config_filename)
            if not errors:
                self._config_filename = config_filename
                self._config = config
                self._communication_channels.config_signal.emit(self._config)
            else:
                self._clear_config()
                self._display_errors('Config read errors', errors)

        self._update_status()

    def _update_status(self):
        if self._config_filename:
            self.statusBar().showMessage('Config file: %s' % self._config_filename)
        else:
            self.statusBar().showMessage('No config file')

    def _save_current_config(self):
        self._save_config(self._config_filename)

    def _save_config(self, config_filename=None):
        if not config_filename:
            # open file save dialog
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            config_filename, _ = QFileDialog.getSaveFileName(self, 'Save config file', '',
                                                             'Config Files (*.cfg);;All Files (*)', options=options)

        if config_filename:
            errors = save_config(self._config, config_filename)
            if not errors:
                self._config_filename = config_filename
            else:
                self._display_errors('Config save errors', errors)

        self._update_status()

    def _display_errors(self, title, errors):
        QMessageBox.critical(self, title, '\n'.join(errors))

    def _clear_config(self):
        self._config = ConfigOptions()
        self._config_filename = None
        self._communication_channels.config_signal.emit(self._config)
        self._update_status()


class WidgetCommunicationChannels(QObject):
    video_loaded_signal = pyqtSignal(MovieFile)
    clear_video_signal = pyqtSignal()
    selected_area_signal = pyqtSignal(int)
    config_signal = pyqtSignal(ConfigOptions)
    monitored_area_options_signal = pyqtSignal(MonitoredAreaOptions)
    maskfile_signal = pyqtSignal(str)
    monitored_area_rois_signal = pyqtSignal(MonitoredArea)
    video_frame_pos_signal = pyqtSignal(float, str)
    fly_coord_pos_signal = pyqtSignal(float, float)
    tracker_running_signal = pyqtSignal(bool)


def main():
    parser = ArgumentParser(usage='prog [options]')
    parser.add_argument('-l', '--log-config',
                        default='logger.conf', dest='log_config_file',
                        metavar='LOG_CONFIG_FILE', help='The full path to the log config file to open')

    args = parser.parse_args()

    # setup logger
    logging.config.fileConfig(args.log_config_file)

    app = QApplication(sys.argv)
    config_app = PySoloMainAppWindow()
    config_app.show()
    app.exec_()


if __name__ == '__main__':
    sys.exit(main())
