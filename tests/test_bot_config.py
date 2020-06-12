"""
Test suite for BotConfig class testing.
"""
from surveillance_bot.bot_config import BotConfig

from telegram_bot_mock import (
    TelegramBotMock,
    get_kwargs_grabber,
    get_mocked_context_object,
    get_mocked_update_object
)


def test_get_config_handler() -> None:
    """Tests bot config states definition."""
    handler = BotConfig.get_config_handler(TelegramBotMock())
    assert len(handler.states) == 5
    assert BotConfig.MAIN_MENU in handler.states
    assert BotConfig.GENERAL_CONFIG in handler.states
    assert BotConfig.SURVEILLANCE_CONFIG in handler.states
    assert BotConfig.BOOLEAN_INPUT in handler.states
    assert BotConfig.INTEGER_INPUT in handler.states


def test_ensure_defaults() -> None:
    """Tests default configuration generation."""
    context = get_mocked_context_object()
    BotConfig.ensure_defaults(context)
    assert context.bot_data == {
        'timestamp': True,
        'od_video_duration': 5,
        'srv_video_duration': 30,
        'srv_picture_interval': 5,
        'srv_motion_contours': True
    }


def test_main_menu() -> None:
    """Tests main menu generation."""
    update = get_mocked_update_object()
    context = get_mocked_context_object()

    parameters, update.message.reply_text = get_kwargs_grabber()
    assert getattr(BotConfig, '_main_menu')(
        update,
        context
    ) == BotConfig.MAIN_MENU
    assert '*Surveillance Telegram Bot Configuration*' in parameters[0]['text']
    assert parameters[0]['reply_markup'].to_dict() == {
        'inline_keyboard': [
            [
                {
                    'text': 'General configuration',
                    'callback_data': str(BotConfig.GENERAL_CONFIG)
                }
            ],
            [
                {
                    'text': 'Surveillance mode configuration',
                    'callback_data': str(BotConfig.SURVEILLANCE_CONFIG)
                }
            ],
            [
                {
                    'text': 'Done',
                    'callback_data': str(BotConfig.END)
                }
            ]
        ]
    }

    # Answering a callback query instead of replying message
    update.message = None
    parameters2, update.callback_query.edit_message_text = get_kwargs_grabber()
    assert getattr(BotConfig, '_main_menu')(
        update,
        context
    ) == BotConfig.MAIN_MENU
    assert parameters == parameters2
    assert update.callback_query.answered


def test_general_config() -> None:
    """Tests general config menu generation."""
    update = get_mocked_update_object()
    context = get_mocked_context_object()

    parameters, update.message.reply_text = get_kwargs_grabber()
    BotConfig.ensure_defaults(context)
    assert getattr(BotConfig, '_general_config')(
        update,
        context
    ) == BotConfig.GENERAL_CONFIG
    assert '*General configuration*' in parameters[0]['text']
    assert parameters[0]['reply_markup'].to_dict() == {
        'inline_keyboard':
            [
                [
                    {
                        'text': 'Timestamp',
                        'callback_data': str(BotConfig.CHANGE_TIMESTAMP)
                    }
                ],
                [
                    {
                        'text': 'On Demand video duration',
                        'callback_data': str(
                            BotConfig.CHANGE_OD_VIDEO_DURATION
                        )
                    }
                ],
                [
                    {
                        'text': 'Back',
                        'callback_data': str(BotConfig.END)
                    }
                ]
            ]
    }


def test_surveillance_config() -> None:
    """Tests surveillance config menu generation."""
    update = get_mocked_update_object()
    context = get_mocked_context_object()

    parameters, update.message.reply_text = get_kwargs_grabber()
    BotConfig.ensure_defaults(context)
    assert getattr(BotConfig, '_surveillance_config')(
        update,
        context
    ) == BotConfig.SURVEILLANCE_CONFIG
    assert '*Surveillance Mode configuration*' in parameters[0]['text']
    assert parameters[0]['reply_markup'].to_dict() == {
        'inline_keyboard': [
            [
                {
                    'text': 'Video duration',
                    'callback_data': str(BotConfig.CHANGE_SRV_VIDEO_DURATION)
                }
            ],
            [
                {
                    'text': 'Picture Interval',
                    'callback_data': str(BotConfig.CHANGE_SRV_PICTURE_INTERVAL)
                }
            ],
            [
                {
                    'text': 'Draw motion contours',
                    'callback_data': str(BotConfig.CHANGE_SRV_MOTION_CONTOURS)
                }
            ],
            [
                {
                    'text': 'Back',
                    'callback_data': str(BotConfig.END)
                }
            ]
        ]
    }


def test_change_timestamp() -> None:
    """Tests timestamp changing action."""
    update = get_mocked_update_object()
    context = get_mocked_context_object()

    parameters, update.callback_query.edit_message_text = get_kwargs_grabber()
    BotConfig.ensure_defaults(context)
    getattr(BotConfig, '_change_timestamp')(update, context)
    assert '*Timestamp*' in parameters[0]['text']


def test_change_od_video_duration() -> None:
    """Tests on demand video duration changing action."""
    update = get_mocked_update_object()
    context = get_mocked_context_object()

    parameters, update.callback_query.edit_message_text = get_kwargs_grabber()
    BotConfig.ensure_defaults(context)
    getattr(BotConfig, '_change_od_video_duration')(update, context)
    assert '*On Demand video duration*' in parameters[0]['text']


