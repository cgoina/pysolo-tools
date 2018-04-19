#!/usr/bin/env python

import cv2
import logging.config
import os
import sys
from argparse import ArgumentParser

from multiprocess.pool import Pool

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
    parser.add_argument('--nprocesses', default=1, type=int, dest='nprocesses')

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
        if args.nprocesses > 1:
            source = MovieFile(config.source,
                                     start_msecs=args.start_frame_pos * 1000,
                                     end_msecs=args.end_frame_pos * 1000,
                                     resolution=config.image_size)
            if not source.is_opened():
                _logger.error('Error opening %s' % config.source)
                return
            start_frame_pos = int(source.get_start_time_in_seconds())
            end_frame_pos = int(source.get_end_time_in_seconds())
            frame_interval = int((end_frame_pos - start_frame_pos) / args.nprocesses)
            tracker_args = [(config, s * 1000, (s + frame_interval) * 1000,
                             args.gaussian_filter_size, args.gaussian_filter_sigma,
                             args.nthreads, _create_results_suffix(s, s + frame_interval)) for s in
                            range(start_frame_pos, end_frame_pos, frame_interval)
                            ]
            with Pool(args.nprocesses) as p:
                p.starmap(_run_tracker, tracker_args)
        else:
            _run_tracker(config, args.start_frame_pos * 1000, args.end_frame_pos * 1000,
                         args.gaussian_filter_size, args.gaussian_filter_sigma, args.nthreads)
    else:
        _logger.error('Config load error: %r' % errors)


def _create_results_suffix(start_pos, end_pos):
    start = '0' if start_pos is None or start_pos < 0 else '%d' % start_pos
    end = 'end' if end_pos is None or end_pos < 0 else '%d' % end_pos
    return start + '-' + end


def _run_tracker(config, start_pos_msecs, end_pos_msecs, gaussian_filter_size, gaussian_filter_sigma, nthreads,
                 results_suffix=''):
    _logger.info('Run tracker for frames between %s' % (
        results_suffix if results_suffix else _create_results_suffix(start_pos_msecs / 1000, end_pos_msecs / 1000)))
    image_source = MovieFile(config.source,
                             start_msecs=start_pos_msecs,
                             end_msecs=end_pos_msecs,
                             resolution=config.image_size)
    if not image_source.is_opened():
        _logger.error('Error opening %s' % config.source)
    else:
        monitored_areas = prepare_monitored_areas(image_source, config, results_suffix=results_suffix)
        process_image_frames(image_source, monitored_areas,
                             gaussian_filter_size=(gaussian_filter_size, gaussian_filter_size),
                             gaussian_sigma=gaussian_filter_sigma,
                             mp_pool_size=nthreads)
        image_source.close()


if __name__ == '__main__':
    sys.exit(main())
