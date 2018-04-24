#!/usr/bin/env python

import cv2
import logging.config
import sys
from argparse import ArgumentParser

from pysolo_config import load_config
from pysolo_video import (estimate_background, MovieFile)


def main():
    parser = ArgumentParser(usage='prog [options]')
    parser.add_argument('-c', '--config',
                        dest='config_file', required=True,
                        metavar='CONFIG_FILE', help='The full path to the config file to open')
    parser.add_argument('-l', '--log-config',
                        default='logger.conf', dest='log_config_file',
                        metavar='LOG_CONFIG_FILE', help='The full path to the log config file to open')
    parser.add_argument('--background-image-file',
                        default='background.jpg', dest='background_image_file',
                        help='The full path of the saved background image')
    parser.add_argument('--start-frame-time', default=-1, type=int, dest='start_frame_pos',
                        help='Start frame time in seconds')
    parser.add_argument('--end-frame-time', default=-1, type=int, dest='end_frame_pos',
                        help='End frame time in seconds')
    parser.add_argument('--smooth-filter-size', default=3, type=int, dest='gaussian_filter_size',
                        help='End frame time in seconds')

    args = parser.parse_args()

    # setup logger
    logging.config.fileConfig(args.log_config_file)
    _logger = logging.getLogger('tracker')

    if args.config_file is None:
        _logger.warning('Missing config file')
        parser.exit(1, 'Missing config file\n')

    # load config file
    config, errors = load_config(args.config_file)
    errors |= set(config.validate_source())

    if len(errors) == 0:
        image_source = MovieFile(config.source,
                                 start_msecs=args.start_frame_pos * 1000,
                                 end_msecs=args.end_frame_pos * 1000,
                                 resolution=config.image_size)
        if (image_source.is_opened()):
            background_image = estimate_background(image_source,
                                                   gaussian_filter_size=(args.gaussian_filter_size, args.gaussian_filter_size),
                                                   gaussian_sigma=0)
            cv2.imwrite(args.background_image_file, background_image)
            image_source.close()
        else:
            _logger.error('Error opening %s' % config.source)
    else:
        _logger.error('Config load error: %r' % errors)


if __name__ == '__main__':
    sys.exit(main())
