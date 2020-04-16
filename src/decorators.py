from functools import wraps
from typing import Callable, Any

from telegram import Update, ChatAction
from telegram.ext import CallbackContext

from src.utils import logger


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


def send_action(action: str):
    """Sends `action` while processing func command."""

    def decorator(func: Callable[[Update, CallbackContext], Any]):
        @wraps(func)
        def command_func(update: Update, context: CallbackContext) -> Any:
            context.bot.send_chat_action(
                chat_id=update.effective_message.chat_id,
                action=action
            )
            return func(update, context)
        return command_func

    return decorator


send_upload_photo_action = send_action(ChatAction.UPLOAD_PHOTO)
send_record_video_action = send_action(ChatAction.RECORD_VIDEO)
