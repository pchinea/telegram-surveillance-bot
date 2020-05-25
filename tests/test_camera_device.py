import time

import numpy as np
import pytest

from src.camera import CameraDevice, CameraConnectionError
from tests.opencv_mock import FPS, FRAME_SIZE, mock_video_capture


def test_init_ok(mocker):
    mock_video_capture(mocker, reader=False)

    CameraDevice()


def test_init_camera_connection_error(mocker):
    mock_video_capture(mocker, reader=False, opened=False)

    with pytest.raises(CameraConnectionError):
        CameraDevice()


def test_start_and_stop(mocker):
    mock_video_capture(mocker, reader=False)

    camera_device = CameraDevice()
    camera_device.start()
    camera_device.stop()


def test_frame_size(mocker):
    mock_video_capture(mocker)

    camera_device = CameraDevice()
    camera_device.start()
    assert camera_device.frame_size == FRAME_SIZE
    camera_device.stop()


def test_fps(mocker):
    mock_video_capture(mocker)

    camera_device = CameraDevice()
    camera_device.start()
    time.sleep(0.5)
    assert abs(camera_device.fps) - FPS < 5  # FPS +/- 5
    camera_device.stop()


def test_read(mocker):
    mock_video_capture(mocker)

    camera_device = CameraDevice()
    camera_device.start()
    frame_id, frame = camera_device.read()

    # Check types
    assert isinstance(frame_id, int)
    assert isinstance(frame, np.ndarray)

    # Check new frame
    frame_id = camera_device.read()[0]
    time.sleep(1 / FPS * 2)  # Wait until next frame is available
    assert frame_id < camera_device.read()[0]

    camera_device.stop()
