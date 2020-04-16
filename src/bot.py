import os

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext

from src.capture import Camera
from src.decorators import restricted, send_upload_photo_action, \
    send_record_video_action
from src.utils import logger


authorized_user = os.environ.get('AUTHORIZED_USER')


@restricted(authorized_user)
def start(update: Update, context: CallbackContext) -> None:
    logger.info('Received "start" command')
    custom_keyboard = [['/get_photo', '/get_video']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Test Surveillance Bot by Pablo Chinea",
        reply_markup=reply_markup
    )


@restricted(authorized_user)
@send_upload_photo_action
def get_photo(update: Update, context: CallbackContext) -> None:
    logger.info('Received "get_photo" command')
    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=cam.get_photo(),
    )


@restricted(authorized_user)
@send_record_video_action
def get_video(update: Update, context: CallbackContext) -> None:
    logger.info('Received "get_video" command')
    video = cam.get_video()
    context.bot.send_chat_action(
        chat_id=update.effective_message.chat_id,
        action='upload_video'
    )
    context.bot.send_video(
        chat_id=update.effective_chat.id,
        video=video,
    )


if __name__ == '__main__':
    cam = Camera()
    cam.start()
    token = os.environ.get('BOT_API_TOKEN')
    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('get_photo', get_photo))
    dispatcher.add_handler(CommandHandler('get_video', get_video))

    updater.start_polling()
    logger.info('Bot started')

    updater.idle()

    cam.stop()
    logger.info('Bot stopped')
