#!/usr/bin/env python

import logging.config
import os
import sys

from argparse import ArgumentParser
from _datetime import datetime
from pysolo_config import load_config
from pysolo_video import (MovieFile, MonitoredArea, process_image_frames)


def main():
    global _logger

    parser = ArgumentParser(usage='prog [options]')
    parser.add_argument('-c', '--config',
                        dest='config_file', required=True,
                        metavar='CONFIG_FILE', help='The full path to the config file to open')
    parser.add_argument('-l', '--log-config',
                        default='logger.conf', dest='log_config_file',
                        metavar='LOG_CONFIG_FILE', help='The full path to the log config file to open')
    parser.add_argument('--start-frame', default=-1, type=int, dest='start_frame', help='Start frame')
    parser.add_argument('--frame-step', default=1, type=int, dest='frame_step', help='Frame step')
    parser.add_argument('--end-frame', default=-1, type=int, dest='end_frame', help='End frame')
    parser.add_argument('-v', '--video-file', dest='video_file', help='Video file')
    parser.add_argument('-m', '--mask', dest='mask_file', help='Mask file')
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

    video_file = args.video_file or config.source
    image_source = MovieFile(video_file,
                             start=args.start_frame,
                             step=args.frame_step,
                             end=args.end_frame,
                             resolution=config.image_size)

    def create_monitor_area(monitor_index):
        monitor_config_options = config.get_monitored_area(monitor_index)
        monitored_area = MonitoredArea(monitor_config_options.track_type,
                                     monitor_config_options.sleep_deprived_flag,
                                     fps=image_source.get_fps(),
                                     acq_time=args.acq_time)
        if monitor_config_options.tracked_rois_filter:
            monitored_area.set_roi_filter(monitor_config_options.tracked_rois_filter)
        monitored_area.load_rois(monitor_config_options.maskfile)
        monitored_area.set_output(
            os.path.join(config.data_folder, 'Monitor%02d.txt' % monitor_index)
        )
        return monitored_area

    process_image_frames(image_source, [create_monitor_area(i) for i in [0, 1, 2]])

    image_source.close()


if __name__ == '__main__':
    sys.exit(main())
