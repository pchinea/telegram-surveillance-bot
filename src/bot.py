"""
Module for bot related functionality.

This module implements the `Bot` class that manage the communication between
the user (through a telegram chat) and the camera. Also contains the
`BotConfig` class that implements a conversational sequence in order to
configure the bot behavior.
"""
import inspect
import logging
from functools import wraps
from typing import Callable, Union, Optional, Any, List

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

        # Registers configuration menu
        dispatcher.add_handler(BotConfig.get_config_handler(self))

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
        """
        Shows a help message listing all available commands.

        This command also sends the custom keyboard to the user.

        Args:
            update: The update to be handled.
        """
        update.message.reply_text(
            text="With this bot, photos or videos can be taken with the cam "
                 "upon request|. A surveillance mode is also included|. This "
                 "mode warns you when it detects movement and it will start "
                 "recording a video|. Whilst recording, photos will be taken "
                 "and sent periodically|.\n"
                 "\n"
                 "These are the available commands:\n"
                 "\n"
                 "*On Demand commands*\n"
                 "/get|_photo |- Grabs a picture from the cam\n"
                 "/get|_video |- Grabs a video from the cam\n"
                 "\n"
                 "*Surveillance Mode commands*\n"
                 "/surveillance|_start |- Starts surveillance mode\n"
                 "/surveillance|_stop |- Stops surveillance mode\n"
                 "/surveillance|_status |- Indicates if surveillance mode "
                 "is active or not\n"
                 "\n"
                 "*General commands*\n"
                 "/config |- Invokes configuration menu\n"
                 "/stop|_config |- Abort configuration sequence\n"
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
        # Retrieves configuration
        timestamp = context.bot_data[BotConfig.TIMESTAMP]

        # Uploads photo
        context.bot.send_chat_action(
            chat_id=update.message.chat_id,
            action=ChatAction.UPLOAD_PHOTO
        )
        context.bot.send_photo(
            chat_id=update.message.chat_id,
            photo=self.camera.get_photo(timestamp=timestamp)
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
        # Retrieves configuration
        timestamp = context.bot_data[BotConfig.TIMESTAMP]
        seconds = context.bot_data[BotConfig.OD_VIDEO_DURATION]

        # Sends waiting message
        message = update.message.reply_text(
            f'Recording a {seconds} seconds video...'
        )

        # Records video
        context.bot.send_chat_action(
            chat_id=update.message.chat_id,
            action=ChatAction.RECORD_VIDEO
        )
        video = self.camera.get_video(timestamp=timestamp, seconds=seconds)

        # Uploads video
        context.bot.send_chat_action(
            chat_id=update.message.chat_id,
            action=ChatAction.UPLOAD_VIDEO
        )
        context.bot.send_video(
            chat_id=update.message.chat_id,
            video=video
        )

        # Deletes waiting message
        context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=message.message_id
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
        # Check if surveillance is already started
        if self.camera.is_surveillance_active:
            update.message.reply_text('Error! Surveillance is already started')
            self.logger.warning("Surveillance already started")
            return

        # Retrieve configuration
        timestamp = context.bot_data[BotConfig.TIMESTAMP]
        video_seconds = context.bot_data[BotConfig.SRV_VIDEO_DURATION]
        picture_interval = context.bot_data[BotConfig.SRV_PICTURE_INTERVAL]
        motion_contours = context.bot_data[BotConfig.SRV_MOTION_CONTOURS]

        # Starts surveillance
        waiting_message = None
        self.logger.info('Surveillance mode start')
        update.message.reply_text(
            "Surveillance mode started",
            reply_markup=self._get_reply_keyboard(True)
        )
        for data in self.camera.surveillance_start(
                timestamp=timestamp,
                video_seconds=video_seconds,
                picture_seconds=picture_interval,
                contours=motion_contours
        ):
            if 'detected' in data:
                update.message.reply_text(
                    '*MOTION DETECTED|!*'.replace('|', '\\'),
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                waiting_message = update.message.reply_text(
                    f'Recording a {video_seconds} seconds video and taking '
                    f'{video_seconds // picture_interval} photos...'
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
                if waiting_message:
                    context.bot.delete_message(
                        chat_id=update.message.chat_id,
                        message_id=waiting_message.message_id
                    )
                    waiting_message = None

        if waiting_message:
            context.bot.delete_message(
                chat_id=update.message.chat_id,
                message_id=waiting_message.message_id
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
    """
    Class for bot configuration process implementation.

    This class contains all constants and static methods needed to implements
    a conversational sequence with the user in order to the bot behavior will
    be configured.

    It doesn't have any instance method so it doesn't need to be instantiated.
    """
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
    def get_config_handler(bot: Bot) -> ConversationHandler:
        """
        Generates the conversation handler for whole configuration process.

        Args:
            bot: The parent `Bot` instance.

        Returns:
            The instantiated `ConversationHandler`.
        """
        main_handler = ConversationHandler(
            entry_points=[bot.command_handler('config', BotConfig._main_menu)],
            states={
                BotConfig.MAIN_MENU: [
                    CallbackQueryHandler(
                        BotConfig._general_config,
                        pattern='^' + str(BotConfig.GENERAL_CONFIG) + '$'
                    ),
                    CallbackQueryHandler(
                        BotConfig._surveillance_config,
                        pattern='^' + str(BotConfig.SURVEILLANCE_CONFIG) + '$'
                    ),
                    CallbackQueryHandler(
                        BotConfig._end,
                        pattern='^' + str(BotConfig.END) + '$'
                    )
                ],
                BotConfig.GENERAL_CONFIG: [
                    CallbackQueryHandler(
                        BotConfig._change_timestamp,
                        pattern='^'
                        + str(BotConfig.CHANGE_TIMESTAMP)
                        + '$'
                    ),
                    CallbackQueryHandler(
                        BotConfig._change_od_video_duration,
                        pattern='^'
                        + str(BotConfig.CHANGE_OD_VIDEO_DURATION)
                        + '$'
                    ),
                    CallbackQueryHandler(
                        BotConfig._main_menu,
                        pattern='^' + str(BotConfig.END) + '$'
                    )
                ],
                BotConfig.SURVEILLANCE_CONFIG: [
                    CallbackQueryHandler(
                        BotConfig._change_srv_video_duration,
                        pattern='^'
                        + str(BotConfig.CHANGE_SRV_VIDEO_DURATION)
                        + '$'
                    ),
                    CallbackQueryHandler(
                        BotConfig._change_srv_picture_interval,
                        pattern='^'
                        + str(BotConfig.CHANGE_SRV_PICTURE_INTERVAL)
                        + '$'
                    ),
                    CallbackQueryHandler(
                        BotConfig._change_motion_contours,
                        pattern='^'
                        + str(BotConfig.CHANGE_SRV_MOTION_CONTOURS)
                        + '$'
                    ),
                    CallbackQueryHandler(
                        BotConfig._main_menu,
                        pattern='^' + str(BotConfig.END) + '$'
                    )
                ],
                BotConfig.BOOLEAN_INPUT: [
                    CallbackQueryHandler(
                        BotConfig._boolean_input,
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
                        BotConfig._integer_input
                    )
                ]
            },
            fallbacks=[bot.command_handler('stop_config', BotConfig._end)],
        )

        return main_handler

    @staticmethod
    def ensure_defaults(context: CallbackContext) -> None:
        """
        Creates non-existent variables and populates with default values.

        Args:
            context: The context object for the update.
        """
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

    # Menus

    @staticmethod
    def _main_menu(update: Update, _: CallbackContext) -> chr:
        """
        Creates the main menu and send it to the user.

        This menu links to the general configuration and to the surveillance
        mode configuration.

        Args:
            update: The update to be handled.

        Returns:
            The state MAIN_MENU.
        """
        text = "*Surveillance Telegram Bot Configuration*\n" \
               "\n" \
               "You can change here some parameters for the bot behavior|. " \
               "If surveillance mode is running any changes here will not " \
               "take effect on it until it is restarted|.\n" \
               "\n" \
               "To abort type /stop|_config|.\n" \
               "\n" \
               "Select section:".replace('|', '\\')
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

        BotConfig._render_menu(update, text, buttons)

        return BotConfig.MAIN_MENU

    @staticmethod
    def _general_config(update: Update, context: CallbackContext) -> chr:
        """
        Creates the menu for general configuration and send it to the user.

        Args:
            update: The update to be handled.
            context: The context object for the update.

        Returns:
            The state GENERAL_CONFIG.
        """
        timestamp = context.bot_data[BotConfig.TIMESTAMP]
        video_duration = context.bot_data[BotConfig.OD_VIDEO_DURATION]

        timestamp_str = 'Enabled' if timestamp else 'Disabled'

        text = f"*General configuration*\n" \
               f"\n" \
               f"__Timestamp__:\n" \
               f" |- _Description_: Print a timestamp on every photo or" \
               f" video taken|.\n" \
               f" |- _Current value_: *{timestamp_str}*\n" \
               f"\n" \
               f"__On Demand video duration__:\n" \
               f" |- _Description_: Duration of the video taken with " \
               f"/get|_video command|.\n" \
               f" |- _Current value_: *{video_duration} seconds*" \
               f"".replace('|', '\\')
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

        BotConfig._render_menu(update, text, buttons)

        return BotConfig.GENERAL_CONFIG

    @staticmethod
    def _surveillance_config(update: Update, context: CallbackContext) -> chr:
        """
        Creates the menu for the surveillance mode configuration and send it
        to the user.

        Args:
            update: The update to be handled.
            context: The context object for the update.

        Returns:
            The state SURVEILLANCE_CONFIG.
        """
        video_duration = context.bot_data[BotConfig.SRV_VIDEO_DURATION]
        picture_interval = context.bot_data[BotConfig.SRV_PICTURE_INTERVAL]
        motion_contours = context.bot_data[BotConfig.SRV_MOTION_CONTOURS]

        motion_contours_str = 'Enabled' if motion_contours else 'Disabled'

        text = f"*Surveillance Mode configuration*\n" \
               f"\n" \
               f"__Video duration__:\n" \
               f" |- _Description_: Duration of the video taken when motion " \
               f"is detected|.\n" \
               f" |- _Current value_: *{video_duration} seconds*\n" \
               f"\n" \
               f"__Picture Interval__:\n" \
               f" |- _Description_: Interval between photos taken after " \
               f"motion is detected|.\n" \
               f" |- _Current value_: *{picture_interval} seconds*\n" \
               f"\n" \
               f"__Draw motion contours__:\n" \
               f" |- _Description_: Draws a rectangle around the objects in " \
               f"motion|.\n" \
               f" |- _Current value_: *{motion_contours_str}*" \
               f"".replace('|', '\\')
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

        BotConfig._render_menu(update, text, buttons)

        return BotConfig.SURVEILLANCE_CONFIG

    @staticmethod
    def _render_menu(
            update: Update,
            text: str,
            buttons: List[List[InlineKeyboardButton]]
    ) -> None:
        """
        Builds the inline keyboard for the menu and sends all to the user.

        Args:
            update: The update to be handled.
            text: Text for the menu caption.
            buttons: Array of button rows,
                each represented by an Array of InlineKeyboardButton objects.
        """
        keyboard = InlineKeyboardMarkup(buttons)

        if update.message:
            update.message.reply_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            update.callback_query.answer()
            update.callback_query.edit_message_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN_V2
            )

    # General configuration options.

    @staticmethod
    def _change_timestamp(
            update: Update,
            context: CallbackContext
    ) -> chr:
        """
        Prepares all required data to request the TIMESTAMP configuration to
        the user.

        Args:
            update: The update to be handled.
            context: The context object for the update.

        Returns:
            The state BOOLEAN_INPUT through `_boolean_question` method.
        """
        timestamp = context.bot_data[BotConfig.TIMESTAMP]

        timestamp_str = 'Enabled' if timestamp else 'Disabled'

        text = f'*Timestamp*\n' \
               f'\n' \
               f'Current state: *{timestamp_str}*\n' \
               f'\n' \
               f'Select state for time stamping:'

        return BotConfig._boolean_question(
            update,
            context,
            text,
            BotConfig.TIMESTAMP,
            BotConfig._general_config
        )

    @staticmethod
    def _change_od_video_duration(
            update: Update,
            context: CallbackContext
    ) -> chr:
        """
        Prepares all required data to request the OD_VIDEO_DURATION
        configuration to the user.

        Args:
            update: The update to be handled.
            context: The context object for the update.

        Returns:
            The state INTEGER_INPUT through `_integer_question` method.
        """
        video_duration = context.bot_data[BotConfig.OD_VIDEO_DURATION]

        text = f'*On Demand video duration*\n' \
               f'\n' \
               f'Current value: *{video_duration}*\n' \
               f'\n' \
               f'Type value for video duration:'

        return BotConfig._integer_question(
            update,
            context,
            text,
            BotConfig.OD_VIDEO_DURATION,
            BotConfig._general_config
        )

    # Surveillance mode configuration options.

    @staticmethod
    def _change_srv_video_duration(
            update: Update,
            context: CallbackContext
    ) -> chr:
        """
        Prepares all required data to request the SRV_VIDEO_DURATION
        configuration to the user.

        Args:
            update: The update to be handled.
            context: The context object for the update.

        Returns:
            The state INTEGER_INPUT through `_integer_question` method.
        """
        video_duration = context.bot_data[BotConfig.SRV_VIDEO_DURATION]

        text = f'*Surveillance video duration*\n' \
               f'\n' \
               f'Current value: *{video_duration}*\n' \
               f'\n' \
               f'Type value for video duration:'

        return BotConfig._integer_question(
            update,
            context,
            text,
            BotConfig.SRV_VIDEO_DURATION,
            BotConfig._surveillance_config
        )

    @staticmethod
    def _change_srv_picture_interval(
            update: Update,
            context: CallbackContext
    ) -> chr:
        """
        Prepares all required data to request the SRV_PICTURE_INTERVAL
        configuration to the user.

        Args:
            update: The update to be handled.
            context: The context object for the update.

        Returns:
            The state INTEGER_INPUT through `_integer_question` method.
        """
        picture_interval = context.bot_data[BotConfig.SRV_PICTURE_INTERVAL]

        text = f'*Surveillance picture interval*\n' \
               f'\n' \
               f'Current value: *{picture_interval}*\n' \
               f'\n' \
               f'Type value for picture interval:'

        return BotConfig._integer_question(
            update,
            context,
            text,
            BotConfig.SRV_PICTURE_INTERVAL,
            BotConfig._surveillance_config
        )

    @staticmethod
    def _change_motion_contours(
            update: Update,
            context: CallbackContext
    ) -> chr:
        """
        Prepares all required data to request the SRV_MOTION_CONTOURS
        configuration to the user.

        Args:
            update: The update to be handled.
            context: The context object for the update.

        Returns:
            The state BOOLEAN_INPUT through `_boolean_question` method.
        """
        motion_contours = context.bot_data[BotConfig.SRV_MOTION_CONTOURS]

        motion_contours_str = 'Enabled' if motion_contours else 'Disabled'

        text = f'*Motion contours*\n' \
               f'\n' \
               f'Current state: *{motion_contours_str}*\n' \
               f'\n' \
               f'Select state for motion contours:'

        return BotConfig._boolean_question(
            update,
            context,
            text,
            BotConfig.SRV_MOTION_CONTOURS,
            BotConfig._surveillance_config
        )

    # Questions helpers.

    @staticmethod
    def _boolean_question(
            update: Update,
            context: CallbackContext,
            text: str,
            current_variable: chr,
            return_handler: chr
    ) -> chr:
        """
        Builds a boolean question to send it to the user using received data.

        Args:
            update: The update to be handled.
            context: The context object for the update.
            text: Message to be shown to the users.
            current_variable: Variable to be set.
            return_handler: Handler to be called with the user response.

        Returns:
            The state BOOLEAN_INPUT.
        """
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
    def _integer_question(
            update: Update,
            context: CallbackContext,
            text: str,
            current_variable: chr,
            return_handler: chr
    ) -> chr:
        """
        Builds a integer question to send it to the user using received data.

        Args:
            update: The update to be handled.
            context: The context object for the update.
            text: Message to be shown to the users.
            current_variable: Variable to be set.
            return_handler: Handler to be called with the user response.

        Returns:
            The state INTEGER_INPUT.
        """
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
    def _boolean_input(update: Update, context: CallbackContext) -> chr:
        """
        Receive a boolean input from the user and saves the value into
        corresponding variable.

        Args:
            update: The update to be handled.
            context: The context object for the update.

        Returns:
            The execution of the previously stored handler.
        """
        context.bot_data[
            context.user_data[BotConfig.CURRENT_VARIABLE]
        ] = update.callback_query.data == BotConfig.ENABLE

        return context.user_data[BotConfig.RETURN_HANDLER](update, context)

    @staticmethod
    def _integer_input(update: Update, context: CallbackContext) -> chr:
        """
        Receive a integer input from the user, validates it, and saves the
        value into corresponding variable.

        Args:
            update: The update to be handled.
            context: The context object for the update.

        Returns:
            The execution of the previously stored handler or the state
                INTEGER_INPUT in case of validation error.
        """
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
    def _end(update: Update, context: CallbackContext) -> int:
        """
        Handler to end the configuration sequence.

        Args:
            update: The update to be handled.
            context: The context object for the update.

        Returns:
            The state END.
        """
        context.user_data.clear()

        if update.callback_query:
            update.callback_query.answer()
            update.callback_query.edit_message_text(text='Configuration done.')
        else:
            update.message.reply_text('Configuration canceled.')

        return BotConfig.END
