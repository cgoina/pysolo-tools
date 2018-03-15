#!/usr/bin/env python

import cv2
import sys

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QRect, QObject
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (QApplication, QWidget, QMainWindow, QHBoxLayout,
                             QLabel, QFileDialog, QVBoxLayout, QAction, QMessageBox)

from pysolo_config import load_config, ConfigOptions, save_config, MonitoredAreaOptions
from pysolo_form_widget import FormWidget
from pysolo_mask_widget import CreateMaskDlgWidget
from pysolo_video import MovieFile


class PySoloMainAppWindow(QMainWindow):

    def __init__(self, parent=None):
        super(PySoloMainAppWindow, self).__init__(parent)
        self._communication_channels = WidgetCommunicationChannels()
        self._config_filename = None
        self._config = ConfigOptions()
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
        saveConfigAct.triggered.connect(self._save_current_config)

        saveConfigAsAct = QAction('Save &As', self)
        saveConfigAsAct.triggered.connect(self._save_config)

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
        self._form_widget = FormWidget(self, self._communication_channels, self._config)
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
                                                         '',
                                                         filter='Config files (*.cfg);;All files (*)',
                                                         options=options)
        if config_filename:
            config, errors = load_config(config_filename)
            if not errors:
                self._config_filename = config_filename
                self._config = config
            else:
                self._config_filename = None
                self._config = None
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


class WidgetCommunicationChannels(QObject):
    video_loaded_signal = pyqtSignal(MovieFile)
    selected_area_signal = pyqtSignal(int)
    monitored_areas_count_signal = pyqtSignal(int)
    config_signal = pyqtSignal(ConfigOptions)
    monitored_area_signal = pyqtSignal(MonitoredAreaOptions)


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


def main():
    app = QApplication(sys.argv)
    config_app = PySoloMainAppWindow()
    config_app.show()
    app.exec_()


if __name__ == '__main__':
    sys.exit(main())
