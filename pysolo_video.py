import cv2
import itertools
import logging
import numpy as np
import os
import pickle

from datetime import datetime, timedelta
from enum import Enum
from functools import partial
from multiprocessing.pool import ThreadPool
from os.path import dirname, exists


_logger = logging.getLogger('tracker')


class TrackingType(Enum):
    distance = 0
    beam_crossings = 1
    position = 2


class MonitoredArea():
    """
    The arena defines the space where the flies move
    Carries information about the ROI (coordinates defining each vial) and
    the number of flies in each vial

    The class monitor takes care of the camera
    The class arena takes care of the flies
    """

    ROIS_PER_MONITOR = 32

    def __init__(self,
                 track_type=1,
                 sleep_deprivation_flag=0,
                 fps=1,
                 aggregated_frames=1,
                 aggregated_frames_size=60,
                 tracking_data_buffer_size=5,
                 extend=True,
                 acq_time=None,
                 results_suffix=''):
        """
        :param track_type: 
        :param sleep_deprivation_flag:
        :param fps: this values is the video acquisition rate and typically comes from the image source
        :param aggregated_frames: specify the aggregation interval in frames
        :param aggregated_frames_size: if the aggregation interval is very large then the
                                       this value specifies the number of frame buffers. Once the buffer
                                       is full it aggregates the current buffered data without reseting
                                       the frame index; frame index is reset only when aggregated_frames is reached
        :param tracking_data_buffer_size: specifies how many output lines to buffer in memory before writing the
                                          data to disk
        :param acq_time: 
        """
        self._track_type = track_type
        self._sleep_deprivation_flag = sleep_deprivation_flag
        self.ROIS = []  # regions of interest
        self.rois_background = []
        self._beams = []  # beams: absolute coordinates
        self._points_to_track = []
        self._tracking_data_buffer_size = tracking_data_buffer_size if tracking_data_buffer_size > 0 else 1
        self._tracking_data_buffer = []
        self._tracking_data_buffer_index = 0
        self._fps = fps
        self._aggregated_frames = aggregated_frames if aggregated_frames > 0 else 1
        self._acq_time = datetime.now() if acq_time is None else acq_time
        self._roi_filter = None
        self._extend = extend
        self._result_suffix = results_suffix

        # shape ( rois, (x, y) ) - contains the coordinates of the current frame per ROI
        self._current_frame_fly_coord = np.zeros((1, 2), dtype=np.uint32)
        # shape ( rois, self._aggregated_frames+1, (x, y) ) - contains the coordinates of the frames that
        # need to be aggregated.
        self._aggregated_frames_size = aggregated_frames_size + 1 if aggregated_frames_size > 0 else 2
        self._aggregated_frames_fly_coord = np.zeros((1, self._aggregated_frames_size, 2), dtype=np.uint32)
        # the relative frame index from the last aggregation
        self._aggregated_frame_index = 0
        # index to the aggregated frames buffer - the reason for this is that if the number of aggregated frames is
        # too large these will drift apart
        self._aggregated_frames_buffer_index = 0
        self._first_position = (0, 0)

    def get_results_suffix(self):
        return self._result_suffix

    def set_roi_filter(self, trackable_rois):
        """
        This is a testing method that allows to only track the specified rois
        :param trackable_rois: rois to track
        :return:
        """
        self._roi_filter = trackable_rois

    def is_roi_trackable(self, roi):
        return self._roi_filter is None or self._roi_filter == [] or roi in self._roi_filter

    def set_output(self, filename):
        self._lineno = 0
        self.output_filename = filename

    def add_fly_coords(self, roi_index, coords):
        """
        Add the provided coordinates to the existing list
        fly_index   int     the fly index number in the arena
        coords      (x,y)    the coordinates to add
        Called for every fly moving in every frame
        """
        previous_position = tuple(self._current_frame_fly_coord[roi_index])
        is_first_movement = (previous_position == self._first_position)
        # coords is None if no blob was detected
        fly_coords = previous_position if coords is None else coords

        distance = self._distance(previous_position, fly_coords)
        if distance == 0:
            # leave the position unchanged if the distance from the previous position is either too small or too big
            fly_coords = previous_position

        # Does a running average for the coordinates of the fly at each frame to _fly_coord_buffer
        # This way the shape of _fly_coord_buffer is always (n, (x,y)) and once a second we just have to add the (x,y)
        # values to _fly_period_end_coords, whose shape is (n, 60, (x,y))
        self._current_frame_fly_coord[roi_index] = fly_coords
        return self._current_frame_fly_coord[roi_index], distance

    def _distance(self, p1, p2):
        """
        Calculate the distance between two cartesian points
        """
        ((x1, y1), (x2, y2)) = (p1, p2)
        return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def get_n_monitors(self):
        n_rois = len(self.ROIS)
        if n_rois % MonitoredArea.ROIS_PER_MONITOR > 0:
            return int(n_rois / MonitoredArea.ROIS_PER_MONITOR + 1)
        else:
            return int(n_rois / MonitoredArea.ROIS_PER_MONITOR)

    def add_roi(self, roi, n_flies=1):
        self.ROIS.append(roi)
        self._points_to_track.append(n_flies)
        self._beams.append(self.get_midline(roi))

    def roi_to_rect(self, roi, scale=(1, 1)):
        """
        Converts a ROI (a tuple of four points coordinates) into
        a Rect (a tuple of two points coordinates)
        """
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = roi
        lx = min([x1, x2, x3, x4])
        rx = max([x1, x2, x3, x4])
        uy = min([y1, y2, y3, y4])
        ly = max([y1, y2, y3, y4])
        return (
            (int(lx * scale[0]), int(uy * scale[1])),
            (int(rx * scale[0]), int(ly * scale[1]))
        )

    def roi_to_poly(self, roi, scale=(1, 1)):
        """
        Converts a ROI (a tuple of four points coordinates) into
        a Rect (a tuple of two points coordinates)
        """
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = roi
        lx = min([x1, x2, x3, x4])
        rx = max([x1, x2, x3, x4])
        uy = min([y1, y2, y3, y4])
        ly = max([y1, y2, y3, y4])

        return [
            [int(lx * scale[0]), int(ly * scale[1])],
            [int(lx * scale[0]), int(uy * scale[1])],
            [int(rx * scale[0]), int(uy * scale[1])],
            [int(rx * scale[0]), int(ly * scale[1])]
        ]

    def get_midline(self, roi, scale=(1, 1), conv=None, midline_type=None):
        """
        Return the position of each ROI's midline
        Will automatically determine the orientation of the vial
        """
        (x1, y1), (x2, y2) = self.roi_to_rect(roi)

        if midline_type == CrossingBeamType.horizontal:
            horizontal_beam = True
        elif midline_type == CrossingBeamType.vertical:
            horizontal_beam = False
        else:
            horizontal_beam = abs(y2 - y1) >= abs(x2 - x1)

        if horizontal_beam:
            ym = y1 + (y2 - y1) / 2
            if conv:
                return (conv(x1 * scale[0]), conv(ym * scale[1])), (conv(x2 * scale[0]), conv(ym * scale[1]))
            else:
                return (x1 * scale[0], ym * scale[1]), (x2 * scale[0], ym * scale[1])
        else:
            xm = x1 + (x2 - x1) / 2
            if conv:
                return (conv(xm * scale[0]), conv(y1 * scale[1])),(conv(xm * scale[0]), conv(y2 * scale[1]))
            else:
                return (xm * scale[0], y1 * scale[1]), (xm * scale[0], y2 * scale[1])

    def save_rois(self, filename):
        with open(filename, 'wb') as cf:
            pickle.dump(self.ROIS, cf)
            pickle.dump(self._points_to_track, cf)

    def load_rois(self, filename):
        """
        Load the crop data from the specified filename
        :param filename: name of the file to load the cropped region from
        :return:
        """
        self._mask_file = filename
        with open(filename, 'rb') as cf:
            self.ROIS = pickle.load(cf)
            self._points_to_track = pickle.load(cf)
        self._reset_data_buffers()
        for roi_index, roi in enumerate(self.ROIS):
            _logger.debug('ROI: %d: %r' % (roi_index + 1, roi))
            self._beams.append(self.get_midline(roi))
            self.rois_background.append(None)

    def _reset_data_buffers(self):
        self._reset_current_frame_buffer()
        self._reset_aggregated_frames_buffers()

    def _reset_aggregated_frames_buffers(self):
        self._aggregated_frames_fly_coord = np.zeros((len(self.ROIS), self._aggregated_frames_size, 2), dtype=np.uint32)

    def _reset_current_frame_buffer(self):
        self._current_frame_fly_coord = np.zeros((len(self.ROIS), 2), dtype=np.uint32)

    def _reset_tracking_data_buffer(self):
        self._tracking_data_buffer = []
        self._tracking_data_buffer_index = 0
        self._aggregated_frame_index = 0

    def _shift_data_window(self, nframes):
        self._aggregated_frames_fly_coord = np.roll(self._aggregated_frames_fly_coord, (-nframes, 0), axis=(1, 0))
        self._aggregated_frames_buffer_index -= nframes

    def update_frame_activity(self, frame_time):
        if self._aggregated_frame_index >= self._aggregated_frames:
            _logger.info('Aggregate data - frame time: %ds' % frame_time)
            # aggregate the current buffers
            self.aggregate_activity(frame_time)
            # then
            if len(self._tracking_data_buffer) < self._tracking_data_buffer_size:
                # buffer the aggregated activity if there's room in the buffers
                self._tracking_data_buffer_index += 1
            else:
                # or dump the current data buffers to disk
                self.write_activity()
            # reset the frame index
            self._aggregated_frame_index = 0
        elif self._aggregated_frames_buffer_index >= self._aggregated_frames_size:
            # the frame buffers reached the limit so aggregate the current buffers
            self.aggregate_activity(frame_time)
        self._aggregated_frames_fly_coord[:, self._aggregated_frames_buffer_index] = self._current_frame_fly_coord
        self._aggregated_frames_buffer_index += 1
        self._aggregated_frame_index += 1

    def get_track_type(self):
        return self._track_type

    def get_track_type_desc(self):
        if self._track_type == TrackingType.distance.value:
            return 'distance'
        elif self._track_type == TrackingType.beam_crossings.value:
            return 'crossings'
        elif self._track_type == TrackingType.position.value:
            return 'position'
        else:
            raise ValueError('Invalid track type option: %d' % self._track_type)

    def aggregate_activity(self, frame_time):
        if self._track_type == TrackingType.distance.value:
            values, _ = self._calculate_distances()
            activity = DistanceSum(frame_time, values)
        elif self._track_type == TrackingType.beam_crossings.value:
            values, _ = self._calculate_vbm()
            activity = VirtualBeamCrossings(frame_time, values)
        elif self._track_type == TrackingType.position.value:
            values, count = self._calculate_position()
            activity = AveragePosition(frame_time, values, count)
        else:
            raise ValueError('Invalid track type option: %d' % self._track_type)

        if len(self._tracking_data_buffer) <= self._tracking_data_buffer_index:
            self._tracking_data_buffer.append(activity)
        else:
            previous_activity = self._tracking_data_buffer[self._tracking_data_buffer_index]
            # combine previous activity with the current activity
            previous_activity.aggregate_with(activity)

    def write_activity(self):
        if self.output_filename:
            n_monitors = self.get_n_monitors()
            for mi in range(0, n_monitors):
                self._write_activity_per_monitor(
                    mi,
                    self.output_filename.format(mi + 1),
                    self._lineno,
                    mi * MonitoredArea.ROIS_PER_MONITOR, (mi + 1) * MonitoredArea.ROIS_PER_MONITOR
                )
            self._lineno += len(self._tracking_data_buffer)

        self._reset_tracking_data_buffer()

    def _write_activity_per_monitor(self, monitor_index, monitor_output, start_lineno, start_roi_index, end_roi_index):
        """
        Writes activity for the corresponding monitor
        :param monitor_index: monitor index
        :param monitor_output: monitor output file
        :param start_roi_index: start roi index - inclusive
        :param end_roi_index: end roi index - non-inclusive
        :return:
        """
        # monitor is active
        active = '1'
        # frames per seconds (FPS)
        damscan = self._fps
        # monitor with sleep deprivation capabilities?
        sleep_deprivation = self._sleep_deprivation_flag * 1
        # monitor number
        monitor = '{}'.format(monitor_index)
        # unused
        unused = 0
        # is light on or off?
        light = '0'  # changed to 0 from ? for compatability with SCAMP
        # Expand the readings to up to the number of ROIs per monitor for compatibility reasons with trikinetics
        n_monitor_rois = len(self.ROIS[start_roi_index:end_roi_index])
        if self._extend and n_monitor_rois < MonitoredArea.ROIS_PER_MONITOR:
            extension = MonitoredArea.ROIS_PER_MONITOR - n_monitor_rois
        else:
            extension = 0

        current_lineno = start_lineno
        with open(monitor_output, 'a') as ofh:
            for activity in self._tracking_data_buffer:
                current_lineno += 1
                # frame timestamp
                frame_dt = self._acq_time + timedelta(seconds=activity.frame_time)

                if int(activity.frame_time) == activity.frame_time:
                    time_fmt = '%d %b %y\t%H:%M:%S'
                else:
                    time_fmt = '%d %b %y\t%H:%M:%S.%f'
                frame_dt_str = frame_dt.strftime(time_fmt)
                row_prefix = '%s\t' * 9 % (current_lineno, frame_dt_str,
                                           active, damscan, self._track_type,
                                           sleep_deprivation,
                                           monitor, unused, light)
                ofh.write(row_prefix)
                ofh.write(activity.format_values(start_roi_index, end_roi_index, extension))
                ofh.write('\n')

    def _calculate_distances(self):
        """
        Motion is calculated as distance in px per minutes
        """
        # shift by one second left flies, seconds, (x,y)
        fs = np.roll(self._aggregated_frames_fly_coord, -1, axis=1)

        x = self._aggregated_frames_fly_coord[:, :self._aggregated_frames_buffer_index, 0]
        y = self._aggregated_frames_fly_coord[:, :self._aggregated_frames_buffer_index, 1]

        x1 = fs[:, :self._aggregated_frames_buffer_index, 0]
        y1 = fs[:, :self._aggregated_frames_buffer_index, 1]

        d = self._distance((x, y), (x1, y1))

        nframes = self._aggregated_frames_buffer_index - 1
        if nframes > 0:
            # we sum nframes only so that we don't have duplication
            values = d[:, :nframes].sum(axis=1)
            self._shift_data_window(nframes)
        else:
            values = np.zeros((len(self.ROIS)), dtype=np.uint32)

        return values, nframes

    def _calculate_vbm(self):
        """
        Motion is calculated as virtual beam crossing
        Detects automatically beam orientation (vertical vs horizontal)
        """
        nframes = self._aggregated_frames_buffer_index - 1
        # the values.shape is (nframes, nrois)),
        values = np.zeros((len(self.ROIS)), dtype=np.uint32)
        if nframes > 0:
            roi_index = 0
            for fd, md in zip(self._aggregated_frames_fly_coord, self._relative_beams()):
                if self.is_roi_trackable(roi_index):
                    (mx1, my1), (mx2, my2) = md
                    horizontal_beam = (my1 == my2)

                    fs = np.roll(fd, -1, 0)  # coordinates shifted to the following frame

                    x = fd[:self._aggregated_frames_buffer_index, 0]
                    y = fd[:self._aggregated_frames_buffer_index, 1]
                    x1 = fs[:self._aggregated_frames_buffer_index, 0]
                    y1 = fs[:self._aggregated_frames_buffer_index, 1]

                    if horizontal_beam:
                        crosses = (y < my1) * (y1 >= my1) + (y > my1) * (y1 <= my1)
                    else:
                        crosses = (x < mx1) * (x1 >= mx1) + (x > mx1) * (x1 <= mx1)
                    # we sum nframes to eliminate duplication
                    values[roi_index] = crosses[:nframes].sum()
                else:
                    # the region is not tracked
                    values[roi_index] = 0

                roi_index += 1

            self._shift_data_window(nframes)

        return values, nframes

    def _relative_beams(self, scale=None):
        """
        Return the coordinates of the beam
        relative to the ROI to which they belong
        """
        scalef = (1, 1) if scale is None else scale
        beams = []
        for roi, beam in zip(self.ROIS, self._beams):
            rx, ry = self.roi_to_rect(roi)[0]
            (bx0, by0), (bx1, by1) = beam
            beams.append(
                (
                    ((bx0 - rx) * scalef[0], (by0 - ry) * scalef[1]),
                    ((bx1 - rx) * scalef[0], (by1 - ry) * scalef[1])
                )
            )
        return beams

    def _calculate_position(self, resolution=1):
        """
        Simply write out position of the fly at every time interval, as
        decided by "resolution" (seconds)
        """
        nframes = self._aggregated_frames_buffer_index - 1
        fs = np.roll(self._aggregated_frames_fly_coord, -1, axis=1)
        x = fs[:, :self._aggregated_frames_buffer_index, 0]
        y = fs[:, :self._aggregated_frames_buffer_index, 1]

        values = np.zeros((len(self.ROIS), 2), dtype=np.uint32)
        # we average nframes, which is 1 less the the buffer's end so that we don't have duplication
        if nframes > 0:
            values[:, 0] = x[:, :nframes].mean(axis=1)
            values[:, 1] = y[:, :nframes].mean(axis=1)
            self._shift_data_window(nframes)

        return values, nframes


