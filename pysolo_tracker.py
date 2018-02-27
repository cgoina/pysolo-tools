#!venv/bin/python

import configparser
import logging.config
import os
import sys

from optparse import OptionParser

def load_config(filename):
    if not os.path.exists(filename):
        # file does not exist
        _logger.warning('The specified config file: %r does not exist' % filename)
        sys.exit(1)
    config = configparser.ConfigParser()
    config.read(filename)
    return config


def main():
    global _logger

    parser = OptionParser(usage='%prog [options] [argument]', version='%prog version 1.0')
    parser.add_option('-c', '--config', dest='config_file', metavar="CONFIG_FILE", help="The full path to the config file to open")
    parser.add_option('-l', '--log-config', default='logger.conf', dest='log_config_file', metavar="LOG_CONFIG_FILE", help="The full path to the log config file to open")

    (options, args) = parser.parse_args()

    # setup logger
    logging.config.fileConfig(options.log_config_file)
    _logger = logging.getLogger('tracker')

    # load config file
    load_config(options.config_file)



if __name__ == '__main__':
    sys.exit(main())
