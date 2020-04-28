""" Utils module for Surveillance Telegram Bot.


This module contains helpers functions, decorators and configuration.
"""
import logging
from functools import wraps
from typing import Callable, Any

from telegram import Update
from telegram.ext import CallbackContext

# Logging config
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


# Decorators
def restricted(username: str):
    """Decorator for restricting handler execution to given username

    Args:
        username: Authorized username.

    Returns:
        Decorated handler.
    """
    logger = logging.getLogger(__name__)

    def decorator(func: Callable[[object, Update, CallbackContext], Any]):
        @wraps(func)
        def command_func(obj: object,
                         update: Update,
                         context: CallbackContext) -> Any:
            if update.effective_chat.username != username:
                logger.warning(
                    'Unauthorized call to "%s" command by @%s',
                    func.__name__,
                    update.effective_chat.username
                )
                update.message.reply_text("Unauthorized")
                return None
            return func(obj, update, context)
        return command_func

    return decorator
