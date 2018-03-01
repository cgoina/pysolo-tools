#!venv/bin/python

import logging.config
import sys

from optparse import OptionParser
from pysolo_config import Config
from pysolo_video import MovieFile, Arena, process_image_frames


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

    parser = OptionParser(usage='%prog [options] [argument]', version='%prog version 1.0')
    parser.add_option('-c', '--config', dest='config_file', metavar='CONFIG_FILE', help='The full path to the config file to open')
    parser.add_option('-l', '--log-config', default='logger.conf', dest='log_config_file', metavar='LOG_CONFIG_FILE', help='The full path to the log config file to open')
    parser.add_option('--start-frame', default=-1, type=int, dest='start_frame', help='Start frame')
    parser.add_option('--frame-step', default=1, type=int, dest='frame_step', help='Frame step')
    parser.add_option('--video-file', dest='video_file', help='Video file')
    parser.add_option('--mask', dest='mask_file', help='Mask file')

    (options, args) = parser.parse_args()

    # setup logger
    logging.config.fileConfig(options.log_config_file)
    _logger = logging.getLogger('tracker')

    if options.config_file is None:
        _logger.warning('Missing config file')
        parser.exit(1, 'Missing config file\n')

    # load config file
    config = Config()
    config.load_config(options.config_file)
    print("!!!!", config._get_value("Foo", 'bar'), config.get_monitors(), config.get_monitors().get(0).get('source'))

    image_source = MovieFile(config.get_monitors().get(0).get('source'),
                             start=options.start_frame, step=options.frame_step, resolution=config.get_option('fullsize'))
    image_arena = Arena()
    image_arena.load_rois(config.get_monitors().get(1).get('mask_file'))

    process_image_frames(image_source, image_arena)

    image_source.close()


if __name__ == '__main__':
    sys.exit(main())
