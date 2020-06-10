"""Main script for Surveillance Telegram Bot."""
import logging
import os

import bot

# Configuration environment variables.
AUTHORIZED_USER = os.environ.get('AUTHORIZED_USER', '')
BOT_API_TOKEN = os.environ.get('BOT_API_TOKEN', '')
PERSISTENCE_DIR = os.environ.get('PERSISTENCE_DIR', None)
LOG_LEVEL = os.environ.get('LOG_LEVEL', logging.WARNING)
BOT_LOG_LEVEL = os.environ.get('BOT_LOG_LEVEL', None)


# Logging config.
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=LOG_LEVEL
)
logging.captureWarnings(True)
logging.getLogger('py.warnings').setLevel(logging.ERROR)


def main() -> None:
    """Surveillance Telegram Bot start up function."""
    surveillance_bot = bot.Bot(
        token=BOT_API_TOKEN,
        username=AUTHORIZED_USER,
        persistence_dir=PERSISTENCE_DIR,
        log_level=BOT_LOG_LEVEL
    )
    surveillance_bot.start()


if __name__ == '__main__':  # pragma: no cover
    main()
