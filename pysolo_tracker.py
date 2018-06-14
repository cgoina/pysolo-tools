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
    parser.add_argument('--nprocesses', default=1, type=int, dest='nprocesses',
                        help='Number of processes to run in parallel')

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
            source = MovieFile(config.get_source(),
                                     start_msecs=args.start_frame_pos * 1000,
                                     end_msecs=args.end_frame_pos * 1000,
                                     resolution=config.get_image_size())
            if not source.is_opened():
                _logger.error('Error opening %s' % config.get_source())
                return
            start_frame_pos = int(source.get_start_time_in_seconds())
            end_frame_pos = int(source.get_end_time_in_seconds())
            frame_interval = int((end_frame_pos - start_frame_pos) / args.nprocesses)
            tracker_args = [(config, s * 1000, (s + frame_interval) * 1000,
                             args.gaussian_filter_size, args.gaussian_filter_sigma,
                             args.nthreads, _get_run_interval(s, s + frame_interval)[1]) for s in
                            range(start_frame_pos, end_frame_pos, frame_interval)
                            ]
            with Pool(args.nprocesses) as p:
                p.starmap(_run_tracker, tracker_args)
        else:
            _run_tracker(config, args.start_frame_pos * 1000, args.end_frame_pos * 1000,
                         args.gaussian_filter_size, args.gaussian_filter_sigma, args.nthreads)
    else:
        _logger.error('Config load error: %r' % errors)


def _get_run_interval(start_pos, end_pos):

    def start_suffix():
        if start_pos is None or start_pos <= 0:
            return False, '0'
        else:
            return True, '{}'.format(start_pos)

    def end_suffix():
        if end_pos is None or end_pos < 0:
            return False, 'end'
        else:
            return True, '{}'.format(end_pos)

    start = start_suffix()
    end = end_suffix()
    return start[0] or end[0], start[1] + '-' + end[1]


def _run_tracker(config, start_pos_msecs, end_pos_msecs, gaussian_filter_size, gaussian_filter_sigma, nthreads,
                 results_suffix=''):
    subinterval_defined, run_interval = _get_run_interval(start_pos_msecs / 1000, end_pos_msecs / 1000)
    _logger.info('Run tracker for frames between {}'.format(run_interval))

    image_source = MovieFile(config.get_source(),
                             start_msecs=start_pos_msecs,
                             end_msecs=end_pos_msecs,
                             resolution=config.get_image_size())
    if not image_source.is_opened():
        _logger.error('Error opening %s' % config.get_source())
    else:
        if subinterval_defined:
            output_suffix = results_suffix or run_interval
        else:
            output_suffix = results_suffix
        monitored_areas = prepare_monitored_areas(config,
                                                  fps=image_source.get_fps(),
                                                  results_suffix=output_suffix)
        process_image_frames(image_source, monitored_areas,
                             gaussian_filter_size=(gaussian_filter_size, gaussian_filter_size),
                             gaussian_sigma=gaussian_filter_sigma,
                             mp_pool_size=nthreads)
        image_source.close()


if __name__ == '__main__':
    sys.exit(main())
