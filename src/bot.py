import logging
import os

from telegram import Update, ReplyKeyboardMarkup, ChatAction
from telegram.ext import Updater, CommandHandler, CallbackContext, run_async

from camera import Camera
from utils import restricted


class Bot:
    authorized_user = os.environ.get('AUTHORIZED_USER')

    def __init__(self):
        self.camera = Camera()
        self.camera.start()
        self.logger = logging.getLogger(__name__)

        token = os.environ.get('BOT_API_TOKEN')
        self.updater = Updater(token=token, use_context=True,
                               user_sig_handler=self.signal_handler)
        dispatcher = self.updater.dispatcher

        dispatcher.add_handler(CommandHandler('start', self.start))
        dispatcher.add_handler(CommandHandler('get_photo', self.get_photo))
        dispatcher.add_handler(CommandHandler('get_video', self.get_video))
        dispatcher.add_handler(CommandHandler('surveillance_start',
                                              self.surveillance_start))
        dispatcher.add_handler(CommandHandler('surveillance_stop',
                                              self.surveillance_stop))
        dispatcher.add_handler(CommandHandler('surveillance_status',
                                              self.surveillance_status))

    def start_bot(self):
        self.updater.start_polling()
        self.logger.info("Surveillance Telegram Bot started")
        self.updater.idle()

    def signal_handler(self, _, __):
        self.camera.stop()
        self.logger.info("Surveillance Telegram Bot stopped")

    @restricted(authorized_user)
    def start(self, update: Update, context: CallbackContext) -> None:
        self.logger.info('Received "start" command')
        custom_keyboard = [
            [
                '/get_photo',
                '/get_video'
            ],
            [
                '/surveillance_start',
                '/surveillance_stop',
                '/surveillance_status'
            ]
        ]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard,
                                           resize_keyboard=True)
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Test Surveillance Bot by Pablo Chinea",
                                 reply_markup=reply_markup)

    @restricted(authorized_user)
    def get_photo(self, update: Update, context: CallbackContext) -> None:
        self.logger.info('Received "get_photo" command')

        # Upload photo
        context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                     action=ChatAction.UPLOAD_PHOTO)
        context.bot.send_photo(chat_id=update.effective_chat.id,
                               photo=self.camera.get_photo())

    @restricted(authorized_user)
    def get_video(self, update: Update, context: CallbackContext) -> None:
        self.logger.info('Received "get_video" command')

        # Record video
        context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                     action=ChatAction.RECORD_VIDEO)
        video = self.camera.get_video()

        # Upload video
        context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                     action=ChatAction.UPLOAD_VIDEO)
        context.bot.send_video(chat_id=update.effective_chat.id,
                               video=video)

    @run_async
    @restricted(authorized_user)
    def surveillance_start(self,
                           update: Update,
                           context: CallbackContext) -> None:
        self.logger.info('Received "surveillance_start" command')

        # Check if surveillance is already started.
        if self.camera.is_surveillance_active:
            update.message.reply_text('Error! Surveillance is already started')
            self.logger.warning("Surveillance already started")
            return

        # Starts surveillance.
        update.message.reply_text("Surveillance started")
        for data in self.camera.surveillance_start():
            if 'detected' in data:
                update.message.reply_text('Motion detected!')
                context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                             action=ChatAction.RECORD_VIDEO)
            if 'photo' in data:
                context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                             action=ChatAction.UPLOAD_PHOTO)
                context.bot.send_photo(chat_id=update.effective_chat.id,
                                       photo=data['photo'],
                                       caption=f'Capture '
                                               f'{data["id"]}/{data["total"]}')
                context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                             action=ChatAction.RECORD_VIDEO)
            if 'video' in data:
                context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                             action=ChatAction.UPLOAD_VIDEO)
                context.bot.send_video(chat_id=update.effective_chat.id,
                                       video=data['video'])

        update.message.reply_text("Surveillance stopped")
        self.logger.info('Surveillance stop')

    @restricted(authorized_user)
    def surveillance_stop(self, update: Update, _: CallbackContext) -> None:
        self.logger.info('Received "surveillance_stop" command')

        # Checks if surveillance is not running.
        if not self.camera.is_surveillance_active:
            update.message.reply_text("Error! Surveillance is not started")
            self.logger.warning("Surveillance is not started")
            return

        # Stop surveillance.
        self.camera.surveillance_stop()

    @restricted(authorized_user)
    def surveillance_status(self, update: Update, _: CallbackContext) -> None:
        self.logger.info('Received "surveillance_status" command')
        if self.camera.is_surveillance_active:
            update.message.reply_text("Surveillance is active")
        else:
            update.message.reply_text("Surveillance is not active")
