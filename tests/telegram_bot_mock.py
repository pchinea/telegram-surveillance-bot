"""
Helper module for bot related mocking.
"""
from threading import Thread
from typing import Callable, Dict, List, Tuple
from unittest.mock import MagicMock

import pytest_mock


class DispatcherMock(MagicMock):
    """Mock object to simulate a telegram bot dispatcher."""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.commands: Dict[str, Callable] = {}
        self.threads: List[Thread] = []

    def add_handler(self, handler) -> None:
        """
        Stores a command handler data.

        Args:
            handler: Command handler to store.
        """
        if hasattr(handler, 'command'):
            if handler.run_async:
                self.commands[handler.command[0]] = self.mock_run_async(handler.callback)
            else:
                self.commands[handler.command[0]] = handler.callback

    def mock_run_async(self, func):
        """
        Decorates a function to execute it into a thread.

        Args:
            func: Function to be decorated.

        Returns:
            Decorated function.

        """
        def wrapped(*args, **kwargs):
            thread = Thread(target=func, args=args, kwargs=kwargs)
            self.threads.append(thread)
            thread.start()
        return wrapped


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
    return mocker.patch('surveillance_bot.bot.Updater', TelegramBotMock)


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


def fake_handler(_, __) -> str:
    """
    Simulates a handler function for bot_config testing.

    Returns:
        Fake string return.
    """
    return 'fake_return'
