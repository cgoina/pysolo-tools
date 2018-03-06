import cv2
import logging
import numpy as np
import os
import _pickle as cPickle

from datetime import datetime, timedelta
from os.path import dirname, exists


_logger = logging.getLogger('tracker')


class MonitorArea():
    """
    The arena defines the space where the flies move
    Carries information about the ROI (coordinates defining each vial) and
    the number of flies in each vial

    The class monitor takes care of the camera
    The class arena takes care of the flies
    """
    def __init__(self, track_type, sleep_deprivation_flag, datawindow_size=10, fps=1, acq_time=None):
        """
        :param track_type: track type
        :param sleep_deprivation_flag: sleep deprivation flag
        :param datawindow_size: data window size
        """
        self._track_type = track_type
        self._sleep_deprivation_flag = sleep_deprivation_flag
        self.ROIS = [] # regions of interest
        self._beams = [] # beams: absolute coordinates
        self._points_to_track = []
        self._datawindow_size = datawindow_size
        self._fps = fps
        self._acq_time = datetime.now() if acq_time is None else acq_time
        self._roi_filter = None

        # shape ( rois, (time, x, y) ) Contains the coordinates of the current frame per ROI
        self._fly_coord_by_roi = np.zeros((1, 2), dtype=np.int)
        # shape ( flies, self._frames_per_dataspan, (time, x, y) )
        # Contains the frame time and the coordinates from all frames from the current period
        self._datawindow_fly_coord_by_roi = np.zeros((1, self._datawindow_size, 2), dtype=np.int)
        self._datawindow_frame_time_pos = np.zeros(self._datawindow_size, dtype=np.int)
        self._datawindow_current_index = 0
        self._first_position = (0, 0)

    def set_roi_filter(self, trackable_rois):
        """
        This is a testing method that allows to only track the specified rois
        :param trackable_rois: rois to track
        :return:
        """
        self._roi_filter = trackable_rois

    def is_roi_trackable(self, roi):
        return self._roi_filter is None or roi in self._roi_filter

    def set_output(self, filename, clear_if_exists=True):
        self._lineno = 0;
        self.output_filename = filename
        if self.output_filename:
            os.makedirs(dirname(self.output_filename), exist_ok=True)
        if exists(self.output_filename) and clear_if_exists:
            os.remove(self.output_filename)

    def add_fly_coords(self, roi_index, coords):
        """
        Add the provided coordinates to the existing list
        fly_index   int     the fly index number in the arena
        coords      (x,y)    the coordinates to add
        Called for every fly moving in every frame
        """
        fly_size = 15  # About 15 pixels at 640x480
        max_movement = fly_size * 100
        min_movement = fly_size / 3

        previous_position = tuple(self._fly_coord_by_roi[roi_index])
        is_first_movement = (previous_position == self._first_position)
        # coords is None if no blob was detected
        fly_coords = previous_position if coords is None else coords

        distance = self._distance(previous_position, fly_coords)
        if (distance > max_movement and not is_first_movement) or (distance < min_movement):
            # leave the position unchanged if the distance from the previous position is either too small or too big
            fly_coords = previous_position

        # Does a running average for the coordinates of the fly at each frame to _fly_coord_buffer
        # This way the shape of _fly_coord_buffer is always (n, (x,y)) and once a second we just have to add the (x,y)
        # values to _fly_period_end_coords, whose shape is (n, 60, (x,y))
        self._fly_coord_by_roi[roi_index] = fly_coords
        return fly_coords, distance

    def _distance(self, p1, p2):
        """
        Calculate the distance between two cartesian points
        """
        ((x1, y1), (x2, y2)) = (p1, p2)
        return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def add_roi(self, roi, n_flies=1):
        self.ROIS.append(roi)
        self._points_to_track.append(n_flies)
        self._beams.append(self._get_midline(roi))

    def roi_to_rect(self, roi, scale=None):
        """
        Converts a ROI (a tuple of four points coordinates) into
        a Rect (a tuple of two points coordinates)
        """
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = roi
        lx = min([x1, x2, x3, x4])
        rx = max([x1, x2, x3, x4])
        uy = min([y1, y2, y3, y4])
        ly = max([y1, y2, y3, y4])
        scalef = (1, 1) if scale is None else scale
        return (
            (int(lx * scalef[0]), int(uy * scalef[1])),
            (int(rx * scalef[0]), int(ly * scalef[1]))
        )

    def roi_to_poly(self, roi, scale=None):
        """
        Converts a ROI (a tuple of four points coordinates) into
        a Rect (a tuple of two points coordinates)
        """
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = roi
        lx = min([x1, x2, x3, x4])
        rx = max([x1, x2, x3, x4])
        uy = min([y1, y2, y3, y4])
        ly = max([y1, y2, y3, y4])
        scalef = (1, 1) if scale is None else scale

        return [
            [int(lx * scalef[0]), int(ly * scalef[1])],
            [int(lx * scalef[0]), int(uy * scalef[1])],
            [int(rx * scalef[0]), int(uy * scalef[1])],
            [int(rx * scalef[0]), int(ly * scalef[1])]
        ]

    def _get_midline(self, roi):
        """
        Return the position of each ROI's midline
        Will automatically determine the orientation of the vial
        """
        (x1, y1), (x2, y2) = self.roi_to_rect(roi)
        horizontal = abs(x2 - x1) > abs(y2 - y1)
        if horizontal:
            xm = x1 + (x2 - x1) / 2
            return (xm, y1), (xm, y2)
        else:
            ym = y1 + (y2 - y1) / 2
            return (x1, ym), (x2, ym)

    def save_rois(self, filename):
        with open(filename, 'wb') as cf:
            cPickle.dump(self.ROIS, cf)
            cPickle.dump(self._points_to_track, cf)

    def load_rois(self, filename):
        """
        Load the crop data from the specified filename
        :param filename: name of the file to load the cropped region from
        :return:
        """
        self._mask_file = filename
        with open(filename, 'rb') as cf:
            self.ROIS = cPickle.load(cf)
            self._points_to_track = cPickle.load(cf)
        self._reset_data_buffers()
        for roi in self.ROIS:
            self._beams.append(self._get_midline(roi))

    def _reset_data_buffers(self):
        self._reset_fly_coord_buffer()
        self._reset_datawindow_buffers()

    def _reset_datawindow_buffers(self):
        self._datawindow_fly_coord_by_roi = np.zeros((len(self.ROIS), self._datawindow_size, 2), dtype=np.int)

    def _reset_fly_coord_buffer(self):
        self._fly_coord_by_roi = np.zeros((len(self.ROIS), 2), dtype=np.int)

    def _shift_data_window(self, nframes):
        self._datawindow_fly_coord_by_roi = np.roll(self._datawindow_fly_coord_by_roi, (-nframes, 0), axis=(1, 0))
        self._datawindow_frame_time_pos = np.roll(self._datawindow_frame_time_pos, -nframes)
        self._datawindow_current_index -= nframes

    def update_frame_activity(self, frame_time):
        self._datawindow_fly_coord_by_roi[:, self._datawindow_current_index] = self._fly_coord_by_roi
        self._datawindow_frame_time_pos[self._datawindow_current_index] = frame_time
        # # prepare the frame coordinate buffer for the next frame
        self._reset_fly_coord_buffer()
        self._datawindow_current_index += 1
        if self._datawindow_current_index >= self._datawindow_size:
            return True
        else:
            return False

    def write_activity(self, frame_time, extend=True, scale=None):
        if self.output_filename:
            # monitor is active
            active = '1'
            # frames per seconds (FPS)
            damscan = self._fps
            # monitor with sleep deprivation capabilities?
            sleep_deprivation = self._sleep_deprivation_flag * 1
            # monitor number, not yet implemented
            monitor = '0'
            # unused
            unused = 0
            # is light on or off?
            light = '0'  # changed to 0 from ? for compatability with SCAMP
            # get fly activity
            activity = []
            if self._track_type == 0:
                activity = self._calculate_distances()
            elif self._track_type == 1:
                activity = self._calculate_vbm(scale=scale)
            elif self._track_type == 2:
                activity = self._calculate_position()

            # Expand the readings to 32 flies for compatibility reasons with trikinetics  - in our case 32 ROIs
            # since there's one fly / ROI
            n_rois = len(self.ROIS)
            if extend and n_rois < 32:
                extension = '\t' + '\t'.join(['0', ] * (32 - n_rois))
            else:
                extension = ''

            with open(self.output_filename, 'a') as ofh:
                for a in activity:
                    self._lineno += 1
                    # frame timestamp
                    frame_dt = self._acq_time + timedelta(seconds=int(a[0]))
                    frame_dt_str = frame_dt.strftime('%d %b %y\t%H:%M:%S')

                    row_prefix = '%s\t' * 9 % (self._lineno, frame_dt_str,
                                               active, damscan, self._track_type,
                                               sleep_deprivation,
                                               monitor, unused, light)
                    ofh.write(row_prefix)
                    ofh.write('\t'.join([str(v) for v in a[1:]]))
                    ofh.write(extension)
                    ofh.write('\n')

    def _calculate_distances(self):
        """
        Motion is calculated as distance in px per minutes
        """
        # shift by one second left flies, seconds, (x,y)
        fs = np.roll(self._datawindow_fly_coord_by_roi, -1, axis=1)

        x = self._datawindow_fly_coord_by_roi[:, :self._datawindow_current_index, 0]
        y = self._datawindow_fly_coord_by_roi[:, :self._datawindow_current_index, 1]

        x1 = fs[:, :self._datawindow_current_index, 0]
        y1 = fs[:, :self._datawindow_current_index, 1]

        d = self._distance((x, y), (x1, y1))

        nframes = self._datawindow_current_index - 1
        values = np.zeros((nframes, 1 + len(self.ROIS)), dtype=np.int)
        values[:, 0] = self._datawindow_frame_time_pos[1:self._datawindow_current_index]

        # we sum everything BUT the last bit of information otherwise we have data duplication
        values[:,1:] = d.transpose()[:nframes,:]

        self._shift_data_window(nframes)

        return values

    def _calculate_vbm(self, scale=None):
        """
        Motion is calculated as virtual beam crossing
        Detects automatically beam orientation (vertical vs horizontal)
        """
        nframes = self._datawindow_current_index - 1
        # the values.shape is (nframes, nrois + 1)),
        #  where the value[:, 0] is the frame time position
        values = np.zeros((nframes, 1 + len(self.ROIS)), dtype=np.int)
        values[:, 0] = self._datawindow_frame_time_pos[1:self._datawindow_current_index]
        roi_index = 0
        for fd, md in zip(self._datawindow_fly_coord_by_roi, self._relative_beams(scale=scale)):
            if self.is_roi_trackable(roi_index):
                (mx1, my1), (mx2, my2) = md
                horizontal = (mx1 == mx2)

                fs = np.roll(fd, -1, 0) # coordinates shifted to the following frame

                x = fd[:self._datawindow_current_index, 0]
                y = fd[:self._datawindow_current_index, 1]
                x1 = fs[:self._datawindow_current_index, 0]
                y1 = fs[:self._datawindow_current_index, 1]

                if horizontal:
                    crosses = (x < mx1) * (x1 > mx1) + (x > mx1) * (x1 < mx1)
                else:
                    crosses = (y < my1) * (y1 > my1) + (y > my1) * (y1 < my1)
                values[:, roi_index + 1] = crosses[:nframes]
            else:
                # the region is not tracked
                values[:, roi_index + 1] = 0

            roi_index += 1

        self._shift_data_window(nframes)

        return values

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
        nframes = self._datawindow_current_index - 1
        fs = np.roll(self._datawindow_fly_coord_by_roi, -1, axis=1)
        x = fs[:, :self._datawindow_current_index, 0]
        y = fs[:, :self._datawindow_current_index, 1]

        values = []
        for frame in range(0, nframes):
            values.append((self._datawindow_frame_time_pos[frame + 1],'\t'.join(['%s,%s' % (x, y) for (x, y) in fs[:,frame,:]])))

        self._shift_data_window(nframes)

        return values


