import configparser
import os

from collections import OrderedDict
from datetime import datetime
from functools import reduce
from itertools import chain


class ConfigOptions:

    def __init__(self):
        self._source = None
        self._source_background_image = None
        self._acq_time = None
        self._data_folder = None
        self._image_size = None
        self._monitored_areas_count = 0
        self._monitored_areas = []
        self._config_filename = None
        self._changed_flag = False

    def get_config_filename(self):
        return self._config_filename

    def set_config_filename(self, config_filename):
        self._config_filename = config_filename

    def get_source(self):
        return self._source

    def set_source(self, source):
        if source != self._source:
            self.set_changed()
            self._source = source

    def get_source_background_image(self):
        return self._source_background_image

    def set_source_background_image(self, source_background_image):
        if source_background_image != self._source_background_image:
            self.set_changed()
            self._source_background_image = source_background_image

    def get_source_background_image_as_display_str(self):
        return "None" if self.get_source_background_image() is None else self.get_source_background_image()

    def get_acq_time(self):
        return self._acq_time

    def set_acq_time(self, acq_time):
        if acq_time != self._acq_time:
            self.set_changed()
            self._acq_time = acq_time

    def get_acq_time_as_str(self):
        if self.get_acq_time():
            return datetime.strftime(self.get_acq_time(), '%Y-%m-%d %H:%M:%S')
        else:
            return ''

    def set_acq_time_from_str(self, time_str):
        if time_str and time_str.strip():
            try:
                self.set_acq_time(datetime.strptime(time_str.strip(), '%Y-%m-%d %H:%M:%S'))
            except ValueError:
                pass  # ignore the exception
        else:
            self.set_acq_time(None)

    def get_data_folder(self):
        return self._data_folder

    def set_data_folder(self, data_folder):
        if data_folder != self._data_folder:
            self.set_changed()
            self._data_folder = data_folder

    def get_image_width(self):
        if self.get_image_size() is None:
            return 0
        else:
            return self.get_image_size()[0]

    def set_image_width(self, w):
        if self.get_image_size() is None:
            self.set_image_size((w, 0))
        else:
            self.set_image_size((w, self.get_image_height()))

    def get_image_height(self):
        if self.get_image_size() is None:
            return 0
        else:
            return self.get_image_size()[1]

    def set_image_height(self, h):
        if self.get_image_size() is None:
            self.set_image_size((0, h))
        else:
            self.set_image_size((self.get_image_width(), h))

    def get_image_size(self):
        return self._image_size

    def set_image_size(self, image_size):
        if image_size != self._image_size:
            self.set_changed()
            self._image_size = image_size

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
        return self._monitored_areas[:self.get_monitored_areas_count()]

    def get_monitored_areas_count(self):
        return self._monitored_areas_count

    def set_monitored_areas_count(self, monitored_areas_count):
        self._monitored_areas_count = monitored_areas_count
        if self.get_monitored_areas_count() >= 0:
            if len(self._monitored_areas) < self.get_monitored_areas_count():
                self.set_changed()
                for i in range(0, self.get_monitored_areas_count() - len(self._monitored_areas)):
                    self._monitored_areas.append(MonitoredAreaOptions())

    def validate(self):
        errors = self.validate_source()
        if self._monitored_areas_count == 0:
            errors.append('Number of monitored areas must be greater than 0')
        elif len(self._monitored_areas) < self._monitored_areas_count:
            errors.append('Number of monitored areas cannot be greater than the number of configured areas')

        def monitored_area_validation(monitored_area, monitored_area_index):
            return ['Region %d: %s' % (monitored_area_index + 1, err) for err in monitored_area.validate()]

        return errors + list(chain.from_iterable([monitored_area_validation(a, ai)
                                                  for ai, a in enumerate(self.get_monitored_areas())]))

    def validate_source(self):
        errors = []
        if not self._source:
            errors.append('Video source file is not defined')
        elif not os.path.exists(self._source):
            # file does not exist
            errors.append('Video source file %s does not exist' % self._source)
        if not self.get_image_size():
            errors.append('Image size has not been set')
        if self.get_image_width() == 0:
            errors.append('Image width cannot be 0')
        if self.get_image_height() == 0:
            errors.append('Image height cannot be 0')
        return errors

    def set_changed(self):
        self._changed_flag = True

    def reset_changed(self):
        self._changed_flag = False
        for ma in self.get_monitored_areas():
            ma.reset_changed()

    def has_changed(self):
        return self._changed_flag or reduce(lambda x, y: x or y, [ma.has_changed() for ma in self.get_monitored_areas()])

    def as_dict(self):
        config_sections = [
            (
                'Options',
                OrderedDict([
                    ('source', self.get_source()),
                    ('source_background_image', self.get_source_background_image_as_display_str()),
                    ('acq_time', self.get_acq_time_as_str()),
                    ('data_folder', self.get_data_folder()),
                    ('fullsize', ', '.join([str(x) for x in self.get_image_size()])),
                    ('monitors', str(self.get_monitored_areas_count()))
                ])
            )
        ]
        for i in range(0, self.get_monitored_areas_count()):
            config_sections.append(('Monitor%d' % (i + 1), self.get_monitored_area(i).as_dict()))

        return OrderedDict(config_sections)


