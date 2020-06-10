"""
Test suite for Bot class testing.
"""
import logging
from hashlib import md5
from time import sleep

import _pytest.logging
import _pytest.tmpdir
import pytest
import pytest_mock

from src.bot import Bot

from .opencv_mock import FRAMES_MD5, mock_bad_video_writer, mock_video_capture
from .telegram_bot_mock import (
    get_kwargs_grabber,
    get_mocked_context_object,
    get_mocked_update_object,
    mock_run_async,
    mock_telegram_updater
)


def test_init_without_token(caplog: _pytest.logging.caplog) -> None:
    """
    Tests Bot instance when is called without token.

    Args:
        caplog: Fixture for log messages capturing.
    """
    with pytest.raises(SystemExit) as error:
        Bot(token='', username='')
    assert len(caplog.records) == 1
    record: logging.LogRecord = caplog.records[0]
    assert record.levelno == logging.CRITICAL
    assert 'BOT_API_KEY' in record.message
    assert error.type == SystemExit
    assert error.value.code == 1


def test_init_without_username(caplog: _pytest.logging.caplog) -> None:
    """
    Tests Bot instance when is called without username.

    Args:
        caplog: Fixture for log messages capturing.
    """
    with pytest.raises(SystemExit) as error:
        Bot(token='FAKE_TOKEN', username='')
    assert len(caplog.records) == 1
    record: logging.LogRecord = caplog.records[0]
    assert record.levelno == logging.CRITICAL
    assert 'AUTHORIZED_USER' in record.message
    assert error.type == SystemExit
    assert error.value.code == 1


def test_init_without_camera(
        caplog: _pytest.logging.caplog,
        mocker: pytest_mock.mocker
) -> None:
    """
    Tests Bot instantiation when device is not reachable.

    Args:
        caplog: Fixture for log messages capturing.
        mocker: Fixture for object mocking.
    """
    mock_video_capture(mocker, reader=False, opened=False)
    with pytest.raises(SystemExit) as error:
        Bot(token='FAKE_TOKEN', username='FAKE_USER')
    assert len(caplog.records) == 1
    record: logging.LogRecord = caplog.records[0]
    assert record.levelno == logging.CRITICAL
    assert 'camera' in record.message
    assert error.type == SystemExit
    assert error.value.code == 2


def test_init_without_available_codec(
        caplog: _pytest.logging.caplog,
        mocker: pytest_mock.mocker
) -> None:
    """
    Tests Bot instantiation when codec is not available.

    Args:
        caplog: Fixture for log messages capturing.
        mocker: Fixture for object mocking.
    """
    mock_video_capture(mocker, reader=False)
    mock_bad_video_writer(mocker)
    with pytest.raises(SystemExit) as error:
        Bot(token='FAKE_TOKEN', username='FAKE_USER')
    assert len(caplog.records) == 1
    record: logging.LogRecord = caplog.records[0]
    assert record.levelno == logging.CRITICAL
    assert 'codec' in record.message
    assert error.type == SystemExit
    assert error.value.code == 2


