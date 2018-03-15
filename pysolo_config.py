import configparser
import os
from collections import OrderedDict
from itertools import chain


class ConfigOptions:

    def __init__(self):
        self.source = None
        self.data_folder = None
        self.image_size = None
        self.monitored_areas_count = 0
        self._monitored_areas = []

    def add_monitored_area(self, monitored_area):
        if monitored_area is not None:
            self._monitored_areas.append(monitored_area)

    def get_monitored_area(self, monitored_area_index):
        """
        Retrieved the specified monitored area. If the index is not between [0, len(_monitored_areas) it returns None
        :param monitored_area_index:
        :return:
        """
        if monitored_area_index < 0 or monitored_area_index >= len(self._monitored_areas):
            return None
        else:
            return self._monitored_areas[monitored_area_index]

    def get_monitored_areas(self):
        return self._monitored_areas[:self.monitored_areas_count]

    def set_monitored_areas_count(self, monitor_areas_count):
        if monitor_areas_count >= 0:
            self.monitored_areas_count = monitor_areas_count
            if len(self._monitored_areas) < self.monitored_areas_count:
                for i in range(0, self.monitored_areas_count - len(self._monitored_areas)):
                    self.add_monitored_area(MonitoredAreaOptions())

    def validate(self):
        errors = []
        if self.monitored_areas_count == 0:
            errors.append('Number of monitored areas must be greater than 0')
        elif len(self._monitored_areas) < self.monitored_areas_count:
            errors.append('Number of monitored areas cannot be greater than the number of configured areas')

        def monitored_area_validation(monitored_area, monitored_area_index):
            return ['Region %d: %s' % (monitored_area_index, err) for err in monitored_area.validate()]

        return errors + list(chain.from_iterable([monitored_area_validation(a, ai) for ai, a in enumerate(self.get_monitored_areas())]))

    def _asdict(self):
        config_sections = [
            (
                'Options',
                OrderedDict([
                    ('source', self.source),
                    ('data_folder', self.data_folder),
                    ('fullsize', ', '.join([str(x) for x in self.image_size])),
                    ('monitors', str(self.monitored_areas_count))
                ])
            )
        ]
        for i in range(0, self.monitored_areas_count):
            config_sections.append(('Monitor%d' % i, self.get_monitored_area(i)._asdict()))

        return OrderedDict(config_sections)


class MonitoredAreaOptions:

    def __init__(self):
        self.maskfile = None
        self.track_flag = False
        self.track_type = 0
        self.sleep_deprived_flag = False
        self.tracked_rois_filter = None
        self.aggregation_interval = 60 # default to 60 frames
        self.aggregation_interval_units = 'frames' # valid values: frames, sec, min

    def get_aggregation_interval_in_frames(self, fps):
        """
        Convert the aggregation interval in number of frames to be aggregated
        :param fps: frames per second
        :return:
        """
        if self.aggregation_interval is None:
            return 1 # default to 1 if no aggregation interval is specified
        if self.aggregation_interval_units == 'sec': # seconds
            return int(self.aggregation_interval * fps)
        elif self.aggregation_interval_units == 'min': # minutes
            return int(self.aggregation_interval * 60 * fps)
        else: # default to frames
            return int(self.aggregation_interval)

    def validate(self):
        errors = []
        if not self.maskfile:
            errors.append('Mask file has not been set')
        elif not os.path.exists(self.maskfile):
            # file does not exist
            errors.append('Mask file %s does not exist' %  self.maskfile)
        if self.track_type not in [0, 1, 2]:
            errors.append('Track type: %d is not a valid value' % self.track_type)
        if self.aggregation_interval <= 0:
            errors.append('Aggregation interval: %d must be a positive number' % self.aggregation_interval)
        if self.aggregation_interval_units not in [None, 'frames', 'sec', 'min']:
            errors.append('Invalid aggregation interval unit: %s' % self.aggregation_interval_units)

        return errors

    def _asdict(self):
        return OrderedDict([
            ('maskfile', str(self.maskfile)),
            ('tracktype', str(self.track_type)),
            ('issdmonitor', str(self.sleep_deprived_flag)),
            ('tracked_rois_filter', str(self.tracked_rois_filter)
                    if self.tracked_rois_filter is None
                    else ', '.join([str(r) for r in self.tracked_rois_filter])),
            ('aggregation_interval', self.aggregation_interval),
            ('aggregation_interval_units', self.aggregation_interval_units)
        ])


def load_config(filename):
    errors = []

    if not os.path.exists(filename):
        # file does not exist
        errors.append('Config file %s not found' % filename)
        return None, errors

    config_parser = configparser.ConfigParser()
    config_parser.read(filename)

    config = ConfigOptions()

    def get_value(section, key, default_value=None, required=True):
        if not config_parser.has_section(section):
            errors.append('Section %s not found in file %s' % (section, filename))
            return None

        if not config_parser.has_option(section, key):
            if default_value is not None or not required:
                return default_value
            else:
                errors.append('Key %s not found in section %s in file %s' % (key, section, filename))
                return None

        val = config_parser.get(section, key)
        return _convert_val(val)

    config.source = get_value('Options', 'source')
    config.data_folder = get_value('Options', 'data_folder')
    config.image_size = get_value('Options', 'fullsize')
    config.set_monitored_areas_count(get_value('Options', 'monitors'))

    for monitored_area_index in range(0, config.monitored_areas_count):
        monitored_area = config.get_monitored_area(monitored_area_index)
        monitored_area_section = 'Monitor%d' % monitored_area_index
        monitored_area.maskfile = get_value(monitored_area_section, 'maskfile')
        monitored_area.track_flag = get_value(monitored_area_section, 'track', default_value=True)
        monitored_area.track_type = get_value(monitored_area_section, 'tracktype')
        monitored_area.sleep_deprived_flag = get_value(monitored_area_section, 'issdmonitor', default_value=False)
        tracked_rois_filter = get_value(monitored_area_section, 'tracked_rois_filter', required=False)
        if type(tracked_rois_filter) is tuple:
            monitored_area.tracked_rois_filter = list(tracked_rois_filter)
        elif type(tracked_rois_filter) is int:
            monitored_area.tracked_rois_filter = [tracked_rois_filter]
        elif tracked_rois_filter is not None:
            errors.append('Cannot handle tracked ROI filter: {arg}'.format(arg=tracked_rois_filter))
        monitored_area.aggregation_interval = get_value(monitored_area_section, 'aggregation_interval', default_value=60)
        monitored_area.aggregation_interval_units = get_value(monitored_area_section, 'aggregation_interval_units', default_value='frames')

    return config, errors


def _convert_val(val):
    vals = val.split(',')
    if len(vals) == 1:
        return _convert_simple_val(val)
    else:
        return tuple([_convert_simple_val(v) for v in vals])


def _convert_simple_val(val):
    if val == '':
        return ''
    elif val == 'None':
        return None
    elif val == 'True' or val == 'False':
        return val == 'True'
    else:
        try:
            return int(val)
        except:
            return val


def save_config(config, filename):
    config_parser = configparser.ConfigParser()
    config_parser.read_dict(config._asdict())
    with open(filename, 'w') as configfile:
        config_parser.write(configfile)
