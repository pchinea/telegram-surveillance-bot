from hashlib import md5
from time import sleep

import pytest

from src.camera import Camera, CodecNotAvailable
from tests.opencv_mock import mock_video_capture, mock_bad_video_writer, \
    FRAMES_MD5


def test_init_ok(mocker):
    mock_video_capture(mocker, reader=False)

    Camera()


def test_init_codec_not_available(mocker):
    mock_video_capture(mocker, reader=False)
    mock_bad_video_writer(mocker)

    with pytest.raises(CodecNotAvailable):
        Camera()


def test_start_and_stop(mocker):
    mock_video_capture(mocker, reader=False)

    camera = Camera()
    camera.start()
    camera.stop()


def test_get_photo(mocker):
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


def test_get_video(mocker):
    mock_video_capture(mocker)

    camera = Camera()
    camera.start()
    sleep(0.5)  # Wait for fps calculation

    video = camera.get_video(seconds=0.5)
    # Checks MP4 magic numbers
    assert video.read(12) == b'\x00\x00\x00\x1cftypisom'

    camera.stop()


def test_surveillance_mode(mocker):
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


def test_detect_duplicated_frames(mocker):
    mock_video_capture(mocker, fps=5)

    camera = Camera()
    camera.start()

    gen = camera.surveillance_start(video_seconds=0.1)
    assert 'detected' in next(gen)
    camera.surveillance_stop()

    camera.stop()
