import cv2
import _pickle as cPickle
import numpy as np

class Arena():
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
        self._data_buffer = np.zeros((1, 2), dtype=np.int)
        # shape ( flies, self._frames_per_period, (x,y) ) Contains the coordinates of the last frame
        self._data_min = np.zeros((1, self._frames_per_period, 2), dtype=np.int)

    def add_roi(self, roi, n_flies=1):
        self.ROIS.append(roi)
        self._points_to_track.append(n_flies)
        self._beams.append(self._get_midline(roi))

    def _roi_to_rect(self, roi, scale=None):
        """
        Converts a ROI (a tuple of four points coordinates) into
        a Rect (a tuple of two points coordinates)
        """
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = roi
        lx = min([x1, x2, x3, x4])
        rx = max([x1, x2, x3, x4])
        uy = min([y1, y2, y3, y4])
        ly = max([y1, y2, y3, y4])
        return ((lx, uy), (rx, ly))

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
        (x1, y1), (x2, y2) = self._roi_to_rect(roi)
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
        self._data_buffer = np.zeros((n_rois, 2), dtype=np.int)
        self._data_min = np.zeros((n_rois, self._frames_per_period, 2), dtype=np.int)

        for roi in self.ROIS:
            self._beams.append(self._get_midline(roi))


class ImageSource():

    def __init__(self, resolution=None, data_resolution=None):
        self._resolution = resolution
        self._data_resolution = data_resolution

    def get_scale(self):
        if self._data_resolution is not None and self._resolution is not None:
            return (self._data_resolution[0] / self._resolution[0], self._data_resolution[1] / self._resolution[1])
        else:
            return None

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

        super(MovieFile, self).__init__(resolution=resolution, data_resolution=(width, height))

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


def process_image_frames(image_source, arena):
    previous_frame = None
    while True:
        next_frame_res = image_source.get_image()
        if not next_frame_res[0]:
            return
        frame_image = next_frame_res[2]

        grey_image = cv2.cvtColor(frame_image, cv2.COLOR_BGR2GRAY)
        grey_image = cv2.GaussianBlur(grey_image, (21, 21), 0)

        roiMsk = grey_image.clone()

        if previous_frame is None:
            previous_frame = grey_image
            continue

        frame_delta = cv2.absdiff(previous_frame, grey_image)
        thresh = cv2.threshold(frame_delta, 20, 255, cv2.THRESH_BINARY)[1]

        # cv2.imwrite("grey%d.jpg" % next_frame_res[1], grey_image)
        # cv2.imwrite("frame%d.jpg" % next_frame_res[1], frame_delta)

        thresh = cv2.dilate(thresh, None, iterations=2)
        thresh = cv2.erode(thresh, None, iterations=2)

        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # cv2.imwrite("thresh%d.jpg" % next_frame_res[1], thresh)
        # cv2.imwrite("cnts_0_%d.jpg" % next_frame_res[1], cnts[0])

        # print("!!!! CNTS", cnts[1])
        for roi in arena.ROIS:
            cv2.fillPoly(cnts[0], [np.array(arena.roi_to_poly(roi, image_source.get_scale()))], color=[255,255,255])
            # cv2.polylines(cnts[0], [np.array(list(arena.roi_to_rect(roi, image_source.get_scale())))], isClosed=True, color=[255, 255, 255])

        cv2.imwrite("cnts_1_%d.jpg" % next_frame_res[1], cnts[0])

        previous_frame = grey_image

    # temp = frame_image.copy()
    # difference = frame_image.copy()
    # roiMsk = grey_image.copy()
    # roiWrk = grey_image.copy()
    #
    # print("!!! SHAPE", grey_image.shape, temp.shape)
    #
    # if first_frame:
    #     moving_average = cv2.cvtColor(frame_image, cv2.COLOR_BGR2GRAY)
    #     tt = cv.CreateImage(cv.GetSize(frame_image), cv2.IPL_DEPTH_32F, 3)
    #     print("!!!!", tt)



    #!!!!!! cv2.imshow('window-name',next_frame_res[2])

    return True
