import cv2
import _pickle as cPickle
import numpy as np

class MonitorArea():
    """
    The arena defines the space where the flies move
    Carries information about the ROI (coordinates defining each vial) and
    the number of flies in each vial

    The class monitor takes care of the camera
    The class arena takes care of the flies
    """
    def __init__(self, frames_per_period=61):
        """
        :param frames_per_period: number of frames per period
        """
        self.ROIS = [] # regions of interest
        self._beams = [] # beams: absolute coordinates
        self._ROAS = [] # regions of actions
        self._points_to_track = []
        self._frames_per_period = frames_per_period

        # shape ( flies, (x,y) ) Contains the coordinates of the last second (if fps > 1, average)
        self._fly_coord_buffer = np.zeros((1, 2), dtype=np.int)
        # shape ( flies, self._frames_per_period, (x,y) ) Contains the coordinates of the last frame
        self._fly_period_end_coords = np.zeros((1, self._frames_per_period, 2), dtype=np.int)
        self._first_position = (0, 0)


    def add_fly_coords(self, fly_index, coords):
        """
        Add the provided coordinates to the existing list
        fly_index   int     the fly index number in the arena
        coords      (x,y)    the coordinates to add
        Called for every fly moving in every frame
        """
        fly_size = 15  # About 15 pixels at 640x480
        max_movement = fly_size * 100
        min_movement = fly_size / 3

        previous_position = tuple(self._fly_coord_buffer[fly_index])
        is_first_movement = (previous_position == self._first_position)
        fly_coords = coords or previous_position  # coords is None if no blob was detected

        distance = self.__distance(previous_position, fly_coords)
        if (distance > max_movement and not is_first_movement) or (distance < min_movement):
            fly_coords = previous_position

        # Does a running average for the coordinates of the fly at each frame to _fly_coord_buffer
        # This way the shape of _fly_coord_buffer is always (n, (x,y)) and once a second we just have to add the (x,y)
        # values to _fly_period_end_coords, whose shape is (n, 60, (x,y))
        self._fly_coord_buffer[fly_index] = np.append(self._fly_coord_buffer[fly_index], fly_coords, axis=0).reshape(-1, 2).mean(axis=0)
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
        n_rois = len(self.ROIS)
        self._fly_coord_buffer = np.zeros((n_rois, 2), dtype=np.int)
        self._fly_period_end_coords = np.zeros((n_rois, self._frames_per_period, 2), dtype=np.int)

        for roi in self.ROIS:
            self._beams.append(self._get_midline(roi))


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
        self._current_frame = self._start
        if self._current_frame != 0:
            self._capture.set(cv2.CAP_PROP_POS_FRAMES, self._current_frame)

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

    def close(self):
        self._capture.release()


def process_image_frames(image_source, monitor_areas, moving_alpha=0.2):
    previous_frame = None
    moving_average = None

    while True:
        next_frame_res = image_source.get_image()
        if not next_frame_res[0]:
            return
        frame_image = next_frame_res[2]

        # smooth the image to get rid of false positives
        frame_image = cv2.GaussianBlur(frame_image, (21, 21), 0)
        cv2.imwrite("frame-%d.jpg" % next_frame_res[1], frame_image)

        if previous_frame is None:
            moving_average = np.float32(frame_image)
        else:
            cv2.accumulateWeighted(frame_image, moving_average, moving_alpha)

        temp_frame = cv2.convertScaleAbs(moving_average)

        cv2.imwrite("moving-%d.jpg" % next_frame_res[1], temp_frame)

        background_diff = cv2.absdiff(frame_image, temp_frame) # subtract the background
        grey_image = cv2.cvtColor(background_diff, cv2.COLOR_BGR2GRAY)

        cv2.imwrite("foreground-%d.jpg" % next_frame_res[1], grey_image)

        binary_image = cv2.threshold(grey_image, 20, 255, cv2.THRESH_BINARY)[1]
        binary_image = cv2.dilate(binary_image, None, iterations=2)
        binary_image = cv2.erode(binary_image, None, iterations=2)

        cv2.imwrite("flyblobs-%d.jpg" % next_frame_res[1], binary_image)

        for area_index, monitor_area in enumerate(monitor_areas):
            for roi_index, roi in enumerate(monitor_area.ROIS):
                process_roi(binary_image, next_frame_res[1], monitor_area, roi, '%d-%d' % (area_index, roi_index), image_source.get_scale())

        previous_frame = grey_image

    return True


def setRoi(image, roiMsk, roi):
    cv2.fillPoly(roiMsk, [roi], color=[255, 255, 255])
    cv2.polylines(image, [roi], isClosed=True, color=[255, 255, 255])


def process_roi(image, image_index, monitor_area, roi, roi_id, scalef):
    roiMsk = np.zeros(image.shape, np.uint8)
    setRoi(image, roiMsk, np.array(monitor_area.roi_to_poly(roi, scalef)))

    image_roi = cv2.bitwise_and(image, image, mask=roiMsk)
    cv2.imwrite("masked-%d-%s.jpg" % (image_index, roi_id), image_roi)
    fly_cnts = cv2.findContours(image_roi.copy(), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

    fly_coords = None
    points = []
    for fly_contour in fly_cnts[1]:
        bound_rect = cv2.boundingRect(fly_contour)
        pt1 = (bound_rect[0], bound_rect[1])
        pt2 = (bound_rect[0] + bound_rect[2], bound_rect[1] + bound_rect[3])
        points.append(pt1)
        points.append(pt2)
        fly_coords = (pt1[0] + (pt2[0] - pt1[0]) / 2, pt1[1] + (pt2[1] - pt1[1]) / 2)
        area = (pt2[0] - pt1[0]) * (pt2[1] - pt1[1])
        if area > 400:
            fly_coords = None
