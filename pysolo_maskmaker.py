#!venv/bin/python

import sys

from optparse import OptionParser
from pysolo_video import Arena


def main():
    parser = OptionParser(usage='%prog [options] [argument]', version='%prog version 1.0')
    parser.add_option('-m', '--mask-file', dest='mask_file', metavar='MASK_FILE', help='The full name of the mask file')

    (options, args) = parser.parse_args()

    rows = 1
    columns = 14

    ################  COORDINATE SECTIONS ########################
    # ----------------------------------- Upper Left
    """
    x1 = 191.5
    x_span = 8
    x_gap = 3.75
    x_tilt = 0

    y1 = 205
    y_len = 50
    y_sep = 2
    y_tilt = 0

    """
    # ----------------------------------- Lower Left
    """
    x1 = 194
    x_span = 8
    x_gap = 3.75
    x_tilt = 0

    y1 = 298
    y_len = 50
    y_sep = 2
    y_tilt = 0
    """
    # ------------------------------------ Upper Right
    """
    x1 = 376
    x_span = 7.75
    x_gap = 4.2
    x_tilt = 0

    y1 = 206
    y_len = 50
    y_sep = 2
    y_tilt = 0
    """
    # -------------------------------------- Lower Right
    """
    x1 = 379
    x_span = 7.7
    x_gap = 4.1
    x_tilt = 0

    y1 = 300
    y_len = 45
    y_sep = 2
    y_tilt = 0
    """

    x1 = 194
    x_span = 8
    x_gap = 3.75
    x_tilt = 0

    y1 = 298
    y_len = 50
    y_sep = 2
    y_tilt = 0

    arena = Arena()
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
            arena.add_roi((ax, ay, bx, by, cx, cy, dx, dy))

            ay = by + y_sep  # move down in y direction to start next row
            by = ay + y_len
            cy = by
            dy = ay
            ax = ax + x_tilt
            bx = ax
            cx = ax + x_span
            dx = cx

    arena.save_rois(options.mask_file)
    # with open(, 'wb') as mfh:
    #     ROI = 1
    #     for col in range(0, columns):  # x-coordinates change through columns
    #         ay = y1 + col * y_tilt  # reset y-coordinate start of col
    #         by = ay + y_len
    #         cy = by
    #         dy = ay
    #         if col == 0:
    #             ax = x1
    #         else:
    #             ax = x1 + col * (x_span + x_gap)  # move over in x direction to start next column
    #         bx = ax
    #         cx = ax + x_span
    #         dx = cx
    #         for row in range(0, rows):  # y-coordinates change through rows
    #             if (row == 0 and col == 0):  # 1st ROI in the mask special treatment
    #                 mfh.write('(lp1\n((I%d\nI%d\nt(I%d\nI%d\nt(I%d\nI%d\nt(I%d\nI%d\n' % (ax, ay, bx, by, cx, cy, dx, dy))
    #                 print('(lp1\n((I%d\nI%d\nt(I%d\nI%d\nt(I%d\nI%d\nt(I%d\nI%d\n' % (ax, ay, bx, by, cx, cy, dx, dy))
    #             else:
    #                 mfh.write('ttp%d\na((I%d\nI%d\nt(I%d\nI%d\nt(I%d\nI%d\nt(I%d\nI%d\n' % (ROI, ax, ay, bx, by, cx, cy, dx, dy))
    #                 print('ttp%d\na((I%d\nI%d\nt(I%d\nI%d\nt(I%d\nI%d\nt(I%d\nI%d\n' % (ROI, ax, ay, bx, by, cx, cy, dx, dy))
    #
    #             ay = by + y_sep  # move down in y direction to start next row
    #             by = ay + y_len
    #             cy = by
    #             dy = ay
    #             ax = ax + x_tilt
    #             bx = ax
    #             cx = ax + x_span
    #             dx = cx
    #             ROI = ROI + 1
    #
    #     mfh.write('ttp%d\na.(lp1\nI1\n' % (ROI + 1))
    #     mfh.write('aI1\n' * (columns * rows - 1))
    #     mfh.write('a.\n\n\n')


if __name__ == '__main__':
    sys.exit(main())
