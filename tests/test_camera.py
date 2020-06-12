"""
Test suite for Camera class testing.
"""
from hashlib import md5
from time import sleep

import pytest
import pytest_mock

from surveillance_bot.camera import Camera, CodecNotAvailable

from .opencv_mock import FRAMES_MD5, mock_bad_video_writer, mock_video_capture


def test_init_ok(mocker: pytest_mock.mocker) -> None:
    """
    Tests Camera instance construction.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_video_capture(mocker, reader=False)

    Camera()


def test_init_codec_not_available(mocker: pytest_mock.mocker) -> None:
    """
    Tests Camera instantiation when codec is not available.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_video_capture(mocker, reader=False)
    mock_bad_video_writer(mocker)

    with pytest.raises(CodecNotAvailable):
        Camera()


def test_start_and_stop(mocker: pytest_mock.mocker) -> None:
    """
    Tests camera process starting and stopping.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_video_capture(mocker, reader=False)

    camera = Camera()
    camera.start()
    camera.stop()


def test_get_photo(mocker: pytest_mock.mocker) -> None:
    """
    Tests photo taking method.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_video_capture(mocker)

    camera = Camera()
    camera.start()

    # Photo without timestamp
    image = camera.get_photo(False)
    assert md5(image.read()).hexdigest() in FRAMES_MD5

    # Photo with timestamp
    image = camera.get_photo()
    assert md5(image.read()).hexdigest() not in FRAMES_MD5

    camera.stop()


def test_get_video(mocker: pytest_mock.mocker) -> None:
    """
    Tests video taking method.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_video_capture(mocker)

    camera = Camera()
    camera.start()
    sleep(0.5)  # Wait for fps calculation

    video = camera.get_video(seconds=0.5)
    # Checks MP4 magic numbers
    assert video.read(12) == b'\x00\x00\x00\x1cftypisom'

    camera.stop()


def test_surveillance_mode(mocker: pytest_mock.mocker) -> None:
    """
    Tests surveillance mode process.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_video_capture(mocker)

    camera = Camera()
    camera.start()
    sleep(0.5)  # Wait for fps calculation

    gen = camera.surveillance_start(video_seconds=1, picture_seconds=0.8)

    assert 'detected' in next(gen)
    assert camera.is_surveillance_active is True
    assert 'photo' in next(gen)
    assert 'video' in next(gen)
    assert 'detected' in next(gen)
    camera.surveillance_stop()
    assert camera.is_surveillance_active is False

    camera.stop()


def test_detect_duplicated_frames(mocker: pytest_mock.mocker) -> None:
    """
    Tests duplicated frames detection.

    Frame requesting can be faster than device frame grabbing, so the same
    frame can be retrieved more than once. This test simulates a very low
    framerate and then tries to detect motion (two consecutive frames are
    different).

    Args:
        mocker: Fixture for object mocking.
    """
    mock_video_capture(mocker, fps=5)

    camera = Camera()
    camera.start()

    gen = camera.surveillance_start(video_seconds=0.1)
    assert 'detected' in next(gen)
    camera.surveillance_stop()

    camera.stop()