class CrossingBeamType(Enum):
    no_crossing_beam = 0
    horizontal = 1
    vertical = 2
    based_on_roi_coord = 3

    @classmethod
    def is_crossing_beam_needed(cls, track_type, beam_type):
        return ((track_type == TrackingType.beam_crossings or track_type == TrackingType.beam_crossings.value) and
                beam_type != cls.no_crossing_beam)


class TrackingData():

    def __init__(self, frame_time, values):
        self.frame_time = frame_time
        self.values = values

    def aggregate_with(self, tracking_data):
        self.frame_time = tracking_data.frame_time
        self.values = self.combine_values(self.values, tracking_data.values)

    def combine_values(self, v1, v2):
        pass

    def format_values(self, start, end, extended_regions):
        if extended_regions > 0:
            return '\t'.join([str(v) for v in self.values[start:end]] + ['0', ] * extended_regions)
        else:
            return '\t'.join([str(v) for v in self.values[start:end]])


class VirtualBeamCrossings(TrackingData):

    def combine_values(self, v1, v2):
        return v1 + v2


class DistanceSum(TrackingData):

    def combine_values(self, v1, v2):
        return v1 + v2


class AveragePosition(TrackingData):

    def __init__(self, frame_time, values, n_values):
        super(AveragePosition, self).__init__(frame_time, values)
        self._n_values = n_values

    def aggregate_with(self, tracking_data):
        self.frame_time = tracking_data.frame_time
        new_values = (self.values * self._n_values + tracking_data.values * tracking_data._n_values) / (
                    self._n_values + tracking_data._n_values)
        self.values = new_values

    def format_values(self, start, end, extended_regions):
        if extended_regions > 0:
            return '\t'.join(['{},{}'.format(v[0], v[1])
                              for v in self.values[start:end]] + ['0.0,0.0', ] * extended_regions)
        else:
            return '\t'.join(['{},{}'.format(v[0], v[1])
                              for v in self.values[start:end]])


