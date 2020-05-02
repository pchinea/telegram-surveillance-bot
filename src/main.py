"""Main script for Surveillance Telegram Bot."""
from bot import Bot
import config


def main():
    """Surveillance Telegram Bot start up function."""
    bot = Bot(token=config.BOT_API_TOKEN, username=config.AUTHORIZED_USER,
              log_level=config.APP_LOG_LEVEL)
    bot.start()


if __name__ == '__main__':
    main()
