#!/usr/bin/env python

import cv2
import logging.config
import os
import sys
from argparse import ArgumentParser

from pysolo_config import load_config
from pysolo_video import (process_image_frames, prepare_monitored_areas, MovieFile)


_logger = None


def main():
    global _logger
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
        _run_tracker(config, args.start_frame_pos * 1000, args.end_frame_pos * 1000,
                     args.gaussian_filter_size, args.gaussian_filter_sigma, args.nthreads)
    else:
        _logger.error('Config load error: %r' % errors)


def _run_tracker(config, start_pos_msecs, end_pos_msecs, gaussian_filter_size, gaussian_filter_sigma, nthreads):
    image_source = MovieFile(config.source,
                             start_msecs=start_pos_msecs,
                             end_msecs=end_pos_msecs,
                             resolution=config.image_size)
    if not image_source.is_opened():
        _logger.error('Error opening %s' % config.source)
    else:
        monitored_areas = prepare_monitored_areas(image_source, config)
        process_image_frames(image_source, monitored_areas,
                             gaussian_filter_size=(gaussian_filter_size, gaussian_filter_size),
                             gaussian_sigma=gaussian_filter_sigma,
                             mp_pool_size=nthreads)
        image_source.close()


if __name__ == '__main__':
    sys.exit(main())