def test_change_srv_video_duration() -> None:
    """Tests surveillance video duration changing action."""
    update = get_mocked_update_object()
    context = get_mocked_context_object()

    parameters, update.callback_query.edit_message_text = get_kwargs_grabber()
    BotConfig.ensure_defaults(context)
    getattr(BotConfig, '_change_srv_video_duration')(update, context)
    assert '*Surveillance video duration*' in parameters[0]['text']


def test_change_srv_picture_interval() -> None:
    """Tests surveillance picture interval changing action."""
    update = get_mocked_update_object()
    context = get_mocked_context_object()

    parameters, update.callback_query.edit_message_text = get_kwargs_grabber()
    BotConfig.ensure_defaults(context)
    getattr(BotConfig, '_change_srv_picture_interval')(update, context)
    assert '*Surveillance picture interval*' in parameters[0]['text']


def test_change_motion_contours() -> None:
    """Tests motion contours changing action."""
    update = get_mocked_update_object()
    context = get_mocked_context_object()

    parameters, update.callback_query.edit_message_text = get_kwargs_grabber()
    BotConfig.ensure_defaults(context)
    getattr(BotConfig, '_change_motion_contours')(update, context)
    assert '*Motion contours*' in parameters[0]['text']


def test_boolean_question() -> None:
    """Tests the request for a boolean value to the user."""
    update = get_mocked_update_object()
    context = get_mocked_context_object()

    parameters, update.callback_query.edit_message_text = get_kwargs_grabber()
    assert getattr(BotConfig, '_boolean_question')(
        update,
        context,
        'fake_text',
        'fake_variable',
        fake_handler := lambda x, y: 'fake_return'
    ) == BotConfig.BOOLEAN_INPUT
    assert parameters[0]['text'] == 'fake_text'
    assert parameters[0]['reply_markup'].to_dict() == {
        'inline_keyboard': [
            [
                {
                    'text': 'Enable',
                    'callback_data': str(BotConfig.ENABLE)
                },
                {
                    'text': 'Disable',
                    'callback_data': str(BotConfig.DISABLE)
                }
            ]
        ]
    }
    assert context.user_data == {
        BotConfig.CURRENT_VARIABLE: 'fake_variable',
        BotConfig.RETURN_HANDLER: fake_handler
    }
    assert update.callback_query.answered


def test_integer_question() -> None:
    """Tests the request for an integer value to the user."""
    update = get_mocked_update_object()
    context = get_mocked_context_object()

    parameters, update.callback_query.edit_message_text = get_kwargs_grabber()
    assert getattr(BotConfig, '_integer_question')(
        update,
        context,
        'fake_text',
        'fake_variable',
        fake_handler := lambda x, y: 'fake_return'
    ) == BotConfig.INTEGER_INPUT
    assert parameters[0]['text'] == 'fake_text'
    assert context.user_data == {
        BotConfig.CURRENT_VARIABLE: 'fake_variable',
        BotConfig.RETURN_HANDLER: fake_handler
    }
    assert update.callback_query.answered


def test_boolean_input() -> None:
    """Tests the store of a boolean value received from the user."""
    update = get_mocked_update_object()
    context = get_mocked_context_object()

    context.user_data[BotConfig.CURRENT_VARIABLE] = 'fake_variable'
    context.user_data[BotConfig.RETURN_HANDLER] = lambda x, y: 'fake_return'

    context.bot_data['fake_variable'] = False
    update.callback_query.data = BotConfig.ENABLE

    assert getattr(BotConfig, '_boolean_input')(
        update,
        context
    ) == 'fake_return'
    assert context.bot_data['fake_variable'] is True


def test_integer_input() -> None:
    """Tests the store of an integer value received from the user."""
    update = get_mocked_update_object()
    context = get_mocked_context_object()

    context.user_data[BotConfig.CURRENT_VARIABLE] = 'fake_variable'
    context.user_data[BotConfig.RETURN_HANDLER] = lambda x, y: 'fake_return'

    context.bot_data['fake_variable'] = 24
    update.message.text = '42'

    assert getattr(BotConfig, '_integer_input')(
        update,
        context
    ) == 'fake_return'
    assert context.bot_data['fake_variable'] == 42

    # Invalid values
    params, update.message.reply_text = get_kwargs_grabber()
    for value in ('-1', '101', 'BAD_TYPE'):
        update.message.text = value
        assert getattr(BotConfig, '_integer_input')(
            update,
            context
        ) == BotConfig.INTEGER_INPUT
        assert 'Invalid value' in params.pop()['text']


def test_end() -> None:
    """Tests the end configuration process method."""
    update = get_mocked_update_object()
    context = get_mocked_context_object()

    context.user_data['key'] = 'value'

    # Done
    parameters, update.callback_query.edit_message_text = get_kwargs_grabber()
    assert getattr(BotConfig, '_end')(update, context) == BotConfig.END
    assert parameters[0]['text'] == 'Configuration done.'
    assert len(context.user_data) == 0
    assert update.callback_query.answered

    # Cancel
    update.callback_query = None
    parameters, update.message.reply_text = get_kwargs_grabber()
    assert getattr(BotConfig, '_end')(update, context) == BotConfig.END
    assert parameters[0]['text'] == 'Configuration canceled.'
