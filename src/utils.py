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
logger = logging.getLogger('TestSurveillanceBot')


# Decorators
def restricted(username: str):
    """Decorator for restricting handler execution to given username

    Args:
        username (str): Authorized username.
    """

    def decorator(func: Callable[[Update, CallbackContext], Any]):
        @wraps(func)
        def command_func(update: Update, context: CallbackContext) -> Any:
            if update.effective_chat.username != username:
                logger.warning(
                    'Unauthorized call to "%s" command by @%s',
                    func.__name__,
                    update.effective_chat.username
                )
                update.message.reply_text("Unauthorized")
                return None
            return func(update, context)
        return command_func

    return decorator
