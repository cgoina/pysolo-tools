#!/usr/bin/env python

import logging.config
import sys
from _datetime import datetime
from argparse import ArgumentParser

from pysolo_config import load_config
from pysolo_video import (MovieFile, MonitoredArea, process_image_frames, prepare_monitored_areas)


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
        process_image_frames(image_source, monitored_areas, mp_pool_size=args.nthreads)
        image_source.close()
    else:
        _logger.error('Config load error: %r' % errors)


if __name__ == '__main__':
    sys.exit(main())
