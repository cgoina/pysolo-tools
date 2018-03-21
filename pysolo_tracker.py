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
    parser.add_argument('--start-frame', default=-1, type=int, dest='start_frame', help='Start frame')
    parser.add_argument('--end-frame', default=-1, type=int, dest='end_frame', help='End frame')
    parser.add_argument('-t', '--acq-time', dest='acq_time',
                        type=lambda s: datetime.strptime(s, '%Y-%m-%d %H:%M:%S'),
                        help='Acquisition time - format YYYY-dd-MM HH:mm:ss')

    args = parser.parse_args()

    # setup logger
    logging.config.fileConfig(args.log_config_file)
    _logger = logging.getLogger('tracker')

    if args.config_file is None:
        _logger.warning('Missing config file')
        parser.exit(1, 'Missing config file\n')

    # load config file
    config, errors = load_config(args.config_file)

    if len(errors) == 0:
        image_source, monitored_areas = prepare_monitored_areas(config,
                                                                start_frame_msecs=args.start_frame,
                                                                end_frame_msecs=args.end_frame)
        process_image_frames(image_source, monitored_areas)
        image_source.close()


if __name__ == '__main__':
    sys.exit(main())
