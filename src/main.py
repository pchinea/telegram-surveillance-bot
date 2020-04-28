import logging

from bot import Bot
from capture import Camera


def main():
    logger = logging.getLogger(__name__)
    cam = Camera()
    cam.start()

    bot = Bot(cam)
    updater = bot.get_updater()

    updater.start_polling()
    logger.info('Bot started')

    updater.idle()

    cam.stop()
    logger.info('Bot stopped')


if __name__ == '__main__':
    main()