class ImageSource():

    def __init__(self, resolution=None, size=None):
        self._resolution = resolution
        self._size = size

    def get_scale(self):
        if self._size is not None and self._resolution is not None:
            return (self._size[0] / self._resolution[0], self._size[1] / self._resolution[1])
        else:
            return None

    def get_size(self):
        return self._size

    def get_image(self):
        pass

    def get_frame_time(self):
        pass

    def close(self):
        pass


class MovieFile(ImageSource):

    def __init__(self, movie_file_path, step=1, start=None, end=None, resolution=None):
        """
        :param movie_file_path: path to the movie file
        :param step: distance between frames
        :param start: start frame. If None starts at first
        :param end: last frame. If None ends at last
        """

        # open the movie file
        self._capture = cv2.VideoCapture(movie_file_path)
        height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))

        super(MovieFile, self).__init__(resolution=resolution, size=(width, height))

        nframes = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT))

        self._movie_file_path = movie_file_path
        self._start = 0 if start is None or start < 0 or start >= nframes else start
        self._end = nframes if end is None or end > nframes or end < 0 else end
        self._step = step or 1
        self._total_frames = nframes
        self._fps = int(self._capture.get(cv2.CAP_PROP_FPS))
        self._current_frame = self._start
        if self._current_frame != 0:
            self._capture.set(cv2.CAP_PROP_POS_FRAMES, self._current_frame)

    def get_fps(self):
        return self._fps

    def get_image(self):
        if self._current_frame < 0 or self._current_frame >= self._end:
            return False, -1, None
        else:
            current_frame = self._current_frame
            res = self._capture.read()
            if self.inc_current_frame() and self._step != 1:
                self._capture.set(cv2.CAP_PROP_POS_FRAMES, self._current_frame)
            return res[0], current_frame, res[1]

    def inc_current_frame(self):
        self._current_frame += self._step
        if self._current_frame < self._end:
            return True
        else:
            return False

    def get_frame_time(self):
        frame_time_in_millis = self._capture.get(cv2.CAP_PROP_POS_MSEC)
        return frame_time_in_millis / 1000 # return the time in seconds

    def get_background(self, moving_alpha=0.2, gaussian_filter_size=(21, 21), gaussian_sigma=0.2):
        """
        The method attempts to get the background image using accumulate weighted method
        :param moving_alpha:
        :param gaussian_filter_size:
        :param gaussian_sigma:
        :return:
        """
        next_frame_res = self.get_image()
        frame_image = next_frame_res[2]
        # smooth the image to get rid of false positives
        frame_image = cv2.GaussianBlur(frame_image, gaussian_filter_size, gaussian_sigma)
        # initialize the moving average
        moving_average = np.float32(frame_image)
        while next_frame_res[0]:
            next_frame_res = self.get_image()
            if not next_frame_res[0]:
                break
            _logger.debug('Update moving average for %d' % next_frame_res[1])
            frame_image = next_frame_res[2]

            # smooth the image to get rid of false positives
            frame_image = cv2.GaussianBlur(frame_image, gaussian_filter_size, gaussian_sigma)
            cv2.accumulateWeighted(frame_image, moving_average, moving_alpha)

        background = cv2.convertScaleAbs(moving_average)
        return background

    def close(self):
        self._capture.release()


