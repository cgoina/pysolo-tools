import cv2



class Arena():
    """
    The arena defines the space where the flies move
    Carries information about the ROI (coordinates defining each vial) and
    the number of flies in each vial

    The class monitor takes care of the camera
    The class arena takes care of the flies
    """
    def __init__(self):
        self.ROIS = [] # regions of interest
        self.beams = [] # beams: absolute coordinates
        self.ROAS = [] # regions of actions


class ImageSource():

    def __init__(self, resolution=None):
        self.resolution = resolution

    def get_resolution(self):
        return self.resolution


class MovieFile(ImageSource):

    def __init__(self, movie_file_path, step=1, start=None, end=None):
        """
        :param movie_file_path: path to the movie file
        :param step: distance between frames
        :param start: start frame. If None starts at first
        :param end: last frame. If None ends at last
        """
        super(MovieFile, self).__init__()
        self.movie_file_path = movie_file_path
        self.start = start or 0
        self.step = step or 1

        self.capture = cv2.VideoCapture(movie_file_path)
        height = self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        width  = self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.resolution = (width, height)

        print("!!!! CAPTURE", self.capture, self.resolution)

