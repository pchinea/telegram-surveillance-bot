"""
Helper module for bot related mocking.
"""
from threading import Thread
from typing import List, Tuple, Callable, Dict
from unittest.mock import MagicMock

import pytest_mock


class DispatcherMock(MagicMock):
    """Mock object to simulate a telegram bot dispatcher."""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.commands: Dict[str, Callable] = {}

    def add_handler(self, handler) -> None:
        """
        Stores a command handler data.

        Args:
            handler: Command handler to store.
        """
        if hasattr(handler, 'command'):
            self.commands[handler.command[0]] = handler.callback


class TelegramBotMock(MagicMock):
    """Mock object to simulate a telegram bot."""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.dispatcher = DispatcherMock()


def mock_telegram_updater(mocker: pytest_mock.mocker) -> TelegramBotMock:
    """
    Mocks telegram bot updater object.

    Args:
        mocker: Fixture for object mocking.

    Returns:
        A mocked telegram bot instance.
    """
    return mocker.patch('src.bot.Updater', TelegramBotMock)


def mock_run_async(mocker: pytest_mock.mocker) -> List[Thread]:
    """
    Mocks telegram bot run_async decorator.

    The generated function simulates the original behavior executing the
    decorated function into a thread.

    Args:
        mocker: Fixture for object mocking.

    Returns:
        An initially empty list, every time the mocked function is called the
        created thread is appended into it.
    """
    threads: List[Thread] = []

    def run_async(func, *args, **kwargs):
        nonlocal threads
        thread = Thread(target=func, args=args, kwargs=kwargs)
        threads.append(thread)
        thread.start()

    dispatcher = mocker.patch('telegram.ext.dispatcher.Dispatcher')
    dispatcher.get_instance().run_async = run_async
    return threads


def get_mocked_update_object() -> MagicMock:
    """
    Mocks telegram bot update object.

    Returns:
        A mocked telegram bot update instance.
    """
    update = MagicMock()
    update.effective_chat.username = 'FAKE_USER'

    def answer():
        update.callback_query.answered = True

    update.callback_query.answered = False
    update.callback_query.answer = answer
    return update


def get_mocked_context_object() -> MagicMock:
    """
    Mocks telegram context update object.

    Returns:
        A mocked telegram context update instance.
    """
    context = MagicMock()
    context.bot_data = {}
    context.user_data = {}
    return context


def get_kwargs_grabber() -> Tuple[List, Callable]:
    """
    Creates a grabber function to capture the named arguments that the
    function is called with.

    Returns:
        A tuple with two values:
            * An initially empty list, every time the grabber function is
              called the named arguments are appended into it.
            * The grabber function.
    """
    parameters: List = []

    def kwargs_grabber(**kwargs) -> MagicMock:
        nonlocal parameters
        parameters.append(kwargs)
        return MagicMock()
    return parameters, kwargs_grabber
