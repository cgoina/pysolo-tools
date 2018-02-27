import configparser
import errno
import logging
import os


def _convert_val(val):
    vals = val.split(',')
    if len(vals) == 1:
        return _convert_simple_val(val)
    else:
        return tuple([_convert_simple_val(v) for v in vals])


def _convert_simple_val(val):
    if val == '':
        return ''
    elif val == 'True' or val == 'False':
        return val == 'True'
    else:
        try:
            return int(val)
        except:
            return val


class Config:
    _monitor_properties = ['sourceType', 'source', 'track', 'maskfile', 'trackType', 'isSDMonitor']

    def __init__(self):
        self._config_filename = None
        self._config = None
        self._logger = logging.getLogger('config')

    def load_config(self, filename):
        if not os.path.exists(filename):
            # file does not exist
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), filename)

        self._logger.info('Loading config file %r' % filename)
        self._config_filename = filename
        self._config = configparser.ConfigParser()
        self._config.read(filename)

    def _get_value(self, section, key):
        if not self._config.has_section(section):
            self._logger.warning('Section %s is not present in config file %s' % (section, self._config_filename))
            return None

        if not self._config.has_option(section, key):
            self._logger.warning('Section %s is present in config file %s but no value found for key %s' % (section, self._config_filename, key))
            return None

        val = self._config.get(section, key)
        return _convert_val(val)

    def _get_option(self, key):
        return self._get_value('Options', key)

    def _get_monitor_section(self, monitor_index):
        return 'Monitor%s' % monitor_index

    def _get_monitor_data(self, monitor_index):
        monitor_section = self._get_monitor_section(monitor_index)
        if self._config.has_section(monitor_section):
            return {monitor_property: self._get_value(monitor_section, monitor_property) for monitor_property in
                    Config._monitor_properties}
        else:
            return {}

    def get_monitors(self):
        monitors = {}

        n_monitors = self._get_option('monitors')
        image_size = self._get_option('fullsize')
        data_folder = self._get_option('data_folder')

        for mon in range(0, n_monitors):
            monitor_section = self._get_monitor_section(mon)
            if self._config.has_section(monitor_section):
                monitor_data = self._get_monitor_data(mon)
                monitors[mon] = {}
                monitors[mon]['source'] = monitor_data.get('source')
                monitors[mon]['resolution'] = image_size
                monitors[mon]['mask_file'] = monitor_data.get('maskfile')
                monitors[mon]['track_type'] = monitor_data.get('trackType')
                monitors[mon]['dataFolder'] = data_folder
                monitors[mon]['track'] = monitor_data.get('track')
                monitors[mon]['isSDMonitor'] = monitor_data.get('isSDMonitor')

        return monitors
