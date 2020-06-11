"""
Helper module for OpenCV related mocking.
"""
import os
import time
from hashlib import md5
from io import BytesIO
from typing import Callable, List, Tuple

import cv2
import numpy as np
import pytest_mock

FPS = 30
FRAME_SIZE = (640, 480)

FRAMES: List[np.ndarray] = [
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


def _get_reader_mock(fps=FPS) -> Callable[[], Tuple[bool, np.ndarray]]:
    """
    Generates a function to simulate video capture read method.

    Args:
        fps: Sets framerate for reading simulation.

    Returns:
        The mocked read method.
    """
    index = 0
    last = time.time() - 1  # don't wait for the first frame

    def read() -> Tuple[bool, np.ndarray]:
        nonlocal index, last
        while time.time() < last + (1 / fps):
            pass
        frame = FRAMES[index % 5]
        index += 1
        last = time.time()
        return True, frame

    return read


def mock_video_capture(
        mocker: pytest_mock.mocker,
        reader=True,
        opened=True,
        fps=FPS
) -> None:
    """
    Patches VideoCapture class to simulate a camera device.

    Args:
        mocker: Fixture for object mocking.
        reader: Patches `read` method if True.
        opened: Patches `isOpened` method if True.
        fps: Sets framerate for reading simulation.
    """
    video_capture = mocker.patch('cv2.VideoCapture')
    if reader:
        video_capture().read = _get_reader_mock(fps)
    video_capture().isOpened.return_value = opened


def mock_bad_video_writer(mocker: pytest_mock.mocker) -> None:
    """
    Patches VideoWriter to simulate that there is no available codec.

    Args:
        mocker: Fixture for object mocking.
    """
    video_writer = mocker.patch('cv2.VideoWriter')
    video_writer().isOpened.return_value = False