def process_image_frames(image_source, monitor_areas, moving_alpha=0.1, gaussian_filter_size=(21, 21), gaussian_sigma=1):
    previous_frame = None
    moving_average = None

    while True:
        frame_time_pos = image_source.get_frame_time()
        next_frame_res = image_source.get_image()
        if not next_frame_res[0]:
            break
        _logger.info('Process frame %d(frame time: %rs)' % (next_frame_res[1], frame_time_pos))
        frame_image = next_frame_res[2]

        # smooth the image to get rid of false positives
        frame_image = cv2.GaussianBlur(frame_image, gaussian_filter_size, gaussian_sigma)
        cv2.imwrite("frame-%d.jpg" % next_frame_res[1], frame_image)

        if moving_average is None:
            moving_average = np.float32(frame_image)
        else:
            moving_average = cv2.accumulateWeighted(frame_image, moving_average, alpha=moving_alpha)

        temp_frame = cv2.convertScaleAbs(moving_average)

        cv2.imwrite("moving-%d.jpg" % next_frame_res[1], temp_frame)

        background_diff = cv2.subtract(temp_frame, frame_image) # subtract the background
        grey_image = cv2.cvtColor(background_diff, cv2.COLOR_BGR2GRAY)

        cv2.imwrite("foreground-%d.jpg" % next_frame_res[1], grey_image)

        binary_image = cv2.threshold(grey_image, 20, 255, cv2.THRESH_BINARY)[1]
        binary_image = cv2.dilate(binary_image, None, iterations=2)
        binary_image = cv2.erode(binary_image, None, iterations=2)

        cv2.imwrite("flyblobs-%d.jpg" % next_frame_res[1], binary_image)

        for area_index, monitor_area in enumerate(monitor_areas):
            for roi_index, roi in enumerate(monitor_area.ROIS):
                if monitor_area.is_roi_trackable(roi_index):
                    process_roi(binary_image, next_frame_res[1], monitor_area, roi, area_index, roi_index, image_source.get_scale())

            # prepare the frame coordinates buffer for the next frame
            if monitor_area.update_frame_activity(frame_time_pos):
                # filled the data buffers
                monitor_area.write_activity(frame_time_pos, scale=image_source.get_scale())

        previous_frame = grey_image

    # write the remaining activity
    for area_index, monitor_area in enumerate(monitor_areas):
        monitor_area.write_activity(frame_time_pos, scale=image_source.get_scale())

    return True