class ImageSource():

    def __init__(self, resolution=None, size=None):
        self._resolution = resolution
        self._size = size

    def get_scale(self):
        if self._size is not None and self._resolution and self._resolution[0] and self._resolution[1]:
            return (self._size[0] / self._resolution[0], self._size[1] / self._resolution[1])
        else:
            return None

    def get_size(self):
        return self._size

    def set_size(self, size):
        self._size = size

    def set_resolution(self, width, height):
        self._resolution = (width, height)

    def is_opened(self):
        return False

    def get_image(self):
        pass

    def get_frame_time(self, frame_index):
        pass

    def get_start_time_in_seconds(self):
        pass

    def set_start_time_in_seconds(self, start_time):
        pass

    def get_end_time_in_seconds(self):
        pass

    def set_end_time_in_seconds(self, end_time):
        pass

    def get_current_frame_time_in_seconds(self):
        pass

    def open(self):
        pass

    def close(self):
        pass


class MovieFile(ImageSource):

    def __init__(self, movie_file_path, open_source=True, start_msecs=None, end_msecs=None, resolution=None):
        """
        :param movie_file_path: path to the movie file
        :param open_source: flag that tells it whether to open the image source or not
        :param start_msecs: start frame time in milliseconds. If None starts at first
        :param end_msecs: last frame time in milliseconds. If None ends at last
        :param resolution: video resolution
        """

        super(MovieFile, self).__init__(resolution=resolution)

        self._movie_file_path = movie_file_path
        self._fps = None
        self._start_msecs = start_msecs
        self._end_msecs = end_msecs
        self._start = None
        self._end = None
        self._step = 1
        self._total_frames = None
        self._current_frame = None

        # open the movie file
        if open_source:
            self.open()

    def is_opened(self):
        return self._capture is not None and self._capture.isOpened()

    def get_fps(self):
        return self._fps

    def get_start(self):
        return self._start

    def get_end(self):
        return self._end

    def get_image(self):
        if not self.is_opened() or self._current_frame < 0 or self._current_frame >= self._end:
            return False, -1, None
        else:
            current_frame = self._current_frame
            res = self._capture.read()
            if self._inc_current_frame() and self._step != 1:
                self._capture.set(cv2.CAP_PROP_POS_FRAMES, self._current_frame)
            return res[0], current_frame, res[1]

    def _inc_current_frame(self):
        self._current_frame += self._step
        if self._current_frame < self._end:
            return True
        else:
            return False

    def update_frame_index(self, frame_index):
        if frame_index >= self._start and frame_index < self._end:
            self._current_frame = frame_index
        elif frame_index < self._start:
            self._current_frame = self._start
        else:
            self._current_frame = self._end
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, self._current_frame)
        res = self._capture.read()
        return res[0], frame_index, res[1]

    def get_frame_time(self, frame_index):
        fps = self.get_fps()
        if fps:
            return frame_index / fps
        else:
            return frame_index

    def get_start_time_in_seconds(self):
        if self.is_opened():
            return self._start / self.get_fps()
        else:
            return None

    def set_start_time_in_seconds(self, start_time):
        self._start_msecs = start_time * 1000
        if self.is_opened():
            start_frame = start_time * self.get_fps()
            if start_frame < 0:
                self._start = 0
            elif start_frame > self._total_frames:
                self._start = self._total_frames
            else:
                self._start = start_frame

    def get_end_time_in_seconds(self):
        fps = self.get_fps()
        if fps:
            return self._end / self.get_fps()
        else:
            return 0

    def set_end_time_in_seconds(self, end_time):
        self._end_msecs = end_time * 1000
        if self.is_opened():
            end_frame = end_time * self.get_fps()
            if end_frame < 0:
                self._end = self._total_frames
            elif end_frame > self._total_frames:
                self._end = self._total_frames
            else:
                self._end = end_frame

    def get_current_frame_time_in_seconds(self):
        if self.is_opened():
            frame_time_in_millis = self._capture.get(cv2.CAP_PROP_POS_MSEC)
            return frame_time_in_millis / 1000  # return the time in seconds
        else:
            return None

    def open(self):
        self._capture = cv2.VideoCapture(self._movie_file_path)
        height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))

        self.set_size((width, height))

        nframes = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self._fps = int(self._capture.get(cv2.CAP_PROP_FPS))

        # set the start frame
        if self._start_msecs is None or self._start_msecs < 0:
            self._start = 0
        else:
            start_frame = int(self._start_msecs * self._fps / 1000)
            if start_frame < nframes:
                self._start = start_frame
            else:
                self._start = nframes
        # set the end frame
        if self._end_msecs is None or self._end_msecs < 0:
            self._end = nframes
        else:
            end_frame = int(self._end_msecs * self._fps / 1000)
            if end_frame < nframes:
                self._end = end_frame
            else:
                self._end = nframes
        # set the frame increment
        self._total_frames = nframes
        self._current_frame = self._start
        if self._current_frame != 0:
            self._capture.set(cv2.CAP_PROP_POS_FRAMES, self._current_frame)

    def close(self):
        if self._capture is not None:
            self._capture.release()
            self._capture = None


