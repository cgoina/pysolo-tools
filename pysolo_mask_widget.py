#!/usr/bin/env python
import os
from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import (QPushButton, QLabel, QComboBox, QDialog, QGridLayout, QSpinBox, QLineEdit,
                             QFileDialog, QCheckBox)

from pysolo_maskmaker import create_mask, get_mask_params, get_mask_params_from_rois
from pysolo_video import MonitoredArea, CrossingBeamType


class CreateMaskDlgWidget(QDialog):

    def __init__(self, communication_channels):
        super(CreateMaskDlgWidget, self).__init__()
        self._communication_channels = communication_channels
        self.setWindowTitle('MAsk Editor')
        self._init_ui()

    def _init_ui(self):
        layout = QGridLayout()

        area_location_lbl = QLabel('Monitored Area')
        self._area_location_choice = QComboBox()
        self._area_location_choice.addItem('Area 1', 'upper_left')
        self._area_location_choice.addItem('Area 2', 'upper_right')
        self._area_location_choice.addItem('Area 3', 'lower_left')
        self._area_location_choice.addItem('Area 4', 'lower_right')

        current_widget_row = 0
        layout.addWidget(area_location_lbl, current_widget_row, 0, 1, 3)
        layout.addWidget(self._area_location_choice, current_widget_row, 3, 1, 3)
        current_widget_row += 1

        crossline_lbl = QLabel('Cross line type')
        self._crossline_choice = QComboBox()
        self._crossline_choice.addItem('None', CrossingBeamType.no_crossing_beam)
        self._crossline_choice.addItem('Horizontal', CrossingBeamType.horizontal)
        layout.addWidget(crossline_lbl, current_widget_row, 0, 1, 3)
        layout.addWidget(self._crossline_choice, current_widget_row, 3, 1, 3)
        current_widget_row += 1

        rows_lbl = QLabel('Rows')
        self._rows_box = QSpinBox()
        cols_lbl = QLabel('Cols')
        self._cols_box = QSpinBox()

        layout.addWidget(rows_lbl, current_widget_row, 0, 1, 3)
        layout.addWidget(cols_lbl, current_widget_row, 3, 1, 3)
        current_widget_row += 1

        layout.addWidget(self._rows_box, current_widget_row, 0, 1, 3)
        layout.addWidget(self._cols_box, current_widget_row, 3, 1, 3)
        current_widget_row += 1

        reg_ex = QRegExp('(-)?[0-9]+.?[0-9]{,2}')
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

        layout.addWidget(x1_lbl, current_widget_row, 0, 1, 3)
        layout.addWidget(y1_lbl, current_widget_row, 3, 1, 3)
        current_widget_row += 1
        layout.addWidget(self.x1_txt, current_widget_row, 0, 1, 3)
        layout.addWidget(self.y1_txt, current_widget_row, 3, 1, 3)
        current_widget_row += 1

        layout.addWidget(x_span_lbl, current_widget_row, 0, 1, 3)
        layout.addWidget(y_len_lbl, current_widget_row, 3, 1, 3)
        current_widget_row += 1
        layout.addWidget(self.x_span_txt, current_widget_row, 0, 1, 3)
        layout.addWidget(self.y_len_txt, current_widget_row, 3, 1, 3)
        current_widget_row += 1

        layout.addWidget(x_gap_lbl, current_widget_row, 0, 1, 3)
        layout.addWidget(y_sep_lbl, current_widget_row, 3, 1, 3)
        current_widget_row += 1
        layout.addWidget(self.x_gap_txt, current_widget_row, 0, 1, 3)
        layout.addWidget(self.y_sep_txt, current_widget_row, 3, 1, 3)
        current_widget_row += 1

        layout.addWidget(x_tilt_lbl, current_widget_row, 0, 1, 3)
        layout.addWidget(y_tilt_lbl, current_widget_row, 3, 1, 3)
        current_widget_row += 1
        layout.addWidget(self.x_tilt_txt, current_widget_row, 0, 1, 3)
        layout.addWidget(self.y_tilt_txt, current_widget_row, 3, 1, 3)

        current_widget_row += 2

        self._overlay_check = QCheckBox()
        self._overlay_check.setChecked(True)

        layout.addWidget(self._overlay_check, current_widget_row, 0)
        layout.addWidget(QLabel('Overlay mask'), current_widget_row, 1)

        current_widget_row += 2

        cancel_btn = QPushButton('Cancel')
        load_btn = QPushButton('Load...')
        save_btn = QPushButton('Save...')

        layout.addWidget(cancel_btn, current_widget_row, 0, 1, 2)
        layout.addWidget(load_btn, current_widget_row, 2, 1, 2)
        layout.addWidget(save_btn, current_widget_row, 4, 1, 2)

        self._update_mask_params()
        self._area_location_choice.currentIndexChanged.connect(self._update_mask_params)

        self._crossline_choice.currentTextChanged.connect(self._update_mask_overlay)
        self._rows_box.valueChanged.connect(self._update_mask_overlay)
        self._cols_box.valueChanged.connect(self._update_mask_overlay)
        self.x1_txt.textChanged.connect(self._update_mask_overlay)
        self.x_span_txt.textChanged.connect(self._update_mask_overlay)
        self.x_gap_txt.textChanged.connect(self._update_mask_overlay)
        self.x_tilt_txt.textChanged.connect(self._update_mask_overlay)
        self.y1_txt.textChanged.connect(self._update_mask_overlay)
        self.y_len_txt.textChanged.connect(self._update_mask_overlay)
        self.y_sep_txt.textChanged.connect(self._update_mask_overlay)
        self.y_tilt_txt.textChanged.connect(self._update_mask_overlay)
        self._overlay_check.stateChanged.connect(self._update_mask_overlay)

        cancel_btn.clicked.connect(self.close)
        load_btn.clicked.connect(self._load_mask)
        save_btn.clicked.connect(self._save_mask)

        self.setLayout(layout)

    def _update_mask_params(self):
        mask_params = get_mask_params(self._area_location_choice.currentData())
        self._update_mask_params_values(mask_params)

    def _update_mask_params_values(self, mask_params):
        self.x1_txt.setText(str(mask_params['x1']))
        self.x_span_txt.setText(str(mask_params['x_span']))
        self.x_gap_txt.setText(str(mask_params['x_gap']))
        self.x_tilt_txt.setText(str(mask_params['x_tilt']))

        self.y1_txt.setText(str(mask_params['y1']))
        self.y_len_txt.setText(str(mask_params['y_len']))
        self.y_sep_txt.setText(str(mask_params['y_sep']))
        self.y_tilt_txt.setText(str(mask_params['y_tilt']))
        self._update_mask_overlay()

    def _load_mask(self):
        options = QFileDialog.Options(QFileDialog.DontUseNativeDialog)
        mask_file, _ = QFileDialog.getOpenFileName(self, 'Select mask file',
                                                   '',
                                                   filter='Mask files (*.msk);;All files (*)',
                                                   options=options)
        if mask_file:
            arena = MonitoredArea()
            arena.load_rois(mask_file)
            mask_params, n_rows, n_cols = get_mask_params_from_rois(arena)
            self._rows_box.setValue(n_rows)
            self._cols_box.setValue(n_cols)
            self._update_mask_params_values(mask_params)

    def _save_mask(self):
        # open the file dialog and save the mask
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        mask_file, _ = QFileDialog.getSaveFileName(self,
                                                       'Save mask file',
                                                       '',
                                                       'Mask Files (*.msk);;All Files (*)',
                                                       options=options)
        if mask_file:
            mask_filename, mask_fileext = os.path.splitext(mask_file)
            if not mask_fileext:
                mask_file = mask_file + '.msk'
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
            arena = create_mask(n_rows, n_cols, mask_params)
            arena.save_rois(mask_file)
            self.close() # close if everything went well

    def _update_mask_overlay(self):
        if self._overlay_check.checkState():
            self._draw_mask()
        else:
            # clear the mask
            self._communication_channels.toggle_mask_signal.emit(False)

    def _draw_mask(self):
        mask_params = {
            'x1': _text_to_float(self.x1_txt.text()),
            'x_span': _text_to_float(self.x_span_txt.text()),
            'x_gap': _text_to_float(self.x_gap_txt.text()),
            'x_tilt': _text_to_float(self.x_tilt_txt.text()),

            'y1': _text_to_float(self.y1_txt.text()),
            'y_len': _text_to_float(self.y_len_txt.text()),
            'y_sep': _text_to_float(self.y_sep_txt.text()),
            'y_tilt': _text_to_float(self.y_tilt_txt.text()),
        }
        n_rows = self._rows_box.value()
        n_cols = self._cols_box.value()
        arena = create_mask(n_rows, n_cols, mask_params)
        self._communication_channels.monitored_area_rois_signal.emit(arena, self._crossline_choice.currentData())


def _text_to_float(s):
    try:
        return float(s)
    except ValueError:
        return 0
