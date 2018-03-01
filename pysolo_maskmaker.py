#!venv/bin/python

import sys

from optparse import OptionParser
from pysolo_video import MonitorArea


def main():
    parser = OptionParser(usage='%prog [options] [argument]', version='%prog version 1.0')
    parser.add_option('-m', '--mask-file', dest='mask_file', metavar='MASK_FILE', help='The full name of the mask file')
    parser.add_option('-r', '--region', dest='region', type='choice',
                      choices=['upper_left', 'lower_left', 'upper_right', 'lower_right'],
                      help='The name of the region for which to generate the mask')

    (options, args) = parser.parse_args()

    rows = 1
    columns = 14

    coordinate_params = {
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

    coord_params = coordinate_params[options.region]

    x1 = coord_params['x1']
    x_span = coord_params['x_span']
    x_gap = coord_params['x_gap']
    x_tilt = coord_params['x_tilt']

    y1 = coord_params['y1']
    y_len = coord_params['y_len']
    y_sep = coord_params['y_sep']
    y_tilt = coord_params['y_tilt']

    arena = MonitorArea()
    for col in range(0, columns):  # x-coordinates change through columns
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
        for row in range(0, rows):  # y-coordinates change through rows
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

    arena.save_rois(options.mask_file)


if __name__ == '__main__':
    sys.exit(main())