def setRoi(image, roiMsk, roi):
    cv2.fillPoly(roiMsk, [roi], color=[255, 255, 255])


def process_roi(image, image_index, monitor_area, roi, monitor_area_index, roi_index, scalef):
    roiMsk = np.zeros(image.shape, np.uint8)
    (offset_x, offset_y), _ = monitor_area.roi_to_rect(roi, scalef)
    setRoi(image, roiMsk, np.array(monitor_area.roi_to_poly(roi, scalef)))

    image_roi = cv2.bitwise_and(image, image, mask=roiMsk)
    cv2.imwrite("masked-%d-%d-%d.jpg" % (image_index, monitor_area_index, roi_index), image_roi)
    # get the contours relative to the upper left corner of the ROI
    fly_cnts = cv2.findContours(image_roi.copy(), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE, offset=(-offset_x, -offset_y))

    fly_coords = None
    for fly_contour in fly_cnts[1]:
        fly_contour_moments = cv2.moments(fly_contour)
        area = fly_contour_moments['m00']
        if area > 0:
            fly_coords = (fly_contour_moments['m10'] / fly_contour_moments['m00'], fly_contour_moments['m01'] / fly_contour_moments['m00'])
        else:
            bound_rect = cv2.boundingRect(fly_contour)
            pt1 = (bound_rect[0], bound_rect[1])
            pt2 = (bound_rect[0] + bound_rect[2], bound_rect[1] + bound_rect[3])
            fly_coords = (pt1[0] + (pt2[0] - pt1[0]) / 2, pt1[1] + (pt2[1] - pt1[1]) / 2)
            area = (pt2[0] - pt1[0]) * (pt2[1] - pt1[1])

        if area > 400 * scalef[0] * scalef[1]:
            fly_coords = None
    return monitor_area.add_fly_coords(roi_index, fly_coords)
