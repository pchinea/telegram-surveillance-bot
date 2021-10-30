"""
Module for bot related functionality.

This module implements the `Bot` class that manage the communication between
the user (through a telegram chat) and the camera.
"""
import inspect
import logging
import os
import sys
from functools import wraps
from typing import Any, Callable, Optional, Union

from telegram import ChatAction, ParseMode, ReplyKeyboardMarkup, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Dispatcher,
    PicklePersistence,
    Updater
)  # type: ignore

from surveillance_bot.bot_config import BotConfig
from surveillance_bot.camera import (
    Camera,
    CameraConnectionError,
    CodecNotAvailable
)

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
            persistence_dir: Optional[str] = None,
            log_level: Union[int, str, None] = None
    ) -> None:
        self.logger = logging.getLogger(__name__)
        if log_level:
            self.logger.setLevel(log_level)

        if not token:
            self.logger.critical("Error! Missing BOT_API_KEY configuration")
            sys.exit(1)
        if not username:
            self.logger.critical(
                "Error! Missing AUTHORIZED_USER configuration"
            )
            sys.exit(1)

        try:
            self.camera = Camera()
        except CameraConnectionError:
            self.logger.critical("Error! Can not connect to the camera.")
            sys.exit(2)
        except CodecNotAvailable:
            self.logger.critical(
                "Error! There are no suitable video codec available."
            )
            sys.exit(2)

        self.authorized_user = username

        persistence: Optional[PicklePersistence]
        if persistence_dir:
            os.makedirs(persistence_dir)
            path = os.path.join(persistence_dir, 'surveillance-bot.pickle')
            persistence = PicklePersistence(filename=path)
        else:
            persistence = None

        self.updater = Updater(
            token=token,
            persistence=persistence,
            use_context=True
        )

        dispatcher: Dispatcher = self.updater.dispatcher

        # Registers commands in the dispatcher
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if name.startswith('_command_'):
                command = name.replace('_command_', '')
                dispatcher.add_handler(self.command_handler(command, method))
            if name.startswith('_async_command_'):
                command = name.replace('_async_command_', '')
                dispatcher.add_handler(self.command_handler(command, method, run_async=True))

        # Registers configuration menu
        dispatcher.add_handler(BotConfig.get_config_handler(self))

        # Register error handler
        dispatcher.add_error_handler(self._error)

    def command_handler(
            self,
            command: str,
            callback: HandlerType,
            **kwargs
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
                update.message.reply_text(text="Unauthorized")
                return None

            BotConfig.ensure_defaults(context)
            logger.debug('Received "%s" command', command)
            return callback(update, context)

        return CommandHandler(command, wrapped, **kwargs)

    def start(self) -> None:
        """
        Starts the bot execution and waits to clean up before exit.

        After starting the camera and the bot polling it waits into a loop
        until the bot is interrupted by a signal. After that the camera
        device is released and the function ends.
        """
        self.camera.start()
        self.updater.start_polling()
        self.logger.info("Surveillance Bot started")

        self.updater.idle()

        self.camera.stop()
        self.logger.info("Surveillance Bot stopped")

    def _error(self, update: Union[Update, object], context: CallbackContext) -> None:
        """
        Logs Errors caused by updates.

        Args:
            update: The update to be handled.
            context: The context object for the update.
        """
        self.logger.warning(
            'Update "%s" caused error "%s"',
            update,
            context.error
        )
        context.bot.send_message(
            chat_id=update.effective_chat.id,  # type: ignore
            text="*ERROR|!* Unknown bot internal error, see server logs "
                 "for more information|.".replace('|', '\\'),
            parse_mode=ParseMode.MARKDOWN_V2
        )

    def _command_start(self, update: Update, context: CallbackContext) -> None:
        """
        Handler for `/start` command.

        It sends a presentation to the user and calls the help command.

        Args:
            update: The update to be handled.
            context: The context object for the update.
        """
        update.message.reply_text(
            text="Welcome to the *Surveillance Bot*",
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
                f"/surveillance_{'stop' if active else 'start'}"
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
                 "/get|_photo |- Takes a picture from the cam\n"
                 "/get|_video |- Takes a video from the cam\n"
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
            text=f'Recording a {seconds} seconds video...'
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

    def _async_command_surveillance_start(
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
            update.message.reply_text(
                text='Error! Surveillance is already started'
            )
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
            text="Surveillance mode started",
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
                    text='*MOTION DETECTED|!*'.replace('|', '\\'),
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                waiting_message = update.message.reply_text(
                    text=f'Recording a {video_seconds} seconds video and '
                         f'taking {video_seconds // picture_interval} '
                         f'photos...'
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
            text="Surveillance mode stopped",
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
            update.message.reply_text(
                text="Error! Surveillance is not started"
            )
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
            update.message.reply_text(text="Surveillance mode is active")
        else:
            update.message.reply_text(text="Surveillance mode is not active")
