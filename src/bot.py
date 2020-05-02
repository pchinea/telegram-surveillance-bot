import inspect
import logging
import os
from functools import wraps
from typing import Callable

from telegram import Update, ReplyKeyboardMarkup, ChatAction
from telegram.ext import Updater, CommandHandler, CallbackContext, run_async

from camera import Camera

HandlerType = Callable[[Update, CallbackContext], None]

# Logging config
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class Bot:
    def __init__(self):
        self.camera = Camera()
        self.camera.start()
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(os.environ.get('LOG_LEVEL', 'WARNING').upper())
        self.authorized_user = os.environ.get('AUTHORIZED_USER')

        token = os.environ.get('BOT_API_TOKEN')
        self.updater = Updater(token=token, use_context=True,
                               user_sig_handler=self.signal_handler)

        # Registers commands in the dispatcher
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if name.startswith('_command_'):
                self._register_command(method)

    def _register_command(self, func: HandlerType):
        logger = self.logger
        dispatcher = self.updater.dispatcher
        command = func.__name__.replace('_command_', '')

        @wraps(func)
        def command_func(update: Update, context: CallbackContext) -> None:

            # Checks if user is authorized
            if update.effective_chat.username != self.authorized_user:
                logger.warning('Unauthorized call to "%s" command by @%s',
                               command, update.effective_chat.username)
                update.message.reply_text("Unauthorized")
                return

            logger.debug('Received "%s" command', command)
            func(update, context)

        # Adds handler to the dispatcher
        dispatcher.add_handler(CommandHandler(command, command_func))

    def start_bot(self):
        self.updater.start_polling()
        self.logger.info("Surveillance Telegram Bot started")
        self.updater.idle()

    def signal_handler(self, _, __):
        self.camera.stop()
        self.logger.info("Surveillance Telegram Bot stopped")

    def _command_start(self, update: Update, context: CallbackContext) -> None:
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

    def _command_get_photo(self,
                           update: Update,
                           context: CallbackContext) -> None:
        # Upload photo
        context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                     action=ChatAction.UPLOAD_PHOTO)
        context.bot.send_photo(chat_id=update.effective_chat.id,
                               photo=self.camera.get_photo())

    def _command_get_video(self,
                           update: Update,
                           context: CallbackContext) -> None:
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
    def _command_surveillance_start(self,
                                    update: Update,
                                    context: CallbackContext) -> None:
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

    def _command_surveillance_stop(self,
                                   update: Update,
                                   _: CallbackContext) -> None:
        # Checks if surveillance is not running.
        if not self.camera.is_surveillance_active:
            update.message.reply_text("Error! Surveillance is not started")
            self.logger.warning("Surveillance is not started")
            return

        # Stop surveillance.
        self.camera.surveillance_stop()

    def _command_surveillance_status(self,
                                     update: Update,
                                     _: CallbackContext) -> None:
        if self.camera.is_surveillance_active:
            update.message.reply_text("Surveillance is active")
        else:
            update.message.reply_text("Surveillance is not active")