def test_init_logging_level(mocker: pytest_mock.mocker) -> None:
    """
    Tests Bot instantiation with logging level modification.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_telegram_updater(mocker)
    mock_video_capture(mocker, reader=False)

    # Default level (WARNING)
    bot = Bot(token='FAKE_TOKEN', username='FAKE_USER')
    assert bot.logger.getEffectiveLevel() == logging.WARNING

    # Change level
    bot = Bot(token='FAKE_TOKEN', username='FAKE_USER', log_level='INFO')
    assert bot.logger.getEffectiveLevel() == logging.INFO


def test_persistence_dir(
        tmp_path: _pytest.tmpdir.tmp_path,
        mocker: pytest_mock.mocker
) -> None:
    """
    Tests Bot instantiation passing a directory for data persistence.

    Args:
        tmp_path: Fixture for temporary path handling.
        mocker: Fixture for object mocking.
    """
    mock_telegram_updater(mocker)
    mock_video_capture(mocker, reader=False)

    persistence_dir = tmp_path / "test"
    assert not persistence_dir.exists()

    Bot(
        token='FAKE_TOKEN',
        username='FAKE_USER',
        persistence_dir=str(persistence_dir)
    )
    assert persistence_dir.exists()


def test_start_and_stop(
        caplog: _pytest.logging.caplog,
        mocker: pytest_mock.mocker
) -> None:
    """
    Tests Bot process starting and stopping.

    Args:
        caplog: Fixture for log messages capturing.
        mocker: Fixture for object mocking.
    """
    mock_telegram_updater(mocker)
    mock_video_capture(mocker, reader=False)
    bot = Bot(token='FAKE_TOKEN', username='FAKE_USER')
    bot.start()
    assert len(caplog.records) == 2
    record = caplog.records[0]
    assert record.levelno == logging.INFO
    assert 'started' in record.message
    record = caplog.records[1]
    assert record.levelno == logging.INFO
    assert 'stopped' in record.message


def test_command_wrapper(
        caplog: _pytest.logging.caplog,
        mocker: pytest_mock.mocker
) -> None:
    """
    Tests bot commands wrapping.

    Args:
        caplog: Fixture for log messages capturing.
        mocker: Fixture for object mocking.
    """
    mock_telegram_updater(mocker)
    mock_video_capture(mocker, reader=False)
    bot = Bot(token='FAKE_TOKEN', username='FAKE_USER')

    update = get_mocked_update_object()
    context = get_mocked_context_object()

    # Checks default configuration
    bot.updater.dispatcher.commands['start'](update, context)
    assert len(context.bot_data) == 5

    # Unauthorized
    update.effective_chat.username = 'BAD_USER'
    bot.updater.dispatcher.commands['start'](update, context)
    assert len(caplog.records) == 1
    record: logging.LogRecord = caplog.records[0]
    assert record.levelno == logging.WARNING
    assert 'Unauthorized' in record.message


def test_error_handler(
        caplog: _pytest.logging.caplog,
        mocker: pytest_mock.mocker
) -> None:
    """
    Tests error handler method.

    Args:
        caplog: Fixture for log messages capturing.
        mocker: Fixture for object mocking.
    """
    mock_telegram_updater(mocker)
    mock_video_capture(mocker, reader=False)
    bot = Bot(token='FAKE_TOKEN', username='FAKE_USER')

    update = get_mocked_update_object()
    context = get_mocked_context_object()

    parameters, context.bot.send_message = get_kwargs_grabber()
    getattr(bot, '_error')(update, context)

    assert len(caplog.records) == 1
    record: logging.LogRecord = caplog.records[0]
    assert record.levelno == logging.WARNING
    assert 'caused error' in record.message

    assert len(parameters) == 1
    assert 'internal error' in parameters[0]['text']


def test_start_command(mocker: pytest_mock.mocker) -> None:
    """
    Tests "start" command invocation.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_telegram_updater(mocker)
    mock_video_capture(mocker, reader=False)
    bot = Bot(token='FAKE_TOKEN', username='FAKE_USER')

    update = get_mocked_update_object()
    context = get_mocked_context_object()

    parameters, update.message.reply_text = get_kwargs_grabber()
    bot.updater.dispatcher.commands['start'](update, context)
    assert len(parameters) == 2

    # Welcome message
    assert 'Welcome' in parameters[0]['text']

    # Help message
    assert 'available commands:' in parameters[1]['text']

    # Reply keyboard
    assert parameters[1]['reply_markup']['keyboard'] == [
        ['/get_photo', '/get_video'],
        ['/surveillance_start']
    ]


