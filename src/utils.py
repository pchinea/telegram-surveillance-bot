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
    """ Restricts function to given username """

    def decorator(func: Callable[[Update, CallbackContext], Any]):
        @wraps(func)
        def command_func(update: Update, context: CallbackContext) -> Any:
            if update.effective_chat.username != username:
                logger.warning(
                    f'Unauthorized call to "{func.__name__}" command '
                    f'by @{update.effective_chat.username}'
                )
                update.message.reply_text("Unauthorized")
                return None
            return func(update, context)
        return command_func

    return decorator
