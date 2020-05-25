import os
import time
from hashlib import md5
from io import BytesIO

import cv2

FPS = 30
FRAME_SIZE = (640, 480)

FRAMES = [
    cv2.imread(
        os.path.join(
            os.path.dirname(__file__),
            f'frames/frame_{i}.jpg'
        )
    ) for i in range(5)
]

FRAMES_MD5 = [
    md5(
        BytesIO(cv2.imencode(".jpg", f)[1]).read()
    ).hexdigest() for f in FRAMES
]


def _get_reader_mock(fps=FPS):
    index = 0
    last = time.time() - 1  # don't wait for the first frame

    def read():
        nonlocal index, last
        while time.time() < last + (1 / fps):
            pass
        frame = FRAMES[index % 5]
        index += 1
        last = time.time()
        return True, frame

    return read


def mock_video_capture(mocker, reader=True, opened=True, fps=FPS):
    video_capture = mocker.patch('cv2.VideoCapture')
    if reader:
        video_capture().read = _get_reader_mock(fps)
    video_capture().isOpened.return_value = opened


def mock_bad_video_writer(mocker):
    video_writer = mocker.patch('cv2.VideoWriter')
    video_writer().isOpened.return_value = False