def estimate_background(image_source,
                        gaussian_filter_size=(3, 3),
                        gaussian_sigma=0,
                        cancel_callback=None):
    background = None
    average = None
    nframes = 0
    for frame_image, frame_index, frame_time_pos in _next_image_frame(image_source, cancel_callback=cancel_callback):
        nframes += 1
        # smooth the image to get rid of false positives
        filtered_image = cv2.GaussianBlur(frame_image, gaussian_filter_size, gaussian_sigma)

        if average is None:
            average = np.float32(filtered_image)
        else:
            average = average + (filtered_image - average) / nframes
        background = cv2.convertScaleAbs(average)

    return background


def prepare_monitored_areas(config, fps=1, results_suffix=''):

    def create_monitored_area(configured_area_index, configured_area):
        aggregated_frames = configured_area.get_aggregation_interval_in_frames(fps)
        aggregated_frames_size = aggregated_frames if aggregated_frames <= 600 else 600
        ma = MonitoredArea(track_type=configured_area.get_track_type(),
                           sleep_deprivation_flag=1 if configured_area.get_sleep_deprived_flag() else 0,
                           fps=fps,
                           aggregated_frames=aggregated_frames,
                           aggregated_frames_size=aggregated_frames_size,
                           acq_time=config.get_acq_time(),
                           extend=configured_area.get_extend_flag(),
                           results_suffix=results_suffix)
        ma.set_roi_filter(configured_area.get_tracked_rois_filter())
        ma.load_rois(configured_area.get_maskfile())
        ma_results_suffix = ma.get_results_suffix()
        if ma_results_suffix:
            ma_results_suffix = '-' + ma_results_suffix

        n_monitors = ma.get_n_monitors()

        if n_monitors > 1:
            monitor_index_holder = '_{:02}'
        else:
            monitor_index_holder = ''
        # the format is Monitor-<area>[_monitor]-<tracking type>[-<start-frame>-<end-frame>].txt
        output_pattern = 'Monitor-{:02}{}-{}{}.txt'.format(
            configured_area_index + 1,
            monitor_index_holder,
            ma.get_track_type_desc(),
            ma_results_suffix
        )
        output_dirname = config.get_data_folder()
        fulloutput_pattern = os.path.join(output_dirname, output_pattern)

        for monitor_index in range(0, n_monitors):
            monitor_output_filename = fulloutput_pattern.format(monitor_index + 1)
            if exists(monitor_output_filename):
                os.remove(monitor_output_filename)

        os.makedirs(output_dirname, exist_ok=True)

        ma.set_output(fulloutput_pattern)
        return ma

    return [create_monitored_area(area_index, configured_area)
            for area_index, configured_area in enumerate(config.get_monitored_areas())
            if configured_area.get_track_flag()]


