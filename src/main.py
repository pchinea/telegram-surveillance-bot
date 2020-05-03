"""Main script for Surveillance Telegram Bot."""
import logging
import os

from bot import Bot

# Configuration environment variables.
AUTHORIZED_USER = os.environ.get('AUTHORIZED_USER')
BOT_API_TOKEN = os.environ.get('BOT_API_TOKEN')
LOG_LEVEL = os.environ.get('LOG_LEVEL', logging.WARNING)
BOT_LOG_LEVEL = os.environ.get('BOT_LOG_LEVEL', None)


# Logging config.
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=LOG_LEVEL
)


def main():
    """Surveillance Telegram Bot start up function."""
    bot = Bot(
        token=BOT_API_TOKEN,
        username=AUTHORIZED_USER,
        log_level=BOT_LOG_LEVEL
    )
    bot.start()


if __name__ == '__main__':
    main()
