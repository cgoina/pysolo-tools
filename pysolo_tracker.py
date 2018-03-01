#!/usr/bin/env python

import logging.config
import os
import sys

from argparse import ArgumentParser
from pysolo_config import Config
from pysolo_video import MovieFile, MonitorArea, process_image_frames


def track(image_source, input_mask_file, output_result_file, tracking_type=1):
    """

    :param image_source: image source - this can be a camera or a movie file
    :param input_mask_file: path to the mask file
    :param tracking_type: 0 - track using the virtual beam method
                          1 (Default) calculate distance moved
    :param output_result_file: where to store the results
    :return:
    """


def main():
    global _logger

    parser = ArgumentParser(usage='prog [options]')
    parser.add_argument('-c', '--config', dest='config_file', metavar='CONFIG_FILE', help='The full path to the config file to open')
    parser.add_argument('-l', '--log-config', default='logger.conf', dest='log_config_file', metavar='LOG_CONFIG_FILE', help='The full path to the log config file to open')
    parser.add_argument('--start-frame', default=-1, type=int, dest='start_frame', help='Start frame')
    parser.add_argument('--frame-step', default=1, type=int, dest='frame_step', help='Frame step')
    parser.add_argument('--video-file', dest='video_file', help='Video file')
    parser.add_argument('--mask', dest='mask_file', help='Mask file')

    args = parser.parse_args()

    # setup logger
    logging.config.fileConfig(args.log_config_file)
    _logger = logging.getLogger('tracker')

    if args.config_file is None:
        _logger.warning('Missing config file')
        parser.exit(1, 'Missing config file\n')

    # load config file
    config = Config()
    config.load_config(args.config_file)


    image_source = MovieFile(config.get_monitors().get(0).get('source'),
                             start=args.start_frame,
                             step=args.frame_step,
                             resolution=config.get_option('fullsize'))

    def create_monitor_area(monitor_index):
        monitor_area = MonitorArea()
        monitor_area.load_rois(config.get_monitors().get(monitor_index).get('mask_file'))
        monitor_area.set_output(
            os.path.join(config.get_monitors().get(monitor_index).get('dataFolder'), 'Monitor%02d.txt' % monitor_index)
        )
        return monitor_area

    process_image_frames(image_source, [create_monitor_area(i) for i in [0, 1, 2, 3]])

    image_source.close()


if __name__ == '__main__':
    sys.exit(main())
