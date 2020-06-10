"""
Test suite for main script testing.
"""
import logging

import _pytest.logging
import pytest_mock

import src.main


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
    mocker.patch('src.main.BOT_API_TOKEN', 'FAKE_TOKEN')
    mocker.patch('src.main.AUTHORIZED_USER', 'FAKE_USER')
    mocker.patch('src.main.BOT_LOG_LEVEL', 'INFO')
    mocker.patch('src.main.bot.Updater')
    mocker.patch('cv2.VideoCapture')
    mocker.patch('cv2.VideoWriter')

    src.main.main()
    assert len(caplog.records) == 2
    assert caplog.records[0].levelno == logging.INFO
    assert 'started' in caplog.records[0].message
    assert caplog.records[1].levelno == logging.INFO
    assert 'stopped' in caplog.records[1].message