def process_image_frames(image_source, monitored_areas,
                         gaussian_filter_size=(3, 3),
                         gaussian_sigma=0,
                         moving_alpha=0.1,
                         cancel_callback=None,
                         frame_callback=None,
                         mp_pool_size=1):
    image_scalef = image_source.get_scale()
    pool = ThreadPool(mp_pool_size)

    results = None
    for frame_image, frame_index, frame_time_pos in _next_image_frame(image_source, cancel_callback=cancel_callback):
        _logger.debug('Process frame %d(frame time: %rs)' % (frame_index, frame_time_pos))

        # there is an option to use the thread pool but it appears that it really doesn't help much
        # on the contrary - using the thread pool makes the processing slower.
        if mp_pool_size <= 1:
            results = list(itertools.starmap(partial(_process_roi,
                                                     frame_image,
                                                     gaussian_filter_size=gaussian_filter_size,
                                                     gaussian_sigma=gaussian_sigma,
                                                     moving_alpha=moving_alpha,
                                                     scalef=image_scalef),
                                             _next_monitored_area_roi(monitored_areas)))
        else:
            results = pool.starmap(partial(_process_roi,
                                           frame_image,
                                           gaussian_filter_size=gaussian_filter_size,
                                           gaussian_sigma=gaussian_sigma,
                                           moving_alpha=moving_alpha,
                                           scalef=image_scalef),
                                   _next_monitored_area_roi(monitored_areas))

        if frame_callback:
            frame_callback(frame_index, frame_time_pos, frame_image, [(r[0][0] * image_scalef[0], r[0][1] * image_scalef[1]) for r in results if r])

        def update_monitored_area_activity(monitored_area):
            monitored_area.update_frame_activity(frame_time_pos)

        list(map(update_monitored_area_activity, monitored_areas))

    if results is not None and frame_callback:
        frame_callback(frame_index,
                       frame_time_pos,
                       frame_image,
                       [(r[0][0] * image_scalef[0], r[0][1] * image_scalef[1]) for r in results])

    frame_time_pos = image_source.get_current_frame_time_in_seconds()
    _logger.info('Aggregate the remaining frames - frame time: %ds' % frame_time_pos)
    # write the remaining activity that is still in memory
    for monitored_area in monitored_areas:
        # aggregate whatever is left in the buffers
        monitored_area.aggregate_activity(frame_time_pos)
        # then write them out to disk
        monitored_area.write_activity()

    return True


