"""
Module for bot related functionality.

This module implements the `Bot` class that manage the communication between
the user (through a telegram chat) and the camera.
"""
import inspect
import logging
from functools import wraps
from typing import Callable, Union, Optional

from telegram import Update, ReplyKeyboardMarkup, ChatAction, ParseMode, \
    InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, run_async, \
    ConversationHandler, CallbackQueryHandler

from camera import Camera

HandlerType = Callable[[Update, CallbackContext], None]


class Bot:
    """
    Class for the telegram bot implementation.

    This class exposes a number of commands to the user in order to control
    the camera processes and receive picture and video files.

    Args:
        token: Access Token for the telegram bot.
        username: Username of the only user authorized to interact with the
            bot (without @).
        log_level: Logging level for logging module.
    """
    def __init__(
            self,
            token: str,
            username: str,
            log_level: Union[int, str, None] = None
    ):
        self.camera = Camera()
        self.logger = logging.getLogger(__name__)
        if log_level:
            self.logger.setLevel(log_level)
        self.authorized_user = username

        self.updater = Updater(token=token, use_context=True)

        # Registers commands in the dispatcher
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if name.startswith('_command_'):
                self._register_command(method)

        self.updater.dispatcher.add_handler(BotConfig.get_config())

    def _register_command(self, func: HandlerType):
        """
        Register a function as a command handler in the dispatcher.

        This method also decorates the function to restrict its use to the
        authorized user.

        Args:
            func: Function to be registered in the dispatcher.
        """
        logger = self.logger
        dispatcher = self.updater.dispatcher
        command = func.__name__.replace('_command_', '')

        @wraps(func)
        def command_func(update: Update, context: CallbackContext) -> None:

            # Checks if user is authorized
            if update.effective_chat.username != self.authorized_user:
                logger.warning(
                    'Unauthorized call to "%s" command by @%s',
                    command,
                    update.effective_chat.username
                )
                update.message.reply_text("Unauthorized")
                return

            BotConfig.ensure_defaults(context)
            logger.debug('Received "%s" command', command)
            func(update, context)

        # Adds handler to the dispatcher
        dispatcher.add_handler(CommandHandler(command, command_func))

    def start(self):
        """
        Starts the bot execution and waits to clean up before exit.

        After starting the camera and the bot polling it waits into a loop
        until the bot is interrupted by a signal. After that the camera
        device is released and the function ends.
        """
        self.camera.start()
        self.updater.start_polling()
        self.logger.info("Surveillance Telegram Bot started")

        self.updater.idle()

        self.camera.stop()
        self.logger.info("Surveillance Telegram Bot stopped")

    def _command_start(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for `/start` command.

        It sends a presentation to the user and calls the help command.

        Args:
            update: The update to be handled.
            context: The context object for the update.
        """
        update.message.reply_text(
            text="Welcome to the *Surveillance Telegram Bot*",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        self._command_help(update, context)

    def _get_reply_keyboard(
            self,
            is_active: Optional[bool] = None
    ) -> ReplyKeyboardMarkup:
        """
        Generates Reply Keyboard content.

        Args:
            is_active: Overrides surveillance mode status.

        Returns:
            ReplyKeyboardMarkup instance with the menu content.

        """
        active = self.camera.is_surveillance_active \
            if is_active is None else is_active
        custom_keyboard = [
            [
                '/get_photo',
                '/get_video'
            ],
            [
                '/surveillance_{}'.format('stop' if active else 'start')
            ]
        ]
        return ReplyKeyboardMarkup(
            custom_keyboard,
            resize_keyboard=True
        )

    def _command_help(
            self,
            update: Update,
            _: CallbackContext
    ) -> None:
        update.message.reply_text(
            text="With this bot you can request that a photo or video be "
                 "taken with the cam|. It also has a surveillance mode that "
                 "will warn when it detects movement and will start "
                 "recording a video, and during the recording, photos will "
                 "be taken and sent periodically|.\n"
                 "\n"
                 "These are the available commands:\n"
                 "\n"
                 "*On Demand commands*\n"
                 "/get|_photo |- Grabs a picture from the cam\n"
                 "/get|_video |- Grabs a video from the cam\n"
                 "\n"
                 "*Surveillance Mode commands*\n"
                 "/surveillance|_start |- Starts surveillance mode\n"
                 "/surveillance|_stop |- Starts surveillance mode\n"
                 "/surveillance|_status |- Indicates if surveillance mode "
                 "is active or not\n"
                 "\n"
                 "*General commands*\n"
                 "/config |- Invokes configuration menu\n"
                 "/help |- Shows this help text\n"
                 "".replace('|', '\\'),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=self._get_reply_keyboard()
        )

    def _command_get_photo(
            self,
            update: Update,
            context: CallbackContext
    ) -> None:
        """
        Handler for `/get_photo` command.

        It takes a single shot and sends it to the user.

        Args:
            update: The update to be handled.
            context: The context object for the update.
        """
        # Upload photo
        context.bot.send_chat_action(
            chat_id=update.message.chat_id,
            action=ChatAction.UPLOAD_PHOTO
        )
        context.bot.send_photo(
            chat_id=update.message.chat_id,
            photo=self.camera.get_photo()
        )

    def _command_get_video(
            self,
            update: Update,
            context: CallbackContext
    ) -> None:
        """
        Handler for `/get_video` command.

        It takes a video and sends it to the user.

        Args:
            update: The update to be handled.
            context: The context object for the update.
        """
        # Record video
        context.bot.send_chat_action(
            chat_id=update.message.chat_id,
            action=ChatAction.RECORD_VIDEO
        )
        video = self.camera.get_video()

        # Upload video
        context.bot.send_chat_action(
            chat_id=update.message.chat_id,
            action=ChatAction.UPLOAD_VIDEO
        )
        context.bot.send_video(
            chat_id=update.message.chat_id,
            video=video
        )

    @run_async
    def _command_surveillance_start(
            self,
            update: Update,
            context: CallbackContext
    ) -> None:
        """
        Handler for `/surveillance_start` command.

        It starts the surveillance mode. In this mode the is waiting for
        motion detection, when this happens it sends a message to the user
        and start to record a video, sending pictures in regular intervals
        during the video recording. After that it goes back to the waiting
        state.

        Args:
            update: The update to be handled.
            context: The context object for the update.
        """
        # Check if surveillance is already started.
        if self.camera.is_surveillance_active:
            update.message.reply_text('Error! Surveillance is already started')
            self.logger.warning("Surveillance already started")
            return

        # Starts surveillance.
        self.logger.info('Surveillance mode start')
        update.message.reply_text(
            "Surveillance mode started",
            reply_markup=self._get_reply_keyboard(True)
        )
        for data in self.camera.surveillance_start():
            if 'detected' in data:
                update.message.reply_text(
                    '*MOTION DETECTED|!*'.replace('|', '\\'),
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                context.bot.send_chat_action(
                    chat_id=update.message.chat_id,
                    action=ChatAction.RECORD_VIDEO
                )
            if 'photo' in data:
                context.bot.send_chat_action(
                    chat_id=update.message.chat_id,
                    action=ChatAction.UPLOAD_PHOTO
                )
                context.bot.send_photo(
                    chat_id=update.message.chat_id,
                    photo=data['photo'],
                    caption=f'Capture {data["id"]}/{data["total"]}'
                )
                context.bot.send_chat_action(
                    chat_id=update.message.chat_id,
                    action=ChatAction.RECORD_VIDEO
                )
            if 'video' in data:
                context.bot.send_chat_action(
                    chat_id=update.message.chat_id,
                    action=ChatAction.UPLOAD_VIDEO
                )
                context.bot.send_video(
                    chat_id=update.message.chat_id,
                    video=data['video']
                )

        update.message.reply_text(
            "Surveillance mode stopped",
            reply_markup=self._get_reply_keyboard()
        )
        self.logger.info('Surveillance mode stop')

    def _command_surveillance_stop(
            self,
            update: Update,
            _: CallbackContext
    ) -> None:
        """
        Handler for `/surveillance_stop` command.

        This method stops the surveillance mode.

        Args:
            update: The update to be handled.
        """
        # Checks if surveillance is not running.
        if not self.camera.is_surveillance_active:
            update.message.reply_text("Error! Surveillance is not started")
            self.logger.warning("Surveillance is not started")
            return

        # Stop surveillance.
        self.camera.surveillance_stop()

    def _command_surveillance_status(
            self,
            update: Update,
            _: CallbackContext
    ) -> None:
        """
        Handler for `/surveillance_stats` command.

        This method informs to the user whether surveillance mode is active
        or not.

        Args:
            update: The update to be handled.
        """
        if self.camera.is_surveillance_active:
            update.message.reply_text("Surveillance mode is active")
        else:
            update.message.reply_text("Surveillance mode is not active")


class BotConfig:
    MAIN_MENU, GENERAL_CONFIG, SURVEILLANCE_CONFIG = map(chr, range(3))

    (
        PRINT_TIMESTAMP,
        OD_VIDEO_DURATION,
        SRV_VIDEO_DURATION,
        SRV_PICTURE_INTERVAL,
        SRV_DRAW_CONTOURS
    ) = map(chr, range(3, 8))

    END = ConversationHandler.END

    @staticmethod
    def start(update: Update, _: CallbackContext) -> chr:
        text = 'This is the main menu'
        buttons = [
            [InlineKeyboardButton(
                text='General configuration',
                callback_data=str(BotConfig.GENERAL_CONFIG)
            )],
            [InlineKeyboardButton(
                text='Surveillance mode configuration',
                callback_data=str(BotConfig.SURVEILLANCE_CONFIG)
            )],
            [InlineKeyboardButton(
                text='Done',
                callback_data=str(BotConfig.END)
            )]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        if update.message:
            update.message.reply_text(text=text, reply_markup=keyboard)
        else:
            update.callback_query.edit_message_text(
                text=text,
                reply_markup=keyboard
            )

        return BotConfig.MAIN_MENU

    @staticmethod
    def general_config(update: Update, _: CallbackContext) -> chr:
        text = 'General configuration'
        buttons = [
            [InlineKeyboardButton(
                text='Print timestamp',
                callback_data=str(BotConfig.PRINT_TIMESTAMP)
            )],
            [InlineKeyboardButton(
                text='On Demand video duration',
                callback_data=str(BotConfig.OD_VIDEO_DURATION)
            )],
            [InlineKeyboardButton(
                text='Back',
                callback_data=str(BotConfig.END)
            )]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        update.callback_query.answer()
        update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )

        return BotConfig.GENERAL_CONFIG

    @staticmethod
    def surveillance_config(update: Update, _: CallbackContext) -> chr:
        text = 'Surveillance Mode configuration'
        buttons = [
            [InlineKeyboardButton(
                text='Video duration',
                callback_data=str(BotConfig.SRV_VIDEO_DURATION)
            )],
            [InlineKeyboardButton(
                text='Picture Interval',
                callback_data=str(BotConfig.SRV_PICTURE_INTERVAL)
            )],
            [InlineKeyboardButton(
                text='Draw motion contours',
                callback_data=str(BotConfig.SRV_DRAW_CONTOURS)
            )],
            [InlineKeyboardButton(
                text='Back',
                callback_data=str(BotConfig.END)
            )]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        update.callback_query.answer()
        update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )

        return BotConfig.SURVEILLANCE_CONFIG

    @staticmethod
    def end(update: Update, _: CallbackContext) -> int:
        if update.callback_query:
            update.callback_query.answer()
            update.callback_query.edit_message_text(text='Configuration done')
        else:
            update.message.reply_text('Configuration canceled')

        return BotConfig.END

    @staticmethod
    def get_config() -> ConversationHandler:
        main_handler = ConversationHandler(
            entry_points=[CommandHandler('config', BotConfig.start)],
            states={
                BotConfig.MAIN_MENU: [
                    CallbackQueryHandler(
                        BotConfig.end,
                        pattern='^' + str(BotConfig.END) + '$'
                    ),
                    CallbackQueryHandler(
                        BotConfig.general_config,
                        pattern='^' + str(BotConfig.GENERAL_CONFIG) + '$'
                    ),
                    CallbackQueryHandler(
                        BotConfig.surveillance_config,
                        pattern='^' + str(BotConfig.SURVEILLANCE_CONFIG) + '$'
                    )
                ],
                BotConfig.GENERAL_CONFIG: [
                    CallbackQueryHandler(
                        BotConfig.start,
                        pattern='^' + str(BotConfig.END) + '$'
                    )
                ],
                BotConfig.SURVEILLANCE_CONFIG: [
                    CallbackQueryHandler(
                        BotConfig.start,
                        pattern='^' + str(BotConfig.END) + '$'
                    )
                ]
            },
            fallbacks=[CommandHandler('stop_config', BotConfig.end)],
        )

        return main_handler

    @staticmethod
    def ensure_defaults(context: CallbackContext) -> None:
        context.bot_data['print_timestamp'] = context.bot_data.get(
            'print_timestamp', True
        )
        context.bot_data['od_video_duration'] = context.bot_data.get(
            'od_video_duration', 5
        )
        context.bot_data['srv_video_duration'] = context.bot_data.get(
            'srv_video_duration', 30
        )
        context.bot_data['srv_picture_interval'] = context.bot_data.get(
            'srv_picture_interval', 5
        )
        context.bot_data['srv_draw_contours'] = context.bot_data.get(
            'srv_draw_contours', True
        )
