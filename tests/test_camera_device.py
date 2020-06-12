"""
Test suite for CameraDevice class testing.
"""
import time

import numpy as np
import pytest
import pytest_mock

from opencv_mock import FPS, FRAME_SIZE, mock_video_capture
from surveillance_bot.camera import CameraConnectionError, CameraDevice


def test_init_ok(mocker: pytest_mock.mocker) -> None:
    """
    Tests CameraDevice instance construction.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_video_capture(mocker, reader=False)

    CameraDevice()


def test_init_camera_connection_error(mocker: pytest_mock.mocker) -> None:
    """
    Tests CameraDevice instantiation when device is not reachable.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_video_capture(mocker, reader=False, opened=False)

    with pytest.raises(CameraConnectionError):
        CameraDevice()


def test_start_and_stop(mocker: pytest_mock.mocker) -> None:
    """
    Tests camera device starting and stopping.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_video_capture(mocker, reader=False)

    camera_device = CameraDevice()
    camera_device.start()
    camera_device.stop()


def test_frame_size(mocker: pytest_mock.mocker) -> None:
    """
    Tests frame size value.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_video_capture(mocker)

    camera_device = CameraDevice()
    camera_device.start()
    assert camera_device.frame_size == FRAME_SIZE
    camera_device.stop()


def test_fps(mocker: pytest_mock.mocker) -> None:
    """
    Tests fps value.

    The testing has +/- 5 fps of tolerance.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_video_capture(mocker)

    camera_device = CameraDevice()
    camera_device.start()
    time.sleep(0.5)
    assert abs(camera_device.fps) - FPS < 5  # FPS +/- 5
    camera_device.stop()


def test_read(mocker: pytest_mock.mocker) -> None:
    """
    Tests frame reading method.

    Args:
        mocker: Fixture for object mocking.
    """
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
