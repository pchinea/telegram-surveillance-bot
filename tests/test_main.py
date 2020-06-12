"""
Test suite for main script testing.
"""
import logging

import _pytest.logging
import pytest_mock

import surveillance_bot.__main__


def test_main(
        caplog: _pytest.logging.caplog,
        mocker: pytest_mock.mocker
) -> None:
    """
    Tests main script execution.

    Args:
        caplog: Fixture for log messages capturing.
        mocker: Fixture for object mocking.
    """
    mocker.patch('surveillance_bot.__main__.BOT_API_TOKEN', 'FAKE_TOKEN')
    mocker.patch('surveillance_bot.__main__.AUTHORIZED_USER', 'FAKE_USER')
    mocker.patch('surveillance_bot.__main__.BOT_LOG_LEVEL', 'INFO')
    mocker.patch('surveillance_bot.__main__.bot.Updater')
    mocker.patch('cv2.VideoCapture')
    mocker.patch('cv2.VideoWriter')

    surveillance_bot.__main__.main()
    assert len(caplog.records) == 2
    assert caplog.records[0].levelno == logging.INFO
    assert 'started' in caplog.records[0].message
    assert caplog.records[1].levelno == logging.INFO
    assert 'stopped' in caplog.records[1].message
