from threading import Thread
from typing import List, Tuple, Callable
from unittest.mock import MagicMock

import pytest_mock


class DispatcherMock(MagicMock):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.commands = {}

    def add_handler(self, handler) -> None:
        if isinstance(handler, CommandHandlerMock):
            self.commands[handler.commands[0]] = handler.commands[1]


class TelegramBotMock(MagicMock):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.dispatcher = DispatcherMock()


class CommandHandlerMock(MagicMock):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.commands = args


def mock_telegram_updater(mocker: pytest_mock.mocker) -> TelegramBotMock:
    mocker.patch('src.bot.CommandHandler', CommandHandlerMock)
    return mocker.patch('src.bot.Updater', TelegramBotMock)


def mock_run_async(mocker: pytest_mock.mocker) -> List[Thread]:
    threads: List[Thread] = []

    def run_async(func, *args, **kwargs):
        nonlocal threads
        t = Thread(target=func, args=args, kwargs=kwargs)
        threads.append(t)
        t.start()

    dispatcher = mocker.patch('telegram.ext.dispatcher.Dispatcher')
    dispatcher.get_instance().run_async = run_async
    return threads


def get_mocked_update_object() -> MagicMock:
    update = MagicMock()
    update.effective_chat.username = 'FAKE_USER'
    return update


def get_mocked_context_object() -> MagicMock:
    context = MagicMock()
    context.bot_data = {}
    return context


def get_kwargs_grabber() -> Tuple[List, Callable]:
    parameters: List = []

    def kwargs_grabber(**kwargs) -> MagicMock:
        nonlocal parameters
        parameters.append(kwargs)
        return MagicMock()
    return parameters, kwargs_grabber
