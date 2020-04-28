import logging
import os

from telegram import Update, ReplyKeyboardMarkup, ChatAction
from telegram.ext import Updater, CommandHandler, CallbackContext, run_async

from capture import Camera
from utils import restricted


class Bot:
    authorized_user = os.environ.get('AUTHORIZED_USER')

    @restricted(authorized_user)
    def start(self, update: Update, context: CallbackContext) -> None:
        self.logger.info('Received "start" command')
        custom_keyboard = [
            ['/get_photo', '/get_video'],
            ['/surveillance_start', '/surveillance_stop']
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
                               photo=self.cam.get_photo())

    @restricted(authorized_user)
    def get_video(self, update: Update, context: CallbackContext) -> None:
        self.logger.info('Received "get_video" command')

        # Record video
        context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                     action=ChatAction.RECORD_VIDEO)
        video = self.cam.get_video()

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
        for data in self.cam.surveillance_start():
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
        self.logger.info('Surveillance stop')

    @restricted(authorized_user)
    def surveillance_stop(self,
                          update: Update,
                          context: CallbackContext) -> None:
        self.logger.info('Received "surveillance_stop" command')
        self.cam.surveillance_stop()

    def __init__(self, cam: Camera):
        self.cam = cam
        self.logger = logging.getLogger(__name__)

        token = os.environ.get('BOT_API_TOKEN')
        self.updater = Updater(token=token, use_context=True)
        dispatcher = self.updater.dispatcher

        dispatcher.add_handler(CommandHandler('start', self.start))
        dispatcher.add_handler(CommandHandler('get_photo', self.get_photo))
        dispatcher.add_handler(CommandHandler('get_video', self.get_video))
        dispatcher.add_handler(CommandHandler('surveillance_start',
                                              self.surveillance_start))
        dispatcher.add_handler(CommandHandler('surveillance_stop',
                                              self.surveillance_stop))

    def get_updater(self):
        return self.updater