def _next_image_frame(image_source, cancel_callback=None):
    not_cancelled = cancel_callback or _always_true
    while not_cancelled():
        frame_time_pos = image_source.get_current_frame_time_in_seconds()
        has_more_frames, frame_index, frame_image = image_source.get_image()
        if not has_more_frames:
            break
        yield (frame_image, frame_index, frame_time_pos)


def _always_true():
    return True


def _next_monitored_area_roi(monitored_areas):
    for monitored_area in monitored_areas:
        for roi_index, roi in enumerate(monitored_area.ROIS):
            if monitored_area.is_roi_trackable(roi_index):
                yield (monitored_area, roi, roi_index)


def _process_roi(image, monitored_area, roi, roi_index,
                 gaussian_filter_size=(3, 3),
                 gaussian_sigma=0,
                 moving_alpha=0.1,
                 scalef=(1, 1)):
    (roi_min_x, roi_min_y), (roi_max_x, roi_max_y) = monitored_area.roi_to_rect(roi, scalef)

    image_roi = image[roi_min_y:roi_max_y, roi_min_x:roi_max_x]

    if gaussian_filter_size[0] == 0:
        filtered_roi =  image_roi
    else:
        filtered_roi =  cv2.GaussianBlur(image_roi, gaussian_filter_size, gaussian_sigma)

    roi_average = monitored_area.rois_background[roi_index]
    if roi_average is None:
        roi_average = np.float32(filtered_roi)
    else:
        roi_average = cv2.accumulateWeighted(filtered_roi, roi_average, alpha=moving_alpha)

    monitored_area.rois_background[roi_index] = roi_average
    roi_background = cv2.convertScaleAbs(roi_average)

    # subtract the background - but instead of subtracting the background from the image
    # we subtract the image from the background because the background has a higher intensity than the fly
    roi_background_diff = cv2.subtract(roi_background, filtered_roi)
    roi_gray_diff = cv2.cvtColor(roi_background_diff, cv2.COLOR_BGR2GRAY)
    _, roi_binary = cv2.threshold(roi_gray_diff, 40, 255, cv2.THRESH_BINARY)
    roi_binary = cv2.dilate(roi_binary, None, iterations=2)
    roi_binary = cv2.erode(roi_binary, None, iterations=2)

    fly_cnts, _ = cv2.findContours(roi_binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

    fly_area = None
    fly_coords = None
    for fly_contour in fly_cnts:
        fly_contour_moments = cv2.moments(fly_contour)
        area = fly_contour_moments['m00']
        if area > 0:
            coords = (fly_contour_moments['m10'] / fly_contour_moments['m00'],
                          fly_contour_moments['m01'] / fly_contour_moments['m00'])
        else:
            bound_rect = cv2.boundingRect(fly_contour)
            pt1 = (bound_rect[0], bound_rect[1])
            pt2 = (bound_rect[0] + bound_rect[2], bound_rect[1] + bound_rect[3])
            area = (pt2[0] - pt1[0]) * (pt2[1] - pt1[1])
            coords = (pt1[0] + (pt2[0] - pt1[0]) / 2, pt1[1] + (pt2[1] - pt1[1]) / 2)

        if area < 400:
            if fly_coords is None:
                fly_coords = coords
                fly_area = area
            elif area > fly_area:
                fly_coords = coords
                fly_area = area

    rel_fly_coord, distance = monitored_area.add_fly_coords(roi_index,
                                                            (fly_coords[0] / scalef[0],
                                                             fly_coords[1] / scalef[1]) if fly_coords is not None
                                                            else None)
    return (rel_fly_coord[0] + roi_min_x / scalef[0],
            rel_fly_coord[1] + roi_min_y / scalef[1]), rel_fly_coord, distance
