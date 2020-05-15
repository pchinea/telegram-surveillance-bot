"""
Module for bot related functionality.

This module implements the `Bot` class that manage the communication between
the user (through a telegram chat) and the camera.
"""
import inspect
import logging
from functools import wraps
from typing import Callable, Union, Optional, Any

from telegram import Update, ReplyKeyboardMarkup, ChatAction, ParseMode, \
    InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, run_async, \
    ConversationHandler, CallbackQueryHandler, Filters, MessageHandler

from camera import Camera

HandlerType = Callable[[Update, CallbackContext], Any]


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

        dispatcher = self.updater.dispatcher

        # Registers commands in the dispatcher
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if name.startswith('_command_'):
                command = name.replace('_command_', '')
                dispatcher.add_handler(self.command_handler(command, method))

        # Register configuration menu
        dispatcher.add_handler(BotConfig.get_config(self))

    def command_handler(
            self,
            command: str,
            callback: HandlerType
    ) -> CommandHandler:
        """
        Decorates callback and returns a CommandHandler.

        This decorator restricts command use to the authorized user, loads
        defaults configuration options and adds debug logging.

        Args:
            command: The command this handler should listen for.
            callback: The callback function for this handler.

        Returns:
            Handler instance to handle Telegram commands.
        """
        logger = self.logger

        @wraps(callback)
        def wrapped(update: Update, context: CallbackContext) -> Any:

            # Checks if user is authorized
            if update.effective_chat.username != self.authorized_user:
                logger.warning(
                    'Unauthorized call to "%s" command by @%s',
                    command,
                    update.effective_chat.username
                )
                update.message.reply_text("Unauthorized")
                return None

            BotConfig.ensure_defaults(context)
            logger.debug('Received "%s" command', command)
            return callback(update, context)

        return CommandHandler(command, wrapped)

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
    # Configuration variables
    TIMESTAMP = 'timestamp'
    OD_VIDEO_DURATION = 'od_video_duration'
    SRV_VIDEO_DURATION = 'srv_video_duration'
    SRV_PICTURE_INTERVAL = 'srv_picture_interval'
    SRV_MOTION_CONTOURS = 'srv_motion_contours'

    # State definitions for top level conversation
    MAIN_MENU, GENERAL_CONFIG, SURVEILLANCE_CONFIG = map(chr, range(3))

    # State definitions for second level conversation
    (
        CHANGE_TIMESTAMP,
        CHANGE_OD_VIDEO_DURATION,
        CHANGE_SRV_VIDEO_DURATION,
        CHANGE_SRV_PICTURE_INTERVAL,
        CHANGE_SRV_MOTION_CONTOURS
    ) = map(chr, range(3, 8))

    # State definitions for input conversation
    BOOLEAN_INPUT, INTEGER_INPUT = map(chr, range(8, 10))

    # Shortcut for ConversationHandler.END
    END = ConversationHandler.END

    # Auxiliary constants
    CURRENT_VARIABLE, RETURN_HANDLER, ENABLE, DISABLE = map(chr, range(10, 14))

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
                text='Timestamp',
                callback_data=str(BotConfig.CHANGE_TIMESTAMP)
            )],
            [InlineKeyboardButton(
                text='On Demand video duration',
                callback_data=str(BotConfig.CHANGE_OD_VIDEO_DURATION)
            )],
            [InlineKeyboardButton(
                text='Back',
                callback_data=str(BotConfig.END)
            )]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        if update.message:
            update.message.reply_text(text=text, reply_markup=keyboard)
        else:
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
                callback_data=str(BotConfig.CHANGE_SRV_VIDEO_DURATION)
            )],
            [InlineKeyboardButton(
                text='Picture Interval',
                callback_data=str(BotConfig.CHANGE_SRV_PICTURE_INTERVAL)
            )],
            [InlineKeyboardButton(
                text='Draw motion contours',
                callback_data=str(BotConfig.CHANGE_SRV_MOTION_CONTOURS)
            )],
            [InlineKeyboardButton(
                text='Back',
                callback_data=str(BotConfig.END)
            )]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        if update.message:
            update.message.reply_text(text=text, reply_markup=keyboard)
        else:
            update.callback_query.answer()
            update.callback_query.edit_message_text(
                text=text,
                reply_markup=keyboard
            )

        return BotConfig.SURVEILLANCE_CONFIG

    # General configuration options.

    @staticmethod
    def change_timestamp(
            update: Update,
            context: CallbackContext
    ) -> chr:
        timestamp = context.bot_data[BotConfig.TIMESTAMP]

        current_status = 'Enabled' if timestamp else 'Disabled'
        text = f'Change time stamping\n' \
               f'Current value: *{current_status}*'

        return BotConfig.boolean_question(
            update,
            context,
            text,
            BotConfig.TIMESTAMP,
            BotConfig.general_config
        )

    @staticmethod
    def change_od_video_duration(
            update: Update,
            context: CallbackContext
    ) -> chr:
        od_video_duration = context.bot_data[BotConfig.OD_VIDEO_DURATION]

        text = f'Change On Demand video duration\n' \
               f'Current value: *{od_video_duration}*'

        return BotConfig.integer_question(
            update,
            context,
            text,
            BotConfig.OD_VIDEO_DURATION,
            BotConfig.general_config
        )

    # Surveillance mode configuration options.

    @staticmethod
    def change_srv_video_duration(
            update: Update,
            context: CallbackContext
    ) -> chr:
        srv_video_duration = context.bot_data[BotConfig.SRV_VIDEO_DURATION]

        text = f'Change Surveillance video duration\n' \
               f'Current value: *{srv_video_duration}*'

        return BotConfig.integer_question(
            update,
            context,
            text,
            BotConfig.SRV_VIDEO_DURATION,
            BotConfig.surveillance_config
        )

    @staticmethod
    def change_srv_picture_interval(
            update: Update,
            context: CallbackContext
    ) -> chr:
        srv_picture_interval = context.bot_data[BotConfig.SRV_PICTURE_INTERVAL]

        text = f'Change Surveillance picture interval\n' \
               f'Current value: *{srv_picture_interval}*'

        return BotConfig.integer_question(
            update,
            context,
            text,
            BotConfig.SRV_PICTURE_INTERVAL,
            BotConfig.surveillance_config
        )

    @staticmethod
    def change_motion_contours(
            update: Update,
            context: CallbackContext
    ) -> chr:
        motion_contours = context.bot_data[BotConfig.SRV_MOTION_CONTOURS]

        current_status = 'Enabled' if motion_contours else 'Disabled'
        text = f'Change motion contours\n' \
               f'Current value: *{current_status}*'

        return BotConfig.boolean_question(
            update,
            context,
            text,
            BotConfig.SRV_MOTION_CONTOURS,
            BotConfig.surveillance_config
        )

    # Questions helpers.

    @staticmethod
    def boolean_question(
            update: Update,
            context: CallbackContext,
            text: str,
            current_variable: chr,
            return_handler: chr
    ) -> chr:
        context.user_data[BotConfig.CURRENT_VARIABLE] = current_variable
        context.user_data[BotConfig.RETURN_HANDLER] = return_handler

        buttons = [[
            InlineKeyboardButton(
                text='Enable',
                callback_data=str(BotConfig.ENABLE)
            ),
            InlineKeyboardButton(
                text='Disable',
                callback_data=str(BotConfig.DISABLE)
            ),
        ]]
        keyboard = InlineKeyboardMarkup(buttons)

        update.callback_query.answer()
        update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2
        )

        return BotConfig.BOOLEAN_INPUT

    @staticmethod
    def integer_question(
            update: Update,
            context: CallbackContext,
            text: str,
            current_variable: chr,
            return_handler: chr
    ) -> chr:
        context.user_data[BotConfig.CURRENT_VARIABLE] = current_variable
        context.user_data[BotConfig.RETURN_HANDLER] = return_handler

        update.callback_query.answer()
        update.callback_query.edit_message_text(
            text=text,
            parse_mode=ParseMode.MARKDOWN_V2
        )

        return BotConfig.INTEGER_INPUT

    # Input handlers.

    @staticmethod
    def boolean_input(update: Update, context: CallbackContext) -> chr:
        context.bot_data[
            context.user_data[BotConfig.CURRENT_VARIABLE]
        ] = update.callback_query.data == BotConfig.ENABLE

        return context.user_data[BotConfig.RETURN_HANDLER](update, context)

    @staticmethod
    def integer_input(update: Update, context: CallbackContext) -> chr:
        try:
            value = int(update.message.text)
            assert value > 0
            assert value < 100
        except (ValueError, AssertionError):
            update.message.reply_text(
                'Invalid value, insert an integer number between 1 and 99'
            )
            return BotConfig.INTEGER_INPUT

        context.bot_data[
            context.user_data[BotConfig.CURRENT_VARIABLE]
        ] = value

        return context.user_data[BotConfig.RETURN_HANDLER](update, context)

    @staticmethod
    def end(update: Update, _: CallbackContext) -> int:
        if update.callback_query:
            update.callback_query.answer()
            update.callback_query.edit_message_text(text='Configuration done')
        else:
            update.message.reply_text('Configuration canceled')

        return BotConfig.END

    @staticmethod
    def get_config(bot: Bot) -> ConversationHandler:
        main_handler = ConversationHandler(
            entry_points=[bot.command_handler('config', BotConfig.start)],
            states={
                BotConfig.MAIN_MENU: [
                    CallbackQueryHandler(
                        BotConfig.general_config,
                        pattern='^' + str(BotConfig.GENERAL_CONFIG) + '$'
                    ),
                    CallbackQueryHandler(
                        BotConfig.surveillance_config,
                        pattern='^' + str(BotConfig.SURVEILLANCE_CONFIG) + '$'
                    ),
                    CallbackQueryHandler(
                        BotConfig.end,
                        pattern='^' + str(BotConfig.END) + '$'
                    )
                ],
                BotConfig.GENERAL_CONFIG: [
                    CallbackQueryHandler(
                        BotConfig.change_timestamp,
                        pattern='^'
                        + str(BotConfig.CHANGE_TIMESTAMP)
                        + '$'
                    ),
                    CallbackQueryHandler(
                        BotConfig.change_od_video_duration,
                        pattern='^'
                        + str(BotConfig.CHANGE_OD_VIDEO_DURATION)
                        + '$'
                    ),
                    CallbackQueryHandler(
                        BotConfig.start,
                        pattern='^' + str(BotConfig.END) + '$'
                    )
                ],
                BotConfig.SURVEILLANCE_CONFIG: [
                    CallbackQueryHandler(
                        BotConfig.change_srv_video_duration,
                        pattern='^'
                        + str(BotConfig.CHANGE_SRV_VIDEO_DURATION)
                        + '$'
                    ),
                    CallbackQueryHandler(
                        BotConfig.change_srv_picture_interval,
                        pattern='^'
                        + str(BotConfig.CHANGE_SRV_PICTURE_INTERVAL)
                        + '$'
                    ),
                    CallbackQueryHandler(
                        BotConfig.change_motion_contours,
                        pattern='^'
                        + str(BotConfig.CHANGE_SRV_MOTION_CONTOURS)
                        + '$'
                    ),
                    CallbackQueryHandler(
                        BotConfig.start,
                        pattern='^' + str(BotConfig.END) + '$'
                    )
                ],
                BotConfig.BOOLEAN_INPUT: [
                    CallbackQueryHandler(
                        BotConfig.boolean_input,
                        pattern='^'
                        + str(BotConfig.ENABLE)
                        + '$|^'
                        + str(BotConfig.DISABLE)
                        + '$'
                    )
                ],
                BotConfig.INTEGER_INPUT: [
                    MessageHandler(
                        Filters.text,
                        BotConfig.integer_input
                    )
                ]
            },
            fallbacks=[bot.command_handler('stop_config', BotConfig.end)],
        )

        return main_handler

    @staticmethod
    def ensure_defaults(context: CallbackContext) -> None:
        if BotConfig.TIMESTAMP not in context.bot_data:
            context.bot_data[BotConfig.TIMESTAMP] = True

        if BotConfig.OD_VIDEO_DURATION not in context.bot_data:
            context.bot_data[BotConfig.OD_VIDEO_DURATION] = 5

        if BotConfig.SRV_VIDEO_DURATION not in context.bot_data:
            context.bot_data[BotConfig.SRV_VIDEO_DURATION] = 30

        if BotConfig.SRV_PICTURE_INTERVAL not in context.bot_data:
            context.bot_data[BotConfig.SRV_PICTURE_INTERVAL] = 5

        if BotConfig.SRV_MOTION_CONTOURS not in context.bot_data:
            context.bot_data[BotConfig.SRV_MOTION_CONTOURS] = True
