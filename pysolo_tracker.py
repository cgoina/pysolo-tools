#!/usr/bin/env python

import cv2
import logging.config
import os
import sys
from argparse import ArgumentParser

from pysolo_config import load_config
from pysolo_video import (process_image_frames, prepare_monitored_areas)


def main():
    parser = ArgumentParser(usage='prog [options]')
    parser.add_argument('-c', '--config',
                        dest='config_file', required=True,
                        metavar='CONFIG_FILE', help='The full path to the config file to open')
    parser.add_argument('-l', '--log-config',
                        default='logger.conf', dest='log_config_file',
                        metavar='LOG_CONFIG_FILE', help='The full path to the log config file to open')
    parser.add_argument('--start-frame-time', default=-1, type=int, dest='start_frame_pos',
                        help='Start frame time in seconds')
    parser.add_argument('--end-frame-time', default=-1, type=int, dest='end_frame_pos',
                        help='End frame time in seconds')
    parser.add_argument('--smooth-filter-size', default=3, type=int, dest='gaussian_filter_size',
                        help='Gaussian filter kernel size')
    parser.add_argument('--smooth-filter-sigma', default=0, type=int, dest='gaussian_filter_sigma',
                        help='Gaussian filter sigma')
    parser.add_argument('--nthreads', default=1, type=int, dest='nthreads')

    args = parser.parse_args()

    # setup logger
    logging.config.fileConfig(args.log_config_file)
    _logger = logging.getLogger('tracker')

    if args.config_file is None:
        _logger.warning('Missing config file')
        parser.exit(1, 'Missing config file\n')

    # load config file
    config, errors = load_config(args.config_file)
    errors |= set(config.validate())

    if len(errors) == 0:
        image_source, monitored_areas = prepare_monitored_areas(config,
                                                                start_frame_msecs=args.start_frame_pos * 1000,
                                                                end_frame_msecs=args.end_frame_pos * 1000)
        if (image_source.is_opened()):
            background_image = None
            if config.source_background_image and os.path.exists(config.source_background_image):
                background_image = cv2.imread(config.source_background_image)
            process_image_frames(image_source, monitored_areas,
                                 gaussian_filter_size=(args.gaussian_filter_size, args.gaussian_filter_size),
                                 gaussian_sigma=args.gaussian_filter_sigma,
                                 mp_pool_size=args.nthreads)
            image_source.close()
        else:
            _logger.error('Error opening %s' % config.source)
    else:
        _logger.error('Config load error: %r' % errors)


if __name__ == '__main__':
    sys.exit(main())