class MonitoredAreaOptions:

    def __init__(self):
        self._maskfile = None
        self._track_flag = True
        self._track_type = 0
        self._sleep_deprived_flag = False
        self._aggregation_interval = 60  # default to 60 frames
        self._aggregation_interval_units = 'frames'  # valid values: frames, sec, min
        self._tracked_rois_filter = None
        self._extend_flag = True
        self._changed_flag = False

    def get_maskfile(self):
        return self._maskfile

    def set_maskfile(self, maskfile):
        if maskfile != self._maskfile:
            self.set_changed()
            self._maskfile = maskfile

    def get_track_flag(self):
        return self._track_flag

    def set_track_flag(self, track_flag):
        if track_flag != self._track_flag:
            self.set_changed()
            self._track_flag = track_flag

    def get_track_type(self):
        return self._track_type

    def set_track_type(self, track_type):
        if track_type != self._track_type:
            self.set_changed()
            self._track_type = track_type

    def get_sleep_deprived_flag(self):
        return self._sleep_deprived_flag

    def set_sleep_deprived_flag(self, sleep_deprived_flag):
        if sleep_deprived_flag != self._sleep_deprived_flag:
            self.set_changed()
            self._sleep_deprived_flag = sleep_deprived_flag

    def get_aggregation_interval(self):
        return self._aggregation_interval

    def set_aggregation_interval(self, aggregation_interval):
        if aggregation_interval != self._aggregation_interval:
            self.set_changed()
            self._aggregation_interval = aggregation_interval

    def get_aggregation_interval_units(self):
        return self._aggregation_interval_units

    def set_aggregation_interval_units(self, aggregation_interval_units):
        if aggregation_interval_units != self._aggregation_interval_units:
            self.set_changed()
            self._aggregation_interval_units = aggregation_interval_units

    def get_aggregation_interval_in_frames(self, fps):
        """
        Convert the aggregation interval in number of frames to be aggregated
        :param fps: frames per second
        :return:
        """
        if self.get_aggregation_interval() is None:
            return 1  # default to 1 if no aggregation interval is specified
        if self.get_aggregation_interval_units() == 'sec':  # seconds
            return int(self.get_aggregation_interval() * fps)
        elif self.get_aggregation_interval_units() == 'min':  # minutes
            return int(self.get_aggregation_interval() * 60 * fps)
        else:  # default to frames
            return int(self.get_aggregation_interval())

    def get_tracked_rois_filter(self):
        return self._tracked_rois_filter

    def set_tracked_rois_filter(self, tracked_rois_filter):
        if tracked_rois_filter != self._tracked_rois_filter:
            self.set_changed()
            self._tracked_rois_filter = tracked_rois_filter

    def get_rois_filter_as_str(self):
        if self.get_tracked_rois_filter() is None:
            return ''
        else:
            return ', '.join([str(roi + 1) for roi in self.get_tracked_rois_filter()])

    def set_rois_filter_as_str(self, rois_filter_str):
        if rois_filter_str and rois_filter_str.strip():
            vals = [val for val in rois_filter_str.split(',') if val and val.strip()]
            self.set_tracked_rois_filter([int(val) - 1 for val in vals])
        else:
            self.set_tracked_rois_filter(None)

    def get_extend_flag(self):
        return self._extend_flag

    def set_extend_flag(self, extend_flag):
        if extend_flag != self._extend_flag:
            self.set_changed()
            self._extend_flag = extend_flag

    def validate(self):
        errors = []
        if not self.get_maskfile():
            errors.append('Mask file has not been set')
        elif not os.path.exists(self.get_maskfile()):
            # file does not exist
            errors.append('Mask file %s does not exist' % self.get_maskfile())
        if self.get_track_type() not in [0, 1, 2]:
            errors.append('Track type: %d is not a valid value' % self.get_track_type())
        if self.get_aggregation_interval() <= 0:
            errors.append('Aggregation interval: %d must be a positive number' % self.get_aggregation_interval())
        if self.get_aggregation_interval_units() not in [None, 'frames', 'sec', 'min']:
            errors.append('Invalid aggregation interval unit: %s' % self.get_aggregation_interval_units())

        return errors

    def set_changed(self):
        self._changed_flag = True

    def reset_changed(self):
        self._changed_flag = False

    def has_changed(self):
        return self._changed_flag

    def as_dict(self):
        return OrderedDict([
            ('maskfile', str(self.get_maskfile())),
            ('track', str(self.get_track_flag())),
            ('tracktype', str(self.get_track_type())),
            ('issdmonitor', str(self.get_sleep_deprived_flag())),
            ('tracked_rois_filter', self.get_rois_filter_as_str()),
            ('aggregation_interval', self.get_aggregation_interval()),
            ('aggregation_interval_units', self.get_aggregation_interval_units())
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

    def get_value(section, key, default_value=None, required=True, use_default_converter=True):
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
        return _convert_val(val) if use_default_converter else val

    config.set_source(get_value('Options', 'source'))
    config.set_source_background_image(get_value('Options', 'source_background_image', required=False))
    config.set_acq_time_from_str(get_value('Options', 'acq_time', required=False, use_default_converter=False))
    config.set_data_folder(get_value('Options', 'data_folder'))
    config.set_image_size(get_value('Options', 'fullsize'))
    config.set_monitored_areas_count(get_value('Options', 'monitors'))

    for monitored_area_index in range(0, config.get_monitored_areas_count()):
        monitored_area = config.get_monitored_area(monitored_area_index)
        monitored_area_section = 'Monitor%d' % (monitored_area_index + 1)
        monitored_area.set_maskfile(get_value(monitored_area_section, 'maskfile'))
        monitored_area.set_track_flag(get_value(monitored_area_section, 'track', default_value=True))
        monitored_area.set_track_type(get_value(monitored_area_section, 'tracktype'))
        monitored_area.set_sleep_deprived_flag(get_value(monitored_area_section, 'issdmonitor', default_value=False))
        monitored_area.set_extend_flag(get_value(monitored_area_section, 'extend', default_value=True, required=False))
        tracked_rois_filter = get_value(monitored_area_section, 'tracked_rois_filter', required=False)
        if type(tracked_rois_filter) is tuple:
            monitored_area.set_tracked_rois_filter(list(tracked_rois_filter))
        elif type(tracked_rois_filter) is int:
            monitored_area.set_tracked_rois_filter([tracked_rois_filter])
        elif tracked_rois_filter is not None:
            errors.append('Cannot handle tracked ROI filter: {arg}'.format(arg=tracked_rois_filter))
        monitored_area.set_aggregation_interval(get_value(monitored_area_section, 'aggregation_interval',
                                                          default_value=60))
        monitored_area.set_aggregation_interval_units(get_value(monitored_area_section, 'aggregation_interval_units',
                                                                default_value='frames'))

    config.reset_changed()
    return config, set(errors)


def _convert_val(val):
    vals = [v for v in val.split(',') if v and v.strip()]
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
        except ValueError:
            return val


def save_config(config, filename):
    config_parser = configparser.ConfigParser()
    errors = config.validate()
    if not errors:
        config_parser.read_dict(config.as_dict())
        with open(filename, 'w') as configfile:
            config_parser.write(configfile)
        config.reset_changed()
    return errors
