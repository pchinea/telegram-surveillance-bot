import logging
import os

# Configuration environment variables.
AUTHORIZED_USER = os.environ.get('AUTHORIZED_USER')
BOT_API_TOKEN = os.environ.get('BOT_API_TOKEN')
GLOBAL_LOG_LEVEL = os.environ.get('GLOBAL_LOG_LEVEL', logging.WARNING)
APP_LOG_LEVEL = os.environ.get('APP_LOG_LEVEL', None)


# Logging config.
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=GLOBAL_LOG_LEVEL
)