def test_get_photo_command(mocker: pytest_mock.mocker) -> None:
    """
    Tests "get_photo" command invocation.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_telegram_updater(mocker)
    mock_video_capture(mocker)
    bot = Bot(token='FAKE_TOKEN', username='FAKE_USER')
    bot.camera.start()

    update = get_mocked_update_object()
    context = get_mocked_context_object()
    context.bot_data['timestamp'] = False

    action_params, context.bot.send_chat_action = get_kwargs_grabber()
    photo_params, context.bot.send_photo = get_kwargs_grabber()

    bot.updater.dispatcher.commands['get_photo'](update, context)
    assert action_params[0]['action'] == 'upload_photo'
    assert md5(photo_params[0]['photo'].read()).hexdigest() in FRAMES_MD5
    bot.camera.stop()


def test_get_video_command(mocker: pytest_mock.mocker) -> None:
    """
    Tests "get_video" command invocation.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_telegram_updater(mocker)
    mock_video_capture(mocker)
    bot = Bot(token='FAKE_TOKEN', username='FAKE_USER')
    bot.camera.start()
    sleep(0.2)  # Wait for fps calculation

    update = get_mocked_update_object()
    context = get_mocked_context_object()
    context.bot_data['od_video_duration'] = 0.1

    action_params, context.bot.send_chat_action = get_kwargs_grabber()
    video_params, context.bot.send_video = get_kwargs_grabber()

    bot.updater.dispatcher.commands['get_video'](update, context)
    assert action_params[0]['action'] == 'record_video'
    assert action_params[1]['action'] == 'upload_video'
    assert video_params[0]['video'].read(12) == b'\x00\x00\x00\x1cftypisom'
    bot.camera.stop()


def test_surveillance_start_command(mocker: pytest_mock.mocker) -> None:
    """
    Tests "surveillance_start" command invocation.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_telegram_updater(mocker)
    mock_video_capture(mocker)
    threads = mock_run_async(mocker)
    bot = Bot(token='FAKE_TOKEN', username='FAKE_USER')
    bot.camera.start()
    sleep(0.2)  # Wait for fps calculation

    update = get_mocked_update_object()
    context = get_mocked_context_object()
    context.bot_data['srv_video_duration'] = 0.3
    context.bot_data['srv_picture_interval'] = 0.2

    action_params, context.bot.send_chat_action = get_kwargs_grabber()
    parameters, update.message.reply_text = get_kwargs_grabber()

    bot.updater.dispatcher.commands['surveillance_status'](update, context)
    bot.updater.dispatcher.commands['surveillance_start'](update, context)
    bot.updater.dispatcher.commands['surveillance_status'](update, context)
    while len(action_params) < 4:
        pass
    bot.updater.dispatcher.commands['surveillance_stop'](update, context)

    threads[0].join()
    assert 'not active' in parameters[0]['text']
    assert 'started' in parameters[1]['text']
    assert 'is active' in parameters[2]['text']
    assert 'DETECTED' in parameters[3]['text']
    assert 'Recording' in parameters[4]['text']

    assert action_params[0]['action'] == 'record_video'
    assert action_params[1]['action'] == 'upload_photo'
    assert action_params[2]['action'] == 'record_video'
    assert action_params[3]['action'] == 'upload_video'
    bot.camera.stop()


def test_surveillance_errors(mocker: pytest_mock.mocker) -> None:
    """
    Tests errors in "start" command invocation.

    Args:
        mocker: Fixture for object mocking.
    """
    mock_telegram_updater(mocker)
    mock_video_capture(mocker)
    threads = mock_run_async(mocker)
    bot = Bot(token='FAKE_TOKEN', username='FAKE_USER')
    bot.camera.start()
    sleep(0.1)  # Wait for fps calculation

    update = get_mocked_update_object()
    context = get_mocked_context_object()

    action_params, context.bot.send_chat_action = get_kwargs_grabber()
    parameters, update.message.reply_text = get_kwargs_grabber()

    bot.updater.dispatcher.commands['surveillance_stop'](update, context)
    bot.updater.dispatcher.commands['surveillance_start'](update, context)
    bot.updater.dispatcher.commands['surveillance_start'](update, context)
    while len(action_params) < 1:
        pass
    bot.updater.dispatcher.commands['surveillance_stop'](update, context)

    threads[0].join()
    assert 'not started' in parameters[0]['text']
    assert 'already started' in parameters[2]['text']
    bot.camera.stop()
