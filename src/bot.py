import os

from telegram import Update, ReplyKeyboardMarkup, ChatAction
from telegram.ext import Updater, CommandHandler, CallbackContext, run_async

from capture import Camera
from utils import logger, restricted

authorized_user = os.environ.get('AUTHORIZED_USER')


@restricted(authorized_user)
def start(update: Update, context: CallbackContext) -> None:
    logger.info('Received "start" command')
    custom_keyboard = [
        ['/get_photo', '/get_video'],
        ['/surveillance_start', '/surveillance_stop']
    ]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Test Surveillance Bot by Pablo Chinea",
        reply_markup=reply_markup
    )


@restricted(authorized_user)
def get_photo(update: Update, context: CallbackContext) -> None:
    logger.info('Received "get_photo" command')

    # Upload photo
    context.bot.send_chat_action(
        chat_id=update.effective_message.chat_id,
        action=ChatAction.UPLOAD_PHOTO
    )
    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=cam.get_photo(),
    )


@restricted(authorized_user)
def get_video(update: Update, context: CallbackContext) -> None:
    logger.info('Received "get_video" command')

    # Record video
    context.bot.send_chat_action(
        chat_id=update.effective_message.chat_id,
        action=ChatAction.RECORD_VIDEO
    )
    video = cam.get_video()

    # Upload video
    context.bot.send_chat_action(
        chat_id=update.effective_message.chat_id,
        action=ChatAction.UPLOAD_VIDEO
    )
    context.bot.send_video(
        chat_id=update.effective_chat.id,
        video=video,
    )


@run_async
@restricted(authorized_user)
def surveillance_start(update: Update, context: CallbackContext) -> None:
    logger.info('Received "surveillance_start" command')
    for data in cam.surveillance_start():
        if 'detected' in data:
            update.message.reply_text('Motion detected!')
            context.bot.send_chat_action(
                chat_id=update.effective_message.chat_id,
                action=ChatAction.RECORD_VIDEO
            )
        if 'photo' in data:
            context.bot.send_chat_action(
                chat_id=update.effective_message.chat_id,
                action=ChatAction.UPLOAD_PHOTO
            )
            context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=data['photo'],
                caption=f'Capture {data["id"]}/{data["total"]}'
            )
            context.bot.send_chat_action(
                chat_id=update.effective_message.chat_id,
                action=ChatAction.RECORD_VIDEO
            )
        if 'video' in data:
            context.bot.send_chat_action(
                chat_id=update.effective_message.chat_id,
                action=ChatAction.UPLOAD_VIDEO
            )
            context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=data['video']
            )
    logger.info('Surveillance stop')


@restricted(authorized_user)
def surveillance_stop(update: Update, context: CallbackContext) -> None:
    logger.info('Received "surveillance_stop" command')
    cam.surveillance_stop()


if __name__ == '__main__':
    cam = Camera()
    cam.start()
    token = os.environ.get('BOT_API_TOKEN')
    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('get_photo', get_photo))
    dispatcher.add_handler(CommandHandler('get_video', get_video))
    dispatcher.add_handler(
        CommandHandler('surveillance_start', surveillance_start)
    )
    dispatcher.add_handler(
        CommandHandler('surveillance_stop', surveillance_stop)
    )

    updater.start_polling()
    logger.info('Bot started')

    updater.idle()

    cam.stop()
    logger.info('Bot stopped')
