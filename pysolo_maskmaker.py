#!/usr/bin/env python

import sys

from argparse import ArgumentParser
from pysolo_video import MonitoredArea


def get_mask_params(area_location):
    mask_params_by_area_location = {
        'upper_left': {
            'x1': 191.5,
            'x_span': 8,
            'x_gap': 3.75,
            'x_tilt': 0,

            'y1': 205,
            'y_len': 50,
            'y_sep': 2,
            'y_tilt': 0,
        },
        'lower_left': {
            'x1': 194,
            'x_span': 8,
            'x_gap': 3.75,
            'x_tilt': 0,

            'y1': 298,
            'y_len': 50,
            'y_sep': 2,
            'y_tilt': 0,
        },
        'upper_right': {
            'x1': 376,
            'x_span': 7.75,
            'x_gap': 4.2,
            'x_tilt': 0,

            'y1': 206,
            'y_len': 50,
            'y_sep': 2,
            'y_tilt': 0,
        },
        'lower_right': {
            'x1': 379,
            'x_span': 7.7,
            'x_gap': 4.1,
            'x_tilt': 0,

            'y1': 300,
            'y_len': 50,
            'y_sep': 2,
            'y_tilt': 0,
        }
    }
    return mask_params_by_area_location[area_location]


def create_mask(n_rows, n_cols, mask_params, mask_filename):
    x1 = mask_params['x1']
    x_span = mask_params['x_span']
    x_gap = mask_params['x_gap']
    x_tilt = mask_params['x_tilt']

    y1 = mask_params['y1']
    y_len = mask_params['y_len']
    y_sep = mask_params['y_sep']
    y_tilt = mask_params['y_tilt']

    arena = MonitoredArea()
    for col in range(0, n_cols):  # x-coordinates change through columns
        ay = y1 + col * y_tilt  # reset y-coordinate start of col
        by = ay + y_len
        cy = by
        dy = ay
        if col == 0:
            ax = x1
        else:
            ax = x1 + col * (x_span + x_gap)  # move over in x direction to start next column
        bx = ax
        cx = ax + x_span
        dx = cx
        for row in range(0, n_rows):  # y-coordinates change through rows
            arena.add_roi(
                (
                    (int(ax), int(ay)),
                    (int(bx), int(by)),
                    (int(cx), int(cy)),
                    (int(dx), int(dy))
                )
            )
            ay = by + y_sep  # move down in y direction to start next row
            by = ay + y_len
            cy = by
            dy = ay
            ax = ax + x_tilt
            bx = ax
            cx = ax + x_span
            dx = cx

    arena.save_rois(mask_filename)


def main():
    parser = ArgumentParser(usage='prog [options]')
    parser.add_argument('-m', '--mask-file', dest='mask_file', metavar='MASK_FILE',
                        help='The full name of the mask file')
    parser.add_argument('--rows', dest='rows', default=1, help='The number of rows')
    parser.add_argument('--cols', dest='cols', default=32, help='The number of cols')
    parser.add_argument('-r', '--region', dest='region',
                        required=True,
                        choices=['upper_left', 'lower_left', 'upper_right', 'lower_right'],
                        help='The name of the region for which to generate the mask')

    args = parser.parse_args()

    mask_params = get_mask_params(args.region)
    create_mask(args.rows, args.cols, mask_params, args.mask_file)


if __name__ == '__main__':
    sys.exit(main())
